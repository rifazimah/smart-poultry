import uuid
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.database import get_session
from app.models.akses import User
from app.models.enums import StatusFormulasi
from app.models.operasional import Formulasi, FormulasiItem, FormulasiNutrisiHasil
from app.models.fisik import Alat, Wadah
from app.schemas.formulasi import (
    FormulasiPreview, FormulasiManualRequest, 
    FormulasiLengkapPublic, FormulasiPublic
)
from app.services.auth import get_current_user
from app.services.formulasi import (
    hitung_formulasi_otomatis, hitung_formulasi_manual, FormulasiException
)
from app.routers.siklus import _get_siklus_or_404

router = APIRouter(tags=["Formulasi"])


@router.post("/siklus/{id}/formulasi/otomatis", response_model=FormulasiPreview)
def generate_formulasi_otomatis_endpoint(
    id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
):
    siklus = _get_siklus_or_404(session, id, current_user)
    try:
        preview = hitung_formulasi_otomatis(session, siklus)
        return preview
    except FormulasiException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/siklus/{id}/formulasi/manual", response_model=FormulasiPreview)
def generate_formulasi_manual_endpoint(
    id: uuid.UUID,
    req: FormulasiManualRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
):
    siklus = _get_siklus_or_404(session, id, current_user)
    try:
        preview = hitung_formulasi_manual(session, siklus, req.item)
        return preview
    except FormulasiException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/formulasi", response_model=FormulasiPublic, status_code=status.HTTP_201_CREATED)
def simpan_formulasi(
    siklus_id: uuid.UUID, # dari query atau body? Contract: body `FormulasiPreview` tapi butuh siklus_id.
    preview: FormulasiPreview,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
):
    """
    Menyimpan hasil preview menjadi formulasi resmi (snapshot).
    Catatan: butuh parameter query ?siklus_id=... agar tahu disimpan ke siklus mana.
    """
    siklus = _get_siklus_or_404(session, siklus_id, current_user)
    
    # Validasi wadah: pastikan bahan_pakan_id di item masih terpasang di wadah alat
    alat = session.exec(select(Alat).where(Alat.kandang_id == siklus.kandang_id)).first()
    if not alat:
        raise HTTPException(status_code=400, detail="Kandang tidak memiliki alat IoT")
        
    wadah_list = session.exec(select(Wadah).where(Wadah.alat_id == alat.id)).all()
    bahan_terpasang = {w.bahan_pakan_id for w in wadah_list if w.bahan_pakan_id is not None}
    
    for item in preview.item:
        if item.bahan_pakan_id not in bahan_terpasang:
            raise HTTPException(
                status_code=409, 
                detail=f"Bahan pakan {item.nama_bahan} sudah dilepas dari wadah sejak preview dibuat."
            )
            
    # Nonaktifkan formulasi lama yang aktif
    old_formulas = session.exec(
        select(Formulasi).where(
            Formulasi.siklus_id == siklus_id,
            Formulasi.status.in_([StatusFormulasi.AKTIF, StatusFormulasi.PERLU_DITINJAU])
        )
    ).all()
    for f in old_formulas:
        f.status = StatusFormulasi.NONAKTIF
        session.add(f)
        
    # Buat Formulasi baru
    db_form = Formulasi(
        siklus_id=siklus_id,
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


@router.get("/siklus/{id}/formulasi", response_model=List[FormulasiPublic])
def riwayat_formulasi(
    id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
):
    _get_siklus_or_404(session, id, current_user)
    
    return session.exec(
        select(Formulasi)
        .where(Formulasi.siklus_id == id)
        .order_by(Formulasi.dibuat_pada.desc())
    ).all()


@router.get("/formulasi/{id}", response_model=FormulasiLengkapPublic)
def get_formulasi_lengkap(
    id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
):
    form = session.get(Formulasi, id)
    if not form:
        raise HTTPException(status_code=404, detail="Formulasi tidak ditemukan")
        
    _get_siklus_or_404(session, form.siklus_id, current_user)
    return form
