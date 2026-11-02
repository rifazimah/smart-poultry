import uuid
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session, select

from app.database import get_session
from app.models.akses import User
from app.models.enums import StatusFormulasi
from app.models.operasional import Formulasi, FormulasiItem, FormulasiNutrisiHasil
from app.models.fisik import Alat, Wadah
from app.models.masterdata import BahanPakan, Nutrisi
from app.schemas.formulasi import (
    FormulasiPreview, FormulasiManualRequest, 
    FormulasiLengkapPublic, FormulasiPublic
)
from app.services.auth import get_current_pemilik, get_current_user
from app.services.paginasi import Paginasi, terapkan
from app.services.formulasi import (
    hitung_formulasi_otomatis, hitung_formulasi_manual, FormulasiException
)
from app.routers.siklus import _get_siklus_or_404

router = APIRouter(tags=["Formulasi"])


@router.post("/siklus/{id}/formulasi/otomatis", response_model=FormulasiPreview)
def generate_formulasi_otomatis_endpoint(
    id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_pemilik)],
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
    current_user: Annotated[User, Depends(get_current_pemilik)],
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
    current_user: Annotated[User, Depends(get_current_pemilik)],
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
    session: Annotated[Session, Depends(get_session)],
    response: Response,
    p: Annotated[Paginasi, Depends()],
):
    _get_siklus_or_404(session, id, current_user)

    return terapkan(
        session, response,
        select(Formulasi).where(Formulasi.siklus_id == id).order_by(Formulasi.dibuat_pada.desc(), Formulasi.id),
        p,
    )


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

    lengkap = FormulasiLengkapPublic.model_validate(form)
    nama_bahan = {
        b.id: b.nama
        for b in session.exec(select(BahanPakan).where(BahanPakan.id.in_([i.bahan_pakan_id for i in lengkap.item]))).all()
    } if lengkap.item else {}
    nutrisi = {
        n.id: n
        for n in session.exec(select(Nutrisi).where(Nutrisi.id.in_([h.nutrisi_id for h in lengkap.nutrisi_hasil]))).all()
    } if lengkap.nutrisi_hasil else {}
    for i in lengkap.item:
        i.nama_bahan = nama_bahan.get(i.bahan_pakan_id)
    for h in lengkap.nutrisi_hasil:
        n = nutrisi.get(h.nutrisi_id)
        h.nama_nutrisi = n.nama if n else None
        h.satuan = n.satuan if n else None
    return lengkap


@router.delete("/formulasi/{id}", status_code=status.HTTP_204_NO_CONTENT)
def hapus_formulasi(
    id: uuid.UUID,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)]
):
    """Hapus formulasi percobaan/salah. Ditolak bila sudah dipakai perintah (riwayat)."""
    from sqlalchemy import func
    from app.models.operasional import Perintah
    from app.services.audit import catat_audit

    form = session.get(Formulasi, id)
    if not form:
        raise HTTPException(status_code=404, detail="Formulasi tidak ditemukan")
    _get_siklus_or_404(session, form.siklus_id, current_pemilik)

    n = session.exec(select(func.count()).select_from(Perintah).where(Perintah.formulasi_id == id)).one()
    if n:
        raise HTTPException(status_code=409, detail=f"Tidak dapat menghapus formulasi: sudah dipakai {n} perintah")

    catat_audit(session, current_pemilik.id, "HAPUS_FORMULASI", "formulasi", form.id,
                nilai_lama=f"mode={form.mode.value}, status={form.status.value}, aktif={form.aktif}")
    session.delete(form)  # item & hasil nutrisi ikut terhapus
    session.commit()
