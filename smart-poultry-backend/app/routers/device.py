import uuid
from typing import Annotated
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Header, Response, status
from sqlmodel import Session, select

from app.config import settings
from app.database import get_session
from app.models.enums import JenisNotifikasi, StatusAlat, StatusPerintah
from app.models.fisik import Alat
from app.models.operasional import Perintah
from app.schemas.perintah import (
    DeviceHeartbeatRequest, DeviceHeartbeatResponse, DeviceLogRequest,
    DeviceConfig, LogEksekusiPublic, PerintahPublic
)
from app.services.notifikasi import notify
from app.services.perintah import expire_perintah, ubah_status


router = APIRouter(tags=["Simulator Alat (IoT)"])


def get_device_by_token(
    x_device_token: str = Header(...),
    session: Session = Depends(get_session)
) -> Alat:
    alat = session.exec(select(Alat).where(Alat.device_token == x_device_token)).first()
    if not alat:
        raise HTTPException(status_code=401, detail="Invalid Device Token")
    return alat


def _get_perintah_alat_or_404(session: Session, alat: Alat, perintah_id: uuid.UUID) -> Perintah:
    perintah = session.get(Perintah, perintah_id)
    if not perintah or perintah.alat_id != alat.id:
        raise HTTPException(status_code=404, detail="Perintah tidak ditemukan")
    return perintah


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
    if req.status == StatusAlat.ERROR and alat.status != StatusAlat.ERROR:
        notify(session, alat.kandang_id, JenisNotifikasi.ALAT_ERROR,
               "Alat error", "Alat melaporkan status ERROR.")
    alat.status = req.status
    alat.waktu_terakhir_sinkron = datetime.now(timezone.utc)
    session.add(alat)
    session.commit()

    expire_perintah(session, alat)

    perintah_pending = session.exec(
        select(Perintah).where(
            Perintah.alat_id == alat.id,
            Perintah.status == StatusPerintah.PENDING
        ).order_by(Perintah.dibuat_pada.asc())
    ).first()

    return DeviceHeartbeatResponse(
        perintah_pending=perintah_pending,
        config=DeviceConfig(heartbeat_interval_seconds=settings.device_heartbeat_interval_seconds)
    )


@router.post("/device/perintah/{id}/ambil", response_model=PerintahPublic)
def ambil_perintah(
    id: uuid.UUID,
    alat: Annotated[Alat, Depends(get_device_by_token)],
    session: Annotated[Session, Depends(get_session)]
):
    perintah = _get_perintah_alat_or_404(session, alat, id)
    if perintah.status != StatusPerintah.DIAMBIL:  # DIAMBIL lagi = pengiriman ulang, idempoten
        ubah_status(perintah, StatusPerintah.DIAMBIL)
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
    perintah = _get_perintah_alat_or_404(session, alat, id)
    if perintah.status != StatusPerintah.BERJALAN:  # BERJALAN lagi = pengiriman ulang, idempoten
        ubah_status(perintah, StatusPerintah.BERJALAN)
        session.add(perintah)
        session.commit()
        session.refresh(perintah)
    return perintah


@router.post("/device/perintah/{id}/log", response_model=LogEksekusiPublic, status_code=status.HTTP_201_CREATED)
def kirim_log_eksekusi(
    id: uuid.UUID,
    req: DeviceLogRequest,
    response: Response,
    alat: Annotated[Alat, Depends(get_device_by_token)],
    session: Annotated[Session, Depends(get_session)]
):
    """201 untuk log baru; 200 (log yang sama) bila id_eksekusi_unik dikirim ulang."""
    perintah = _get_perintah_alat_or_404(session, alat, id)

    from app.services.device import proses_log_eksekusi
    log, baru = proses_log_eksekusi(session, alat, perintah, req)
    if not baru:
        response.status_code = status.HTTP_200_OK
    return log
