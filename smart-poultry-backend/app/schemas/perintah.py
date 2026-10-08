import uuid
from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel
from app.models.enums import TipePerintah, StatusPerintah, StatusEksekusi, StatusAlat


class PerintahBeriMakanRequest(BaseModel):
    formulasi_id: uuid.UUID


class LogEksekusiPublic(BaseModel):
    id: uuid.UUID
    perintah_id: uuid.UUID
    id_eksekusi_unik: uuid.UUID
    berat_aktual: Optional[float] = None
    status: StatusEksekusi
    dilaporkan_pada: datetime

    class Config:
        from_attributes = True


class PerintahPublic(BaseModel):
    id: uuid.UUID
    alat_id: uuid.UUID
    dibuat_oleh_id: uuid.UUID
    formulasi_id: Optional[uuid.UUID] = None
    tipe: TipePerintah
    command_id: uuid.UUID
    status: StatusPerintah
    dibuat_pada: datetime

    class Config:
        from_attributes = True


class PerintahDetailPublic(PerintahPublic):
    log_eksekusi: Optional[LogEksekusiPublic] = None


# --- DEVICE INTERFACE SCHEMAS ---

class DeviceHeartbeatRequest(BaseModel):
    status: StatusAlat


class DeviceConfig(BaseModel):
    heartbeat_interval_seconds: int


class DeviceHeartbeatResponse(BaseModel):
    perintah_pending: Optional[PerintahPublic]
    config: DeviceConfig


class DeviceLogRequest(BaseModel):
    id_eksekusi_unik: uuid.UUID
    berat_aktual: Optional[float] = None
    status: StatusEksekusi
