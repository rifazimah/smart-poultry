"""
Diagnosis formulasi otomatis yang infeasible (S-1, BR-11).

Ketika LP utama tidak punya solusi, kita menjawab "nutrisi mana yang bermasalah" dalam tiga langkah:
1. Cek dasar: jumlah batas maksimum bahan harus >= 100% (kalau tidak, tak ada komposisi yang berjumlah 1).
2. Rentang tiap nutrisi: nilai terendah dan tertinggi yang MUNGKIN dicapai dengan bahan terpasang (dua LP kecil,
   hanya dengan kendala "jumlah = 1" dan batas per bahan). Batas yang berada di luar rentang itu mustahil dipenuhi
   oleh komposisi apa pun.
3. Kompromi: bila tiap nutrisi mungkin sendiri-sendiri tetapi tidak bersama, LP "elastis" mencari komposisi dengan
   total pelanggaran relatif terkecil; nutrisi yang masih melanggar pada komposisi itu dilaporkan berbenturan.
Hasil diagnosis hanya informasi: `item` tetap kosong dan tidak dapat disimpan sebagai formulasi.
"""
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from scipy.optimize import linprog

from app.models.enums import StatusNutrisi
from app.schemas.formulasi import NutrisiHasilOutput

TOL = 1e-4
PESAN_UMUM = "Formulasi tidak dapat memenuhi batasan nutrisi dengan bahan pakan yang tersedia."
SARAN = "Tambah bahan pakan berkadar nutrisi yang sesuai, longgarkan batas nutrisi, atau naikkan batas_maksimum bahan."


@dataclass
class BatasNutrisi:
    """Satu baris KebutuhanNutrisiFase beserta kandungan tiap bahan (urutan sama dengan `bounds`)."""
    nutrisi_id: object
    nama: str
    satuan: str
    batas_min: Optional[float]
    batas_max: Optional[float]
    kandungan: List[float]


def _status(nilai: float, batas_min: Optional[float], batas_max: Optional[float]) -> StatusNutrisi:
    if batas_min is not None and nilai < batas_min - TOL:
        return StatusNutrisi.KURANG
    if batas_max is not None and nilai > batas_max + TOL:
        return StatusNutrisi.BERLEBIH
    return StatusNutrisi.SESUAI


def _rentang(kandungan: Sequence[float], bounds: Sequence[Tuple[float, float]]) -> Optional[Tuple[float, float]]:
    """(terendah, tertinggi) nilai nutrisi dengan kendala jumlah=1 dan batas per bahan; None bila gagal dihitung."""
    n = len(bounds)
    kwargs = dict(A_eq=[[1.0] * n], b_eq=[1.0], bounds=list(bounds), method="highs")
    rendah = linprog(list(kandungan), **kwargs)
    tinggi = linprog([-v for v in kandungan], **kwargs)
    if not (rendah.success and tinggi.success):
        return None
    return float(rendah.fun), float(-tinggi.fun)


def _kompromi(batas: List[BatasNutrisi], bounds: Sequence[Tuple[float, float]]) -> Optional[List[float]]:
    """Komposisi dengan total pelanggaran relatif terkecil (LP elastis). None bila gagal."""
    n = len(bounds)
    sisi = []  # (indeks batas, "min"/"max", ambang)
    for j, b in enumerate(batas):
        if b.batas_min is not None:
            sisi.append((j, "min", b.batas_min))
        if b.batas_max is not None:
            sisi.append((j, "max", b.batas_max))
    m = len(sisi)

    c = [0.0] * n + [1.0 / max(abs(ambang), 1e-3) for _, _, ambang in sisi]
    A_ub, b_ub = [], []
    for k, (j, jenis, ambang) in enumerate(sisi):
        slack = [0.0] * m
        slack[k] = -1.0
        if jenis == "min":      # nilai + slack >= min
            A_ub.append([-v for v in batas[j].kandungan] + slack)
            b_ub.append(-ambang)
        else:                   # nilai - slack <= max
            A_ub.append(list(batas[j].kandungan) + slack)
            b_ub.append(ambang)

    res = linprog(
        c, A_ub=A_ub or None, b_ub=b_ub or None,
        A_eq=[[1.0] * n + [0.0] * m], b_eq=[1.0],
        bounds=list(bounds) + [(0, None)] * m, method="highs",
    )
    return [float(v) for v in res.x[:n]] if res.success else None


def _titik_layak(bounds: Sequence[Tuple[float, float]]) -> Optional[List[float]]:
    n = len(bounds)
    res = linprog([0.0] * n, A_eq=[[1.0] * n], b_eq=[1.0], bounds=list(bounds), method="highs")
    return [float(v) for v in res.x] if res.success else None


def diagnosa_infeasible(
    batas: List[BatasNutrisi], bounds: Sequence[Tuple[float, float]]
) -> Tuple[str, List[NutrisiHasilOutput]]:
    """Mengembalikan (pesan, nutrisi_hasil) untuk preview `TIDAK_SEMPURNA`."""
    total_maks = sum(ub for _, ub in bounds)
    if total_maks < 1 - 1e-9:
        return (
            f"Jumlah batas maksimum bahan terpasang hanya {total_maks * 100:.0f}% (kurang dari 100%), "
            f"sehingga tidak ada komposisi yang berjumlah 100%. Naikkan batas_maksimum bahan atau tambah bahan di wadah.",
            [],
        )

    rentang = {b.nutrisi_id: _rentang(b.kandungan, bounds) for b in batas}
    x = _kompromi(batas, bounds) or _titik_layak(bounds)
    if x is None:
        return PESAN_UMUM, []

    hasil: List[NutrisiHasilOutput] = []
    mustahil: List[str] = []   # batas yang tak mungkin dipenuhi komposisi apa pun
    berbenturan: List[str] = []  # mungkin sendiri-sendiri, melanggar pada komposisi kompromi
    for b in batas:
        nilai = sum(k * xi for k, xi in zip(b.kandungan, x))
        status = _status(nilai, b.batas_min, b.batas_max)
        keterangan = None
        rng = rentang[b.nutrisi_id]
        u = b.satuan

        if rng and b.batas_min is not None and b.batas_min > rng[1] + TOL:
            nilai, status = rng[1], StatusNutrisi.KURANG
            keterangan = (f"Batas minimum {b.batas_min:g} {u} tidak tercapai; nilai tertinggi yang mungkin "
                          f"dengan bahan terpasang {rng[1]:.2f} {u}")
            mustahil.append(f"{b.nama} (min {b.batas_min:g} {u}; tertinggi yang mungkin {rng[1]:.2f})")
        elif rng and b.batas_max is not None and b.batas_max < rng[0] - TOL:
            nilai, status = rng[0], StatusNutrisi.BERLEBIH
            keterangan = (f"Batas maksimum {b.batas_max:g} {u} tidak tercapai; nilai terendah yang mungkin "
                          f"dengan bahan terpasang {rng[0]:.2f} {u}")
            mustahil.append(f"{b.nama} (maks {b.batas_max:g} {u}; terendah yang mungkin {rng[0]:.2f})")
        elif status != StatusNutrisi.SESUAI:
            ambang = (f"min {b.batas_min:g}" if status == StatusNutrisi.KURANG else f"maks {b.batas_max:g}")
            keterangan = (f"Berbenturan dengan batas nutrisi lain; komposisi kompromi terdekat menghasilkan "
                          f"{nilai:.2f} {u} ({ambang} {u})")
            berbenturan.append(f"{b.nama} ({ambang} {u}; tercapai {nilai:.2f})")

        hasil.append(NutrisiHasilOutput(
            nutrisi_id=b.nutrisi_id, nama_nutrisi=b.nama, nilai_hasil=float(nilai),
            batas_min=b.batas_min, batas_max=b.batas_max, status=status, keterangan=keterangan,
        ))

    bagian = []
    if mustahil:
        bagian.append("Formulasi tidak dapat memenuhi batas nutrisi: " + ", ".join(mustahil))
    if berbenturan:
        awal = "Selain itu, batas" if mustahil else "Batas"
        bagian.append(
            f"{awal} nutrisi saling bertentangan pada bahan terpasang (tidak ada komposisi yang memenuhi semuanya "
            "sekaligus); pada komposisi kompromi terdekat yang masih melanggar: " + ", ".join(berbenturan)
            + " (salah satu pilihan kompromi; longgarkan salah satu batas yang berbenturan)"
        )
    if not bagian:
        return PESAN_UMUM + " " + SARAN, hasil
    return ". ".join(bagian) + ". " + SARAN, hasil
