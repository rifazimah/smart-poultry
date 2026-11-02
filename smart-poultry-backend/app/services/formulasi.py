from app.models.operasional import FormulasiNutrisiHasil
from app.models.operasional import FormulasiItem
from app.models.operasional import Formulasi
from app.models.akses import User
import uuid
from typing import List, Dict, Optional

from sqlmodel import Session, select
from scipy.optimize import linprog

from app.models.enums import ModeFormulasi, StatusFormulasi, StatusNutrisi, StatusSiklus
from app.models.masterdata import (
    Nutrisi, BahanPakan, KandunganNutrisiBahan,
    KebutuhanNutrisiFase, StandarKonsumsi
)
from app.models.fisik import Alat, Wadah
from app.models.operasional import SiklusKandang
from app.schemas.formulasi import (
    FormulasiPreview, FormulasiItemOutput, NutrisiHasilOutput, FormulasiItemInput
)


class FormulasiException(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code


def _get_alat_and_bahan(session: Session, kandang_id: uuid.UUID):
    alat = session.exec(select(Alat).where(Alat.kandang_id == kandang_id)).first()
    if not alat:
        raise FormulasiException("Kandang belum memiliki Alat IoT", 409)

    wadah_list = session.exec(
        select(Wadah).where(Wadah.alat_id == alat.id, Wadah.bahan_pakan_id != None)
    ).all()
    
    if not wadah_list:
        raise FormulasiException("Tidak ada bahan pakan yang terpasang di wadah", 409)

    bahan_ids = [w.bahan_pakan_id for w in wadah_list]
    bahan_list = session.exec(select(BahanPakan).where(BahanPakan.id.in_(bahan_ids))).all()
    
    return alat, bahan_list


def _get_kebutuhan_and_standar(session: Session, fase_id: uuid.UUID):
    kebutuhan = session.exec(
        select(KebutuhanNutrisiFase).where(KebutuhanNutrisiFase.fase_id == fase_id)
    ).all()
    if not kebutuhan:
        raise FormulasiException("Kebutuhan nutrisi untuk fase ini belum diatur", 409)
        
    standar = session.exec(
        select(StandarKonsumsi).where(StandarKonsumsi.fase_id == fase_id)
    ).first()
    if not standar:
        raise FormulasiException("Standar konsumsi untuk fase ini belum diatur", 409)
        
    return kebutuhan, standar


def _evaluate_nutrisi(
    session: Session,
    bahan_list: List[BahanPakan],
    proporsi_dict: Dict[uuid.UUID, float],
    kebutuhan: List[KebutuhanNutrisiFase]
) -> List[NutrisiHasilOutput]:
    # Ambil semua nutrisi ID yang ada di kebutuhan
    nutrisi_ids = [k.nutrisi_id for k in kebutuhan]
    
    # Ambil detail nutrisi untuk nama
    nutrisi_detail = session.exec(select(Nutrisi).where(Nutrisi.id.in_(nutrisi_ids))).all()
    nutrisi_map = {n.id: n for n in nutrisi_detail}
    
    # Ambil kandungan nutrisi setiap bahan
    kandungan = session.exec(
        select(KandunganNutrisiBahan).where(
            KandunganNutrisiBahan.bahan_pakan_id.in_([b.id for b in bahan_list]),
            KandunganNutrisiBahan.nutrisi_id.in_(nutrisi_ids)
        )
    ).all()
    
    # Kelompokkan kandungan per nutrisi
    kandungan_map: Dict[uuid.UUID, Dict[uuid.UUID, float]] = {nid: {} for nid in nutrisi_ids}
    for k in kandungan:
        kandungan_map[k.nutrisi_id][k.bahan_pakan_id] = k.nilai_per_kg
        
    hasil = []
    for keb in kebutuhan:
        nilai_total = 0.0
        for b in bahan_list:
            nilai = kandungan_map[keb.nutrisi_id].get(b.id, 0.0)
            nilai_total += nilai * proporsi_dict[b.id]
            
        status = StatusNutrisi.SESUAI
        if keb.batas_min is not None and nilai_total < (keb.batas_min - 1e-4):
            status = StatusNutrisi.KURANG
        if keb.batas_max is not None and nilai_total > (keb.batas_max + 1e-4):
            status = StatusNutrisi.BERLEBIH
            
        hasil.append(
            NutrisiHasilOutput(
                nutrisi_id=keb.nutrisi_id,
                nama_nutrisi=nutrisi_map[keb.nutrisi_id].nama,
                nilai_hasil=nilai_total,
                batas_min=keb.batas_min,
                batas_max=keb.batas_max,
                status=status
            )
        )
        
    return hasil


def hitung_formulasi_otomatis(session: Session, siklus: SiklusKandang) -> FormulasiPreview:
    alat, bahan_list = _get_alat_and_bahan(session, siklus.kandang_id)
    kebutuhan, standar = _get_kebutuhan_and_standar(session, siklus.fase_id)
    
    # Validasi harga
    for b in bahan_list:
        if b.harga is None:
            raise FormulasiException(f"Bahan {b.nama} belum memiliki harga (wajib untuk OTOMATIS)", 409)
            
    # Susun matriks LP
    c = [b.harga for b in bahan_list]
    
    A_eq = [[1.0 for _ in bahan_list]]
    b_eq = [1.0]
    
    A_ub = []
    b_ub = []
    
    # Ambil kandungan nutrisi untuk batas
    nutrisi_ids = [k.nutrisi_id for k in kebutuhan]
    kandungan = session.exec(
        select(KandunganNutrisiBahan).where(
            KandunganNutrisiBahan.bahan_pakan_id.in_([b.id for b in bahan_list]),
            KandunganNutrisiBahan.nutrisi_id.in_(nutrisi_ids)
        )
    ).all()
    kand_map = {}
    for k in kandungan:
        if k.nutrisi_id not in kand_map:
            kand_map[k.nutrisi_id] = {}
        kand_map[k.nutrisi_id][k.bahan_pakan_id] = k.nilai_per_kg
        
    for keb in kebutuhan:
        row = [kand_map.get(keb.nutrisi_id, {}).get(b.id, 0.0) for b in bahan_list]
        
        if keb.batas_min is not None:
            # -x <= -min  =>  x >= min
            A_ub.append([-val for val in row])
            b_ub.append(-keb.batas_min)
            
        if keb.batas_max is not None:
            # x <= max
            A_ub.append([val for val in row])
            b_ub.append(keb.batas_max)
            
    bounds = [(0, b.batas_maksimum if b.batas_maksimum is not None else 1.0) for b in bahan_list]
    
    res = linprog(c, A_ub=A_ub if A_ub else None, b_ub=b_ub if b_ub else None, 
                  A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")
                  
    total_pakan_sesi = (standar.gram_per_ekor_per_hari * siklus.jumlah_ayam) / standar.frekuensi_makan
    
    if not res.success:
        # Infeasible!
        return FormulasiPreview(
            siklus_id=siklus.id,
            mode=ModeFormulasi.OTOMATIS,
            status=StatusFormulasi.TIDAK_SEMPURNA,
            total_biaya_per_kg=None,
            item=[],
            nutrisi_hasil=[],
            pesan="Formulasi tidak dapat memenuhi batasan nutrisi dengan bahan pakan yang tersedia."
        )
        
    # Sukses
    proporsi_dict = {bahan_list[i].id: float(res.x[i]) for i in range(len(bahan_list))}
    
    item_out = []
    for b in bahan_list:
        p = proporsi_dict[b.id]
        if p > 1e-5: # abaikan yang sangat kecil (0)
            item_out.append(
                FormulasiItemOutput(
                    bahan_pakan_id=b.id,
                    nama_bahan=b.nama,
                    proporsi=p,
                    berat_per_sesi=p * total_pakan_sesi
                )
            )
            
    nutrisi_hasil = _evaluate_nutrisi(session, bahan_list, proporsi_dict, kebutuhan)
    
    # Cek ada nutrisi di luar batas (seharusnya tidak ada jika sukses)
    status_form = StatusFormulasi.VALID
    for n in nutrisi_hasil:
        if n.status != StatusNutrisi.SESUAI:
            status_form = StatusFormulasi.TIDAK_SEMPURNA
            
    return FormulasiPreview(
        siklus_id=siklus.id,
        mode=ModeFormulasi.OTOMATIS,
        status=status_form,
        total_biaya_per_kg=float(res.fun),
        item=item_out,
        nutrisi_hasil=nutrisi_hasil,
        pesan=None
    )


def hitung_formulasi_manual(
    session: Session, 
    siklus: SiklusKandang, 
    items: List[FormulasiItemInput]
) -> FormulasiPreview:
    alat, bahan_list = _get_alat_and_bahan(session, siklus.kandang_id)
    kebutuhan, standar = _get_kebutuhan_and_standar(session, siklus.fase_id)
    
    bahan_ids_available = {b.id for b in bahan_list}
    bahan_map = {b.id: b for b in bahan_list}
    
    # Validasi input
    total_proporsi = 0.0
    proporsi_dict = {b.id: 0.0 for b in bahan_list}
    
    for i in items:
        if i.bahan_pakan_id not in bahan_ids_available:
            raise FormulasiException(f"Bahan pakan {i.bahan_pakan_id} tidak tersedia di wadah alat ini", 400)
        if i.proporsi < 0:
            raise FormulasiException("Proporsi tidak boleh negatif", 400)
        total_proporsi += i.proporsi
        proporsi_dict[i.bahan_pakan_id] = i.proporsi
        
    if abs(total_proporsi - 1.0) > 1e-4:
        raise FormulasiException(f"Total proporsi harus 1.0 (saat ini {total_proporsi})", 400)
        
    total_biaya = 0.0
    for b in bahan_list:
        if proporsi_dict[b.id] > 0 and b.harga is not None:
            total_biaya += proporsi_dict[b.id] * b.harga
            
    total_pakan_sesi = (standar.gram_per_ekor_per_hari * siklus.jumlah_ayam) / standar.frekuensi_makan
    
    item_out = []
    for b in bahan_list:
        p = proporsi_dict[b.id]
        if p > 0:
            item_out.append(
                FormulasiItemOutput(
                    bahan_pakan_id=b.id,
                    nama_bahan=b.nama,
                    proporsi=p,
                    berat_per_sesi=p * total_pakan_sesi
                )
            )
            
    nutrisi_hasil = _evaluate_nutrisi(session, bahan_list, proporsi_dict, kebutuhan)
    
    pesan_error = []
    for n in nutrisi_hasil:
        if n.status != StatusNutrisi.SESUAI:
            pesan_error.append(n.nama_nutrisi)
            
    status_form = StatusFormulasi.VALID
    pesan = None
    if pesan_error:
        status_form = StatusFormulasi.TIDAK_SEMPURNA
        pesan = "Nutrisi tidak sesuai batas: " + ", ".join(pesan_error)
        
    return FormulasiPreview(
        siklus_id=siklus.id,
        mode=ModeFormulasi.MANUAL,
        status=status_form,
        total_biaya_per_kg=total_biaya if total_biaya > 0 else None,
        item=item_out,
        nutrisi_hasil=nutrisi_hasil,
        pesan=pesan
    )


TOLERANSI_BIAYA_REL = 1e-3  # preview OTOMATIS boleh selisih 0,1% dari optimum (pembulatan di klien)


def simpan_formulasi_service(
    session: Session,
    preview: FormulasiPreview,
    current_user: User
) -> Formulasi:
    """
    Simpan formulasi sebagai snapshot. Angka dari klien TIDAK dipercaya: hanya komposisi
    (bahan + proporsi) yang dipakai, lalu semua nilai dihitung ulang di server dari data terkini.
    Untuk mode OTOMATIS, komposisi harus sama dengan hasil LP terbaru (biaya sama dalam toleransi
    dan batas_maksimum per bahan terpenuhi); bila tidak, 409 dan klien diminta menghitung ulang.
    """
    from app.routers.siklus import _get_siklus_or_404
    siklus = _get_siklus_or_404(session, preview.siklus_id, current_user)
    if siklus.status != StatusSiklus.AKTIF:
        raise FormulasiException("Siklus sudah selesai", 409)
    if not preview.item:
        raise FormulasiException("Formulasi tanpa bahan tidak dapat disimpan", 400)

    # Bahan harus masih terpasang di wadah alat (409 bila dilepas sejak preview dibuat)
    alat = session.exec(select(Alat).where(Alat.kandang_id == siklus.kandang_id)).first()
    if not alat:
        raise FormulasiException("Kandang tidak memiliki alat IoT", 409)
    wadah_list = session.exec(select(Wadah).where(Wadah.alat_id == alat.id)).all()
    bahan_terpasang = {w.bahan_pakan_id for w in wadah_list if w.bahan_pakan_id is not None}
    for item in preview.item:
        if item.bahan_pakan_id not in bahan_terpasang:
            raise FormulasiException(
                f"Bahan pakan {item.nama_bahan} sudah dilepas dari wadah sejak preview dibuat.", 409
            )

    # Hitung ulang dari komposisi (validasi proporsi, nutrisi, biaya, berat per sesi)
    hasil = hitung_formulasi_manual(
        session, siklus,
        [FormulasiItemInput(bahan_pakan_id=i.bahan_pakan_id, proporsi=i.proporsi) for i in preview.item],
    )

    if preview.mode == ModeFormulasi.OTOMATIS:
        acuan = hitung_formulasi_otomatis(session, siklus)
        if acuan.status != StatusFormulasi.VALID or acuan.total_biaya_per_kg is None:
            raise FormulasiException("Formulasi otomatis tidak lagi dapat dipenuhi; hitung ulang.", 409)
        bahan = {
            b.id: b for b in session.exec(
                select(BahanPakan).where(BahanPakan.id.in_([i.bahan_pakan_id for i in hasil.item]))
            ).all()
        }
        melebihi = [
            i.nama_bahan for i in hasil.item
            if bahan[i.bahan_pakan_id].batas_maksimum is not None
            and i.proporsi > bahan[i.bahan_pakan_id].batas_maksimum + 1e-4
        ]
        if melebihi:
            raise FormulasiException("Proporsi melebihi batas maksimum bahan: " + ", ".join(melebihi), 409)
        if hasil.total_biaya_per_kg is None or abs(hasil.total_biaya_per_kg - acuan.total_biaya_per_kg) > max(
            0.01, TOLERANSI_BIAYA_REL * acuan.total_biaya_per_kg
        ):
            raise FormulasiException(
                "Komposisi tidak sesuai hasil perhitungan otomatis terbaru; hitung ulang formulasi.", 409
            )

    # Nonaktifkan formulasi lama yang aktif
    for f in session.exec(
        select(Formulasi).where(
            Formulasi.siklus_id == siklus.id,
            Formulasi.aktif == True  # noqa: E712
        )
    ).all():
        f.aktif = False
        session.add(f)

    db_form = Formulasi(
        siklus_id=siklus.id,
        dibuat_oleh_id=current_user.id,
        mode=preview.mode,
        total_biaya_per_kg=hasil.total_biaya_per_kg,
        status=hasil.status,
        aktif=hasil.status == StatusFormulasi.VALID,
    )
    session.add(db_form)
    session.flush()  # db_form.id

    for item in hasil.item:
        session.add(FormulasiItem(
            formulasi_id=db_form.id,
            bahan_pakan_id=item.bahan_pakan_id,
            proporsi=item.proporsi,
            berat_per_sesi=item.berat_per_sesi,
        ))
    for nh in hasil.nutrisi_hasil:
        session.add(FormulasiNutrisiHasil(
            formulasi_id=db_form.id,
            nutrisi_id=nh.nutrisi_id,
            nilai_hasil=nh.nilai_hasil,
            status=nh.status,
        ))

    session.commit()
    session.refresh(db_form)
    return db_form
