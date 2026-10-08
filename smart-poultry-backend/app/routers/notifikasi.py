import uuid
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.database import get_session
from app.models.akses import User
from app.models.enums import StatusNotifikasi
from app.models.operasional import Notifikasi
from app.schemas.notifikasi import NotifikasiPublic
from app.services.auth import get_current_user

router = APIRouter(tags=["Notifikasi"])


@router.get("/notifikasi", response_model=List[NotifikasiPublic])
def list_notifikasi(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    status: Optional[StatusNotifikasi] = None
):
    query = select(Notifikasi).where(Notifikasi.user_id == current_user.id)
    if status:
        query = query.where(Notifikasi.status == status)
        
    query = query.order_by(Notifikasi.dibuat_pada.desc())
    return session.exec(query).all()


@router.patch("/notifikasi/baca-semua", status_code=status.HTTP_204_NO_CONTENT)
def baca_semua_notifikasi(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
):
    notif_belum_dibaca = session.exec(
        select(Notifikasi).where(
            Notifikasi.user_id == current_user.id,
            Notifikasi.status == StatusNotifikasi.BELUM_DIBACA
        )
    ).all()
    
    for notif in notif_belum_dibaca:
        notif.status = StatusNotifikasi.SUDAH_DIBACA
        session.add(notif)
        
    session.commit()


@router.patch("/notifikasi/{id}/baca", response_model=NotifikasiPublic)
def baca_notifikasi(
    id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
):
    notif = session.get(Notifikasi, id)
    if not notif or notif.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notifikasi tidak ditemukan")
        
    notif.status = StatusNotifikasi.SUDAH_DIBACA
    session.add(notif)
    session.commit()
    session.refresh(notif)
    
    return notif
