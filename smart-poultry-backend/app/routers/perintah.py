import uuid
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.database import get_session
from app.models.akses import User
from app.models.enums import TipePerintah, StatusPerintah, StatusAlat
from app.models.fisik import Alat
from app.models.operasional import Perintah
from app.schemas.perintah import (
    PerintahBeriMakanRequest, PerintahPublic, PerintahDetailPublic
)
from app.services.auth import get_current_user
from app.routers.kandang import _get_kandang_or_404

router = APIRouter(tags=["Perintah Manual"])


@router.post("/kandang/{id}/perintah/beri-makan", response_model=PerintahPublic, status_code=status.HTTP_201_CREATED)
def beri_makan_manual(
    id: uuid.UUID,
    req: PerintahBeriMakanRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
):
    _get_kandang_or_404(session, id, current_user)
    
    alat = session.exec(select(Alat).where(Alat.kandang_id == id)).first()
    if not alat:
        raise HTTPException(status_code=400, detail="Kandang ini belum memiliki Alat IoT")
        
    if alat.status == StatusAlat.OFFLINE:
        raise HTTPException(status_code=409, detail="Alat sedang OFFLINE")
        
    # Cek apakah ada perintah yang masih PENDING atau BERJALAN
    active_perintah = session.exec(
        select(Perintah).where(
            Perintah.alat_id == alat.id,
            Perintah.status.in_([StatusPerintah.PENDING, StatusPerintah.DIAMBIL, StatusPerintah.BERJALAN])
        )
    ).first()
    
    if active_perintah:
        raise HTTPException(status_code=409, detail="Alat sedang memproses perintah lain")
        
    perintah = Perintah(
        alat_id=alat.id,
        dibuat_oleh_id=current_user.id,
        formulasi_id=req.formulasi_id,
        tipe=TipePerintah.BERI_MAKAN,
        status=StatusPerintah.PENDING
    )
    session.add(perintah)
    session.commit()
    session.refresh(perintah)
    
    return perintah


@router.post("/kandang/{id}/perintah/stop-darurat", response_model=PerintahPublic, status_code=status.HTTP_201_CREATED)
def stop_darurat(
    id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
):
    _get_kandang_or_404(session, id, current_user)
    
    alat = session.exec(select(Alat).where(Alat.kandang_id == id)).first()
    if not alat:
        raise HTTPException(status_code=400, detail="Kandang ini belum memiliki Alat IoT")
        
    perintah = Perintah(
        alat_id=alat.id,
        dibuat_oleh_id=current_user.id,
        formulasi_id=None,
        tipe=TipePerintah.STOP_DARURAT,
        status=StatusPerintah.PENDING
    )
    session.add(perintah)
    session.commit()
    session.refresh(perintah)
    
    return perintah


@router.get("/perintah/{id}", response_model=PerintahDetailPublic)
def detail_perintah(
    id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
):
    perintah = session.get(Perintah, id)
    if not perintah:
        raise HTTPException(status_code=404, detail="Perintah tidak ditemukan")
        
    alat = session.get(Alat, perintah.alat_id)
    # Validasi akses
    _get_kandang_or_404(session, alat.kandang_id, current_user)
    
    return perintah


@router.get("/kandang/{id}/perintah", response_model=List[PerintahPublic])
def riwayat_perintah(
    id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
):
    _get_kandang_or_404(session, id, current_user)
    
    alat = session.exec(select(Alat).where(Alat.kandang_id == id)).first()
    if not alat:
        return []
        
    return session.exec(
        select(Perintah)
        .where(Perintah.alat_id == alat.id)
        .order_by(Perintah.dibuat_pada.desc())
    ).all()
