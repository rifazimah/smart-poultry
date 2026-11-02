import uuid
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session, select

from app.database import get_session
from app.models.akses import User
from app.models.enums import TipePerintah, StatusPerintah, StatusAlat, JenisNotifikasi
from app.models.fisik import Alat
from app.models.operasional import Perintah
from app.schemas.perintah import (
    PerintahBeriMakanRequest, PerintahPublic, PerintahDetailPublic
)
from app.services.auth import get_current_user
from app.services.notifikasi import notify
from app.services.paginasi import Paginasi, terapkan
from app.services.perintah import (
    batalkan_perintah_aktif, deteksi_offline, expire_perintah, validasi_formulasi_untuk_beri_makan,
)
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
        raise HTTPException(status_code=409, detail="Kandang ini belum memiliki Alat IoT")
        
    expire_perintah(session, alat)
    if deteksi_offline(session, alat) == StatusAlat.OFFLINE:
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

    validasi_formulasi_untuk_beri_makan(session, id, alat, req.formulasi_id)

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
        raise HTTPException(status_code=409, detail="Kandang ini belum memiliki Alat IoT")

    # Selalu boleh dikirim (walau alat offline); perintah yang sedang aktif dibatalkan.
    batalkan_perintah_aktif(session, alat)
    notify(session, id, JenisNotifikasi.PERINTAH_GAGAL,
           "Stop darurat", f"Stop darurat dikirim oleh {current_user.nama}.")

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

    expire_perintah(session, alat)
    session.refresh(perintah)
    return perintah


@router.get("/kandang/{id}/perintah", response_model=List[PerintahPublic])
def riwayat_perintah(
    id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    response: Response,
    p: Annotated[Paginasi, Depends()],
):
    _get_kandang_or_404(session, id, current_user)

    alat = session.exec(select(Alat).where(Alat.kandang_id == id)).first()
    if not alat:
        response.headers["X-Total-Count"] = "0"
        return []

    expire_perintah(session, alat)
    return terapkan(
        session, response,
        select(Perintah).where(Perintah.alat_id == alat.id).order_by(Perintah.dibuat_pada.desc(), Perintah.id),
        p,
    )
