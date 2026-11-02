import uuid
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlmodel import Session, select

from app.database import get_session
from app.models.akses import User, PenugasanKandang
from app.models.fisik import Kandang
from app.models.enums import PeranUser, StatusPenugasan
from app.schemas.user import (
    UserPublic, 
    UserCreate, 
    UserStatusUpdate, 
    PenugasanKandangCreate, 
    PenugasanKandangPublic,
    PenugasanDetailPublic,
)
from app.routers.kandang import _get_kandang_or_404
from app.services.audit import catat_audit
from app.services.auth import get_current_pemilik, get_password_hash
from app.services.paginasi import Paginasi, terapkan

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
    response: Response,
    p: Annotated[Paginasi, Depends()],
):
    """Mendapatkan daftar pekerja (hanya Pemilik)."""
    query = select(User).where(
        User.role == PeranUser.PEKERJA,
        User.pemilik_id == current_pemilik.id,
    ).order_by(User.nama, User.id)
    return terapkan(session, response, query, p)


@router.patch("/users/{id}/status", response_model=UserPublic)
def update_user_status(
    id: uuid.UUID,
    status_update: UserStatusUpdate,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)],
):
    """Mengubah status pekerja (misal: dinonaktifkan). Hanya Pemilik."""
    user = _get_pekerja_or_404(session, id, current_pemilik)
    lama = user.status.value
    user.status = status_update.status
    catat_audit(session, current_pemilik.id, "UBAH_STATUS_USER", "user", user.id,
                nilai_lama=lama, nilai_baru=status_update.status.value)
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
    session.flush()
    catat_audit(session, current_pemilik.id, "BUAT_PENUGASAN", "penugasan_kandang", penugasan.id,
                nilai_baru=f"user={pekerja.id} kandang={penugasan.kandang_id}")
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
    catat_audit(session, current_pemilik.id, "AKHIRI_PENUGASAN", "penugasan_kandang", penugasan.id,
                nilai_lama="AKTIF", nilai_baru="BERAKHIR")
    session.commit()


def _penugasan_detail(session: Session, rows: List[PenugasanKandang]) -> List[PenugasanDetailPublic]:
    if not rows:
        return []
    users = {u.id: u for u in session.exec(select(User).where(User.id.in_({r.user_id for r in rows}))).all()}
    kandang = {k.id: k for k in session.exec(select(Kandang).where(Kandang.id.in_({r.kandang_id for r in rows}))).all()}
    return [
        PenugasanDetailPublic(
            id=r.id, user_id=r.user_id, kandang_id=r.kandang_id, tanggal_mulai=r.tanggal_mulai, status=r.status,
            nama_pekerja=users[r.user_id].nama, email_pekerja=users[r.user_id].email,
            nama_kandang=kandang[r.kandang_id].nama,
        )
        for r in rows
    ]


@router.get("/kandang/{id}/penugasan", response_model=List[PenugasanDetailPublic])
def list_penugasan_kandang(
    id: uuid.UUID,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)],
    response: Response,
    p: Annotated[Paginasi, Depends()],
    status_penugasan: Annotated[Optional[StatusPenugasan], Query(alias="status")] = None,
):
    """Pekerja yang ditugaskan (atau pernah) di sebuah kandang. Filter `?status=AKTIF|BERAKHIR`."""
    _get_kandang_or_404(session, id, current_pemilik)
    query = select(PenugasanKandang).where(PenugasanKandang.kandang_id == id)
    if status_penugasan:
        query = query.where(PenugasanKandang.status == status_penugasan)
    query = query.order_by(PenugasanKandang.tanggal_mulai.desc(), PenugasanKandang.id)
    return _penugasan_detail(session, terapkan(session, response, query, p))


@router.get("/users/{id}/penugasan", response_model=List[PenugasanDetailPublic])
def list_penugasan_pekerja(
    id: uuid.UUID,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)],
    response: Response,
    p: Annotated[Paginasi, Depends()],
    status_penugasan: Annotated[Optional[StatusPenugasan], Query(alias="status")] = None,
):
    """Kandang yang ditugaskan (atau pernah) kepada seorang Pekerja. Filter `?status=AKTIF|BERAKHIR`."""
    pekerja = _get_pekerja_or_404(session, id, current_pemilik)
    query = select(PenugasanKandang).where(PenugasanKandang.user_id == pekerja.id)
    if status_penugasan:
        query = query.where(PenugasanKandang.status == status_penugasan)
    query = query.order_by(PenugasanKandang.tanggal_mulai.desc(), PenugasanKandang.id)
    return _penugasan_detail(session, terapkan(session, response, query, p))
