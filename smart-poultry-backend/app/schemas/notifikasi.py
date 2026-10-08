import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.enums import JenisNotifikasi, StatusNotifikasi

class NotifikasiPublic(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    jenis: JenisNotifikasi
    judul: str
    pesan: str
    status: StatusNotifikasi
    dibuat_pada: datetime

    class Config:
        from_attributes = True
