import secrets
import uuid
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.database import get_session
from app.models.akses import User, PenugasanKandang
from app.models.fisik import Kandang, Alat, Wadah
from app.models.enums import PeranUser, StatusPenugasan
from app.schemas.fisik import (
    KandangCreate, KandangUpdate, KandangPublic,
    AlatWithToken, TokenRotasiResponse,
    WadahCreate, WadahUpdate, WadahPublic
)
from app.services.auth import get_current_user, get_current_pemilik

router = APIRouter(tags=["Kandang & Alat"])


@router.post("/kandang", response_model=KandangPublic, status_code=status.HTTP_201_CREATED)
def create_kandang(
    kandang_in: KandangCreate,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)],
):
    """Mendaftarkan kandang baru. Hanya Pemilik."""
    kandang = Kandang(
        pemilik_id=current_pemilik.id,
        nama=kandang_in.nama,
        lokasi=kandang_in.lokasi,
    )
    session.add(kandang)
    session.commit()
    session.refresh(kandang)
    return kandang


@router.get("/kandang", response_model=List[KandangPublic])
def list_kandang(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """
    List kandang.
    Jika Pemilik: kembalikan kandang miliknya.
    Jika Pekerja: kembalikan kandang yang ditugaskan kepadanya.
    """
    if current_user.role == PeranUser.PEMILIK:
        statement = select(Kandang).where(Kandang.pemilik_id == current_user.id)
        return session.exec(statement).all()
    else:
        # Pekerja
        statement = (
            select(Kandang)
            .join(PenugasanKandang, PenugasanKandang.kandang_id == Kandang.id)
            .where(
                PenugasanKandang.user_id == current_user.id,
                PenugasanKandang.status == StatusPenugasan.AKTIF
            )
        )
        return session.exec(statement).all()


def _get_kandang_or_404(session: Session, kandang_id: uuid.UUID, user: User) -> Kandang:
    kandang = session.get(Kandang, kandang_id)
    if not kandang:
        raise HTTPException(status_code=404, detail="Kandang tidak ditemukan")
        
    if user.role == PeranUser.PEMILIK:
        if kandang.pemilik_id != user.id:
            raise HTTPException(status_code=403, detail="Tidak berhak mengakses kandang ini")
    else:
        # Pekerja
        assigned = session.exec(
            select(PenugasanKandang).where(
                PenugasanKandang.kandang_id == kandang_id,
                PenugasanKandang.user_id == user.id,
                PenugasanKandang.status == StatusPenugasan.AKTIF
            )
        ).first()
        if not assigned:
            raise HTTPException(status_code=403, detail="Anda tidak ditugaskan ke kandang ini")
            
    return kandang


@router.get("/kandang/{id}", response_model=KandangPublic)
def get_kandang(
    id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Detail kandang. Pemilik & Pekerja yang ditugaskan."""
    kandang = _get_kandang_or_404(session, id, current_user)
    return kandang


@router.patch("/kandang/{id}", response_model=KandangPublic)
def update_kandang(
    id: uuid.UUID,
    kandang_update: KandangUpdate,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)],
):
    """Update kandang. Hanya Pemilik."""
    kandang = _get_kandang_or_404(session, id, current_pemilik)
    
    update_data = kandang_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(kandang, key, value)
        
    session.add(kandang)
    session.commit()
    session.refresh(kandang)
    return kandang


@router.post("/kandang/{id}/alat", response_model=AlatWithToken, status_code=status.HTTP_201_CREATED)
def register_alat(
    id: uuid.UUID,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)],
):
    """
    Mendaftarkan alat IoT ke sebuah kandang.
    device_token di-generate dan HANYA DIKEMBALIKAN SEKALI di endpoint ini.
    """
    kandang = _get_kandang_or_404(session, id, current_pemilik)
    
    # Cek apakah sudah ada alat (karena 1 kandang = max 1 alat di skema kita, unique index)
    existing_alat = session.exec(select(Alat).where(Alat.kandang_id == id)).first()
    if existing_alat:
        raise HTTPException(status_code=400, detail="Kandang ini sudah memiliki Alat IoT")
        
    new_token = secrets.token_hex(32)
    alat = Alat(
        kandang_id=id,
        device_token=new_token,
    )
    
    session.add(alat)
    session.commit()
    session.refresh(alat)
    
    return alat


@router.post("/alat/{id}/rotasi-token", response_model=TokenRotasiResponse)
def rotasi_token_alat(
    id: uuid.UUID,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)],
):
    """Ganti device_token alat dengan yang baru. Hanya Pemilik."""
    alat = session.get(Alat, id)
    if not alat:
        raise HTTPException(status_code=404, detail="Alat tidak ditemukan")
        
    # Validasi kepemilikan alat via kandang
    _get_kandang_or_404(session, alat.kandang_id, current_pemilik)
    
    new_token = secrets.token_hex(32)
    alat.device_token = new_token
    session.add(alat)
    session.commit()
    
    return TokenRotasiResponse(device_token=new_token)


@router.post("/alat/{id}/wadah", response_model=WadahPublic, status_code=status.HTTP_201_CREATED)
def create_wadah(
    id: uuid.UUID,
    wadah_in: WadahCreate,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)],
):
    """Menambahkan wadah pakan ke Alat IoT."""
    alat = session.get(Alat, id)
    if not alat:
        raise HTTPException(status_code=404, detail="Alat tidak ditemukan")
        
    _get_kandang_or_404(session, alat.kandang_id, current_pemilik)
    
    # Cek apakah nomor wadah sudah dipakai di alat ini
    existing_wadah = session.exec(
        select(Wadah).where(Wadah.alat_id == id, Wadah.nomor_wadah == wadah_in.nomor_wadah)
    ).first()
    if existing_wadah:
        raise HTTPException(status_code=400, detail=f"Wadah nomor {wadah_in.nomor_wadah} sudah ada")
        
    wadah = Wadah(
        alat_id=id,
        nomor_wadah=wadah_in.nomor_wadah,
        bahan_pakan_id=wadah_in.bahan_pakan_id
    )
    session.add(wadah)
    session.commit()
    session.refresh(wadah)
    return wadah


@router.patch("/wadah/{id}", response_model=WadahPublic)
def update_wadah(
    id: uuid.UUID,
    wadah_update: WadahUpdate,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)],
):
    """Mapping ulang bahan pakan ke wadah tertentu."""
    wadah = session.get(Wadah, id)
    if not wadah:
        raise HTTPException(status_code=404, detail="Wadah tidak ditemukan")
        
    # Validasi kepemilikan via wadah -> alat -> kandang
    alat = session.get(Alat, wadah.alat_id)
    _get_kandang_or_404(session, alat.kandang_id, current_pemilik)
    
    if wadah_update.bahan_pakan_id is not None:
        wadah.bahan_pakan_id = wadah_update.bahan_pakan_id
        
    session.add(wadah)
    session.commit()
    session.refresh(wadah)
    return wadah
