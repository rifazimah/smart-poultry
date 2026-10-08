from app.models.operasional import FormulasiNutrisiHasil
from app.models.operasional import FormulasiItem
from app.models.operasional import Formulasi
from app.models.akses import User
import uuid
from typing import List, Dict, Optional

from sqlmodel import Session, select
from scipy.optimize import linprog

from app.models.enums import ModeFormulasi, StatusFormulasi, StatusNutrisi
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
        raise FormulasiException("Kandang belum memiliki Alat IoT", 400)

    wadah_list = session.exec(
        select(Wadah).where(Wadah.alat_id == alat.id, Wadah.bahan_pakan_id != None)
    ).all()
    
    if not wadah_list:
        raise FormulasiException("Tidak ada bahan pakan yang terpasang di wadah", 400)

    bahan_ids = [w.bahan_pakan_id for w in wadah_list]
    bahan_list = session.exec(select(BahanPakan).where(BahanPakan.id.in_(bahan_ids))).all()
    
    return alat, bahan_list


def _get_kebutuhan_and_standar(session: Session, fase_id: uuid.UUID):
    kebutuhan = session.exec(
        select(KebutuhanNutrisiFase).where(KebutuhanNutrisiFase.fase_id == fase_id)
    ).all()
    if not kebutuhan:
        raise FormulasiException("Kebutuhan nutrisi untuk fase ini belum diatur", 400)
        
    standar = session.exec(
        select(StandarKonsumsi).where(StandarKonsumsi.fase_id == fase_id)
    ).first()
    if not standar:
        raise FormulasiException("Standar konsumsi untuk fase ini belum diatur", 400)
        
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
            status = StatusNutrisi.TIDAK_SESUAI
        if keb.batas_max is not None and nilai_total > (keb.batas_max + 1e-4):
            status = StatusNutrisi.TIDAK_SESUAI
            
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
    
    # Cek ada TIDAK_SESUAI gak (seharusnya tidak ada jika sukses)
    status_form = StatusFormulasi.VALID
    for n in nutrisi_hasil:
        if n.status == StatusNutrisi.TIDAK_SESUAI:
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
        if n.status == StatusNutrisi.TIDAK_SESUAI:
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


def simpan_formulasi_service(
    session: Session,
    preview: FormulasiPreview,
    current_user: User
) -> Formulasi:
    from app.routers.siklus import _get_siklus_or_404
    siklus = _get_siklus_or_404(session, preview.siklus_id, current_user)
    
    # Validasi wadah: pastikan bahan_pakan_id di item masih terpasang di wadah alat
    alat = session.exec(select(Alat).where(Alat.kandang_id == siklus.kandang_id)).first()
    if not alat:
        raise FormulasiException("Kandang tidak memiliki alat IoT", 400)
        
    wadah_list = session.exec(select(Wadah).where(Wadah.alat_id == alat.id)).all()
    bahan_terpasang = {w.bahan_pakan_id for w in wadah_list if w.bahan_pakan_id is not None}
    
    for item in preview.item:
        if item.bahan_pakan_id not in bahan_terpasang:
            raise FormulasiException(
                f"Bahan pakan {item.nama_bahan} sudah dilepas dari wadah sejak preview dibuat.", 409
            )
            
    # Nonaktifkan formulasi lama yang aktif
    old_formulas = session.exec(
        select(Formulasi).where(
            Formulasi.siklus_id == preview.siklus_id,
            Formulasi.status.in_([StatusFormulasi.AKTIF, StatusFormulasi.PERLU_DITINJAU])
        )
    ).all()
    for f in old_formulas:
        f.status = StatusFormulasi.NONAKTIF
        session.add(f)
        
    # Buat Formulasi baru
    db_form = Formulasi(
        siklus_id=preview.siklus_id,
        dibuat_oleh_id=current_user.id,
        mode=preview.mode,
        total_biaya_per_kg=preview.total_biaya_per_kg,
        status=StatusFormulasi.AKTIF if preview.status != StatusFormulasi.TIDAK_SEMPURNA else StatusFormulasi.TIDAK_SEMPURNA
    )
    session.add(db_form)
    session.commit()
    session.refresh(db_form)
    
    # Simpan Items
    for item in preview.item:
        db_item = FormulasiItem(
            formulasi_id=db_form.id,
            bahan_pakan_id=item.bahan_pakan_id,
            proporsi=item.proporsi,
            berat_per_sesi=item.berat_per_sesi
        )
        session.add(db_item)
        
    # Simpan Nutrisi Hasil
    for nh in preview.nutrisi_hasil:
        db_nh = FormulasiNutrisiHasil(
            formulasi_id=db_form.id,
            nutrisi_id=nh.nutrisi_id,
            nilai_hasil=nh.nilai_hasil,
            status=nh.status
        )
        session.add(db_nh)
        
    session.commit()
    session.refresh(db_form)
    return db_form
