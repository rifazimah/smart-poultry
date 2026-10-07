import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.database import get_session
from app.models.akses import User
from app.models.enums import StatusSiklus, JenisPerubahan, StatusFormulasi
from app.models.fisik import Kandang
from app.models.operasional import SiklusKandang, PerubahanPopulasi, Formulasi
from app.models.masterdata import JenisAyam, Fase
from app.schemas.operasional import (
    SiklusKandangCreate, SiklusKandangUpdateFase, SiklusKandangPublic,
    PerubahanPopulasiCreate, PerubahanPopulasiPublic
)
from app.services.auth import get_current_user
from app.routers.kandang import _get_kandang_or_404

router = APIRouter(tags=["Siklus & Populasi"])


def _get_siklus_or_404(session: Session, siklus_id: uuid.UUID, user: User) -> SiklusKandang:
    siklus = session.get(SiklusKandang, siklus_id)
    if not siklus:
        raise HTTPException(status_code=404, detail="Siklus tidak ditemukan")
    
    # Verifikasi hak akses lewat kandang
    _get_kandang_or_404(session, siklus.kandang_id, user)
    return siklus


@router.post("/kandang/{id}/siklus", response_model=SiklusKandangPublic, status_code=status.HTTP_201_CREATED)
def create_siklus(
    id: uuid.UUID,
    siklus_in: SiklusKandangCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
):
    """Memulai siklus baru di sebuah kandang. Ditolak jika masih ada siklus aktif."""
    kandang = _get_kandang_or_404(session, id, current_user)
    
    # Cek apakah ada siklus aktif
    active_siklus = session.exec(
        select(SiklusKandang).where(
            SiklusKandang.kandang_id == id,
            SiklusKandang.status == StatusSiklus.AKTIF
        )
    ).first()
    if active_siklus:
        raise HTTPException(status_code=409, detail="Kandang masih memiliki siklus aktif")
        
    # Validasi master data
    jenis = session.get(JenisAyam, siklus_in.jenis_ayam_id)
    if not jenis:
        raise HTTPException(status_code=404, detail="Jenis Ayam tidak ditemukan")
        
    fase = session.get(Fase, siklus_in.fase_id)
    if not fase or fase.jenis_ayam_id != jenis.id:
        raise HTTPException(status_code=400, detail="Fase tidak valid untuk Jenis Ayam ini")
        
    new_siklus = SiklusKandang(
        kandang_id=id,
        jenis_ayam_id=siklus_in.jenis_ayam_id,
        fase_id=siklus_in.fase_id,
        jumlah_ayam=siklus_in.jumlah_ayam,
        tanggal_mulai=siklus_in.tanggal_mulai,
        status=StatusSiklus.AKTIF
    )
    
    session.add(new_siklus)
    session.commit()
    session.refresh(new_siklus)
    return new_siklus


@router.get("/kandang/{id}/siklus/aktif", response_model=Optional[SiklusKandangPublic])
def get_active_siklus(
    id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
):
    """Mendapatkan siklus yang sedang aktif di suatu kandang (bisa null)."""
    _get_kandang_or_404(session, id, current_user)
    
    active_siklus = session.exec(
        select(SiklusKandang).where(
            SiklusKandang.kandang_id == id,
            SiklusKandang.status == StatusSiklus.AKTIF
        )
    ).first()
    
    return active_siklus


@router.patch("/siklus/{id}/fase", response_model=SiklusKandangPublic)
def update_fase_siklus(
    id: uuid.UUID,
    fase_update: SiklusKandangUpdateFase,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
):
    """
    Pindah fase ayam. Formulasi lama akan otomatis ditandai PERLU_DITINJAU
    karena kebutuhan nutrisinya berubah.
    """
    siklus = _get_siklus_or_404(session, id, current_user)
    
    if siklus.status != StatusSiklus.AKTIF:
        raise HTTPException(status_code=400, detail="Siklus sudah selesai")
        
    # Validasi fase baru
    fase_baru = session.get(Fase, fase_update.fase_id)
    if not fase_baru or fase_baru.jenis_ayam_id != siklus.jenis_ayam_id:
        raise HTTPException(status_code=400, detail="Fase baru tidak valid")
        
    siklus.fase_id = fase_update.fase_id
    session.add(siklus)
    
    # Tandai formulasi aktif menjadi PERLU_DITINJAU
    active_formulas = session.exec(
        select(Formulasi).where(
            Formulasi.siklus_id == id,
            Formulasi.status == StatusFormulasi.AKTIF
        )
    ).all()
    for f in active_formulas:
        f.status = StatusFormulasi.PERLU_DITINJAU
        session.add(f)
        
    session.commit()
    session.refresh(siklus)
    return siklus


@router.post("/siklus/{id}/populasi", response_model=PerubahanPopulasiPublic, status_code=status.HTTP_201_CREATED)
def catat_perubahan_populasi(
    id: uuid.UUID,
    data_in: PerubahanPopulasiCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
):
    """Mencatat mortalitas, panen, atau penambahan ayam."""
    siklus = _get_siklus_or_404(session, id, current_user)
    
    if siklus.status != StatusSiklus.AKTIF:
        raise HTTPException(status_code=400, detail="Siklus sudah selesai")
        
    perubahan = PerubahanPopulasi(
        siklus_id=id,
        jenis=data_in.jenis,
        jumlah=data_in.jumlah,
        tanggal=data_in.tanggal,
        catatan=data_in.catatan
    )
    session.add(perubahan)
    
    # Update populasi total di siklus
    if data_in.jenis in [JenisPerubahan.MORTALITAS, JenisPerubahan.PANEN]:
        siklus.jumlah_ayam -= data_in.jumlah
    elif data_in.jenis == JenisPerubahan.PENAMBAHAN:
        siklus.jumlah_ayam += data_in.jumlah
        
    if siklus.jumlah_ayam < 0:
        raise HTTPException(status_code=400, detail="Jumlah ayam tidak bisa kurang dari 0")
        
    session.add(siklus)
    session.commit()
    session.refresh(perubahan)
    
    return perubahan


@router.post("/siklus/{id}/selesai", response_model=SiklusKandangPublic)
def akhiri_siklus(
    id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
):
    """Tandai siklus sebagai selesai."""
    siklus = _get_siklus_or_404(session, id, current_user)
    
    if siklus.status != StatusSiklus.AKTIF:
        raise HTTPException(status_code=400, detail="Siklus sudah selesai")
        
    siklus.status = StatusSiklus.SELESAI
    session.add(siklus)
    
    # Matikan formulasi yang aktif
    active_formulas = session.exec(
        select(Formulasi).where(
            Formulasi.siklus_id == id,
            Formulasi.status == StatusFormulasi.AKTIF
        )
    ).all()
    for f in active_formulas:
        f.status = StatusFormulasi.NONAKTIF
        session.add(f)
        
    session.commit()
    session.refresh(siklus)
    return siklus
