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
from app.services.auth import get_current_pemilik, get_password_hash

# Kita buat 2 prefix yang berbeda sesuai API Contract
router = APIRouter(tags=["User & Penugasan"])


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
    # Untuk MVP, kita ambil semua PEKERJA, 
    # karena saat ini tidak ada relasi langsung Pemilik->Pekerja di tabel User.
    # Jika diinginkan hanya pekerja tertentu, relasinya perlu ditambahkan.
    pekerja_list = session.exec(
        select(User).where(User.role == PeranUser.PEKERJA)
    ).all()
    
    return pekerja_list


@router.patch("/users/{id}/status", response_model=UserPublic)
def update_user_status(
    id: uuid.UUID,
    status_update: UserStatusUpdate,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)],
):
    """Mengubah status pekerja (misal: dinonaktifkan). Hanya Pemilik."""
    user = session.get(User, id)
    if not user or user.role != PeranUser.PEKERJA:
        raise HTTPException(status_code=404, detail="Pekerja tidak ditemukan")
        
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
    # Verifikasi pekerja ada
    pekerja = session.get(User, id)
    if not pekerja or pekerja.role != PeranUser.PEKERJA:
        raise HTTPException(status_code=404, detail="Pekerja tidak ditemukan")
        
    # Verifikasi kandang (dan milik pemilik ini) - di-skip detailnya untuk MVP, tapi idealnya dicek
    # ...
    
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
        
    penugasan.status = StatusPenugasan.BERAKHIR
    session.add(penugasan)
    session.commit()
