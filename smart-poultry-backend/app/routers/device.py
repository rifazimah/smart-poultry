import uuid
from typing import Annotated
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlmodel import Session, select

from app.database import get_session
from app.models.enums import StatusPerintah, JenisTransaksi, StatusNotifikasi, JenisNotifikasi
from app.models.fisik import Alat, Stok, TransaksiStok, Wadah
from app.models.operasional import Perintah, LogEksekusi, FormulasiItem, Notifikasi
from app.schemas.perintah import (
    DeviceHeartbeatRequest, DeviceHeartbeatResponse, DeviceLogRequest, 
    DeviceConfig, PerintahPublic
)


router = APIRouter(tags=["Simulator Alat (IoT)"])


def get_device_by_token(
    x_device_token: str = Header(...), 
    session: Session = Depends(get_session)
) -> Alat:
    alat = session.exec(select(Alat).where(Alat.device_token == x_device_token)).first()
    if not alat:
        raise HTTPException(status_code=401, detail="Invalid Device Token")
    return alat


@router.post("/device/heartbeat", response_model=DeviceHeartbeatResponse)
def device_heartbeat(
    req: DeviceHeartbeatRequest,
    alat: Annotated[Alat, Depends(get_device_by_token)],
    session: Annotated[Session, Depends(get_session)]
):
    """
    Heartbeat dari alat. Update status ONLINE/ERROR dan kembalikan
    perintah yang PENDING (jika ada).
    """
    alat.status = req.status
    alat.waktu_terakhir_sinkron = datetime.now(timezone.utc)
    session.add(alat)
    
    perintah_pending = session.exec(
        select(Perintah).where(
            Perintah.alat_id == alat.id,
            Perintah.status == StatusPerintah.PENDING
        ).order_by(Perintah.dibuat_pada.asc())
    ).first()
    
    session.commit()
    
    return DeviceHeartbeatResponse(
        perintah_pending=perintah_pending,
        config=DeviceConfig(heartbeat_interval_seconds=10) # 10 detik default untuk MVP
    )


@router.post("/device/perintah/{id}/ambil", response_model=PerintahPublic)
def ambil_perintah(
    id: uuid.UUID,
    alat: Annotated[Alat, Depends(get_device_by_token)],
    session: Annotated[Session, Depends(get_session)]
):
    perintah = session.get(Perintah, id)
    if not perintah or perintah.alat_id != alat.id:
        raise HTTPException(status_code=404, detail="Perintah tidak ditemukan")
        
    if perintah.status == StatusPerintah.PENDING:
        perintah.status = StatusPerintah.DIAMBIL
        session.add(perintah)
        session.commit()
        session.refresh(perintah)
        
    return perintah


@router.post("/device/perintah/{id}/mulai", response_model=PerintahPublic)
def mulai_perintah(
    id: uuid.UUID,
    alat: Annotated[Alat, Depends(get_device_by_token)],
    session: Annotated[Session, Depends(get_session)]
):
    perintah = session.get(Perintah, id)
    if not perintah or perintah.alat_id != alat.id:
        raise HTTPException(status_code=404, detail="Perintah tidak ditemukan")
        
    if perintah.status in [StatusPerintah.PENDING, StatusPerintah.DIAMBIL]:
        perintah.status = StatusPerintah.BERJALAN
        session.add(perintah)
        session.commit()
        session.refresh(perintah)
        
    return perintah


@router.post("/device/perintah/{id}/log", status_code=status.HTTP_201_CREATED)
def kirim_log_eksekusi(
    id: uuid.UUID,
    req: DeviceLogRequest,
    alat: Annotated[Alat, Depends(get_device_by_token)],
    session: Annotated[Session, Depends(get_session)]
):
    perintah = session.get(Perintah, id)
    if not perintah or perintah.alat_id != alat.id:
        raise HTTPException(status_code=404, detail="Perintah tidak ditemukan")
        
    from app.services.device import proses_log_eksekusi
    return proses_log_eksekusi(session, alat, perintah, req)
