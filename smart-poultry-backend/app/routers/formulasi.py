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
    preview: FormulasiPreview,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
):
    """
    Menyimpan hasil preview menjadi formulasi resmi (snapshot).
    """
    try:
        from app.services.formulasi import simpan_formulasi_service
        return simpan_formulasi_service(session, preview, current_user)
    except FormulasiException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


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
