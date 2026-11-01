import uuid
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.database import get_session
from app.models.akses import User, PenugasanKandang
from app.models.enums import PeranUser, StatusPenugasan
from app.schemas.user import (
    UserPublic, 
    UserCreate, 
    UserStatusUpdate, 
    PenugasanKandangCreate, 
    PenugasanKandangPublic
)
from app.routers.kandang import _get_kandang_or_404
from app.services.auth import get_current_pemilik, get_password_hash

# Kita buat 2 prefix yang berbeda sesuai API Contract
router = APIRouter(tags=["User & Penugasan"])


def _get_pekerja_or_404(session: Session, user_id: uuid.UUID, pemilik: User) -> User:
    """Pekerja harus milik Pemilik yang login."""
    pekerja = session.get(User, user_id)
    if not pekerja or pekerja.role != PeranUser.PEKERJA or pekerja.pemilik_id != pemilik.id:
        raise HTTPException(status_code=404, detail="Pekerja tidak ditemukan")
    return pekerja


@router.post("/users", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: UserCreate,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)],
):
    """
    Membuat user baru. Hanya Pemilik yang dapat membuat user,
    dan role yang dibuat harus PEKERJA.
    """
    if user_in.role != PeranUser.PEKERJA:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hanya dapat membuat user dengan role PEKERJA",
        )
        
    # Cek email sudah ada atau belum
    existing_user = session.exec(select(User).where(User.email == user_in.email)).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email sudah terdaftar",
        )
        
    db_user = User(
        nama=user_in.nama,
        email=user_in.email,
        kata_sandi_hash=get_password_hash(user_in.kata_sandi),
        role=user_in.role,
        pemilik_id=current_pemilik.id,
    )

    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    
    return db_user


@router.get("/users", response_model=List[UserPublic])
def get_users(
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)],
):
    """Mendapatkan daftar pekerja (hanya Pemilik)."""
    return session.exec(
        select(User).where(
            User.role == PeranUser.PEKERJA,
            User.pemilik_id == current_pemilik.id,
        )
    ).all()


@router.patch("/users/{id}/status", response_model=UserPublic)
def update_user_status(
    id: uuid.UUID,
    status_update: UserStatusUpdate,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)],
):
    """Mengubah status pekerja (misal: dinonaktifkan). Hanya Pemilik."""
    user = _get_pekerja_or_404(session, id, current_pemilik)
    user.status = status_update.status
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@router.post("/users/{id}/penugasan", response_model=PenugasanKandangPublic, status_code=status.HTTP_201_CREATED)
def buat_penugasan(
    id: uuid.UUID,
    penugasan_in: PenugasanKandangCreate,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)],
):
    """Menugaskan Pekerja ke sebuah Kandang."""
    pekerja = _get_pekerja_or_404(session, id, current_pemilik)
    _get_kandang_or_404(session, penugasan_in.kandang_id, current_pemilik)

    sudah_ada = session.exec(
        select(PenugasanKandang).where(
            PenugasanKandang.user_id == pekerja.id,
            PenugasanKandang.kandang_id == penugasan_in.kandang_id,
            PenugasanKandang.status == StatusPenugasan.AKTIF,
        )
    ).first()
    if sudah_ada:
        raise HTTPException(status_code=409, detail="Pekerja sudah ditugaskan ke kandang ini")

    penugasan = PenugasanKandang(
        user_id=pekerja.id,
        kandang_id=penugasan_in.kandang_id,
        tanggal_mulai=penugasan_in.tanggal_mulai,
        status=StatusPenugasan.AKTIF
    )
    session.add(penugasan)
    session.commit()
    session.refresh(penugasan)
    return penugasan


@router.delete("/penugasan/{id}", status_code=status.HTTP_204_NO_CONTENT)
def akhiri_penugasan(
    id: uuid.UUID,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)],
):
    """Mengakhiri penugasan (soft delete / set status BERAKHIR)."""
    penugasan = session.get(PenugasanKandang, id)
    if not penugasan:
        raise HTTPException(status_code=404, detail="Penugasan tidak ditemukan")
    _get_kandang_or_404(session, penugasan.kandang_id, current_pemilik)

    penugasan.status = StatusPenugasan.BERAKHIR
    session.add(penugasan)
    session.commit()
