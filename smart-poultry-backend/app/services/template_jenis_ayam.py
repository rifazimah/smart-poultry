"""
Template referensi jenis ayam (BR-13): data statis bawaan, tidak terikat Pemilik dan tidak disimpan di tabel.
`salin_template` menyalin jenis ayam + fase + kebutuhan nutrisi + standar konsumsi ke akun Pemilik.

PERHATIAN: angka di bawah adalah CONTOH berdasarkan kisaran umum, BUKAN rekomendasi gizi resmi. Pemilik wajib
menyesuaikannya dengan pedoman strain/pakar nutrisi sebelum dipakai untuk formulasi sungguhan.
"""
import uuid
from typing import Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlmodel import Session, select

from app.models.akses import User
from app.models.enums import TipeBatas
from app.models.masterdata import Fase, JenisAyam, KebutuhanNutrisiFase, Nutrisi, StandarKonsumsi
from app.services.audit import catat_audit

DISCLAIMER = (
    "Contoh nilai berdasarkan kisaran umum, bukan rekomendasi gizi resmi. "
    "Sesuaikan dengan pedoman strain atau pakar nutrisi sebelum dipakai."
)

# Nama nutrisi dipakai sebagai kunci pencocokan (tanpa membedakan huruf besar/kecil) dengan nutrisi milik Pemilik.
NUTRISI = {
    "Protein": ("%", TipeBatas.MIN_MAKS),
    "Energi Metabolis": ("kkal/kg", TipeBatas.MINIMUM),
    "Kalsium": ("%", TipeBatas.MIN_MAKS),
    "Fosfor Tersedia": ("%", TipeBatas.MIN_MAKS),
    "Lisin": ("%", TipeBatas.MINIMUM),
}


def _fase(nama, umur_min, umur_max, protein, energi_min, kalsium, fosfor, lisin_min, gram, frekuensi, air):
    return {
        "nama": nama,
        "umur_min_hari": umur_min,
        "umur_max_hari": umur_max,
        "kebutuhan": [
            {"nutrisi": "Protein", "batas_min": protein[0], "batas_max": protein[1]},
            {"nutrisi": "Energi Metabolis", "batas_min": energi_min, "batas_max": None},
            {"nutrisi": "Kalsium", "batas_min": kalsium[0], "batas_max": kalsium[1]},
            {"nutrisi": "Fosfor Tersedia", "batas_min": fosfor[0], "batas_max": fosfor[1]},
            {"nutrisi": "Lisin", "batas_min": lisin_min, "batas_max": None},
        ],
        "standar_konsumsi": {
            "gram_per_ekor_per_hari": gram,
            "frekuensi_makan": frekuensi,
            "durasi_aduk": 30,
            "volume_air": air,
        },
    }


TEMPLATE: List[dict] = [
    {
        "id": "broiler",
        "nama": "Broiler",
        "deskripsi": "Ayam pedaging 0–42 hari (Starter, Grower, Finisher). " + DISCLAIMER,
        "fase": [
            _fase("Starter", 0, 14, (21, 23), 3000, (0.90, 1.10), (0.45, 0.55), 1.20, 35, 4, 200),
            _fase("Grower", 15, 28, (19, 21), 3100, (0.80, 1.00), (0.40, 0.50), 1.05, 110, 3, 300),
            _fase("Finisher", 29, 42, (17.5, 19.5), 3150, (0.75, 0.95), (0.35, 0.45), 0.95, 170, 3, 400),
        ],
    },
    {
        "id": "petelur",
        "nama": "Ayam Petelur",
        "deskripsi": "Ayam petelur (Starter, Grower, Layer). " + DISCLAIMER,
        "fase": [
            _fase("Starter", 0, 42, (19, 21), 2800, (0.90, 1.10), (0.45, 0.50), 1.00, 30, 3, 200),
            _fase("Grower", 43, 126, (15, 17), 2750, (0.90, 1.20), (0.40, 0.45), 0.70, 70, 2, 250),
            _fase("Layer", 127, 540, (16, 18), 2750, (3.50, 4.20), (0.35, 0.42), 0.75, 110, 2, 300),
        ],
    },
]


def daftar_template() -> List[dict]:
    return TEMPLATE


def _cari_template(template_id: str) -> dict:
    for t in TEMPLATE:
        if t["id"] == template_id:
            return t
    raise HTTPException(status_code=404, detail="Template tidak ditemukan")


def _nutrisi_milik(session: Session, pemilik_id: uuid.UUID, nama: str, dibuat: List[str]) -> Nutrisi:
    """Cari nutrisi Pemilik berdasarkan nama (tanpa beda huruf); buat dari katalog template bila belum ada."""
    ada = session.exec(
        select(Nutrisi).where(Nutrisi.pemilik_id == pemilik_id, func.lower(Nutrisi.nama) == nama.lower())
    ).first()
    if ada:
        return ada
    satuan, tipe = NUTRISI[nama]
    baru = Nutrisi(pemilik_id=pemilik_id, nama=nama, satuan=satuan, tipe_batas=tipe)
    session.add(baru)
    session.flush()
    dibuat.append(nama)
    return baru


def salin_template(session: Session, pemilik: User, template_id: str, nama: Optional[str] = None) -> JenisAyam:
    t = _cari_template(template_id)
    nama_baru = (nama or t["nama"]).strip()
    if not nama_baru:
        raise HTTPException(status_code=400, detail="Nama jenis ayam tidak boleh kosong")
    kembar = session.exec(
        select(JenisAyam).where(JenisAyam.pemilik_id == pemilik.id, func.lower(JenisAyam.nama) == nama_baru.lower())
    ).first()
    if kembar:
        raise HTTPException(
            status_code=409,
            detail=f"Jenis ayam bernama '{nama_baru}' sudah ada. Beri nama lain (body: {{\"nama\": \"...\"}}) atau hapus yang lama.",
        )

    jenis = JenisAyam(pemilik_id=pemilik.id, nama=nama_baru)
    session.add(jenis)
    session.flush()

    nutrisi_baru: List[str] = []
    for f in t["fase"]:
        fase = Fase(
            jenis_ayam_id=jenis.id, nama=f["nama"], umur_min_hari=f["umur_min_hari"], umur_max_hari=f["umur_max_hari"]
        )
        session.add(fase)
        session.flush()
        for k in f["kebutuhan"]:
            n = _nutrisi_milik(session, pemilik.id, k["nutrisi"], nutrisi_baru)
            session.add(KebutuhanNutrisiFase(
                fase_id=fase.id, nutrisi_id=n.id, batas_min=k["batas_min"], batas_max=k["batas_max"]
            ))
        session.add(StandarKonsumsi(fase_id=fase.id, **f["standar_konsumsi"]))

    catat_audit(
        session, pemilik.id, "SALIN_TEMPLATE", "jenis_ayam", jenis.id,
        nilai_baru=f"template={template_id}, nama={nama_baru}",
        catatan=("nutrisi baru: " + ", ".join(nutrisi_baru)) if nutrisi_baru else "memakai nutrisi yang sudah ada",
    )
    session.commit()
    session.refresh(jenis)
    return jenis
