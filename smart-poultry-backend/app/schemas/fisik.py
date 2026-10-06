import uuid
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

from app.models.enums import StatusKandang, StatusAlat


class KandangCreate(BaseModel):
    nama: str
    lokasi: Optional[str] = None


class KandangUpdate(BaseModel):
    nama: Optional[str] = None
    lokasi: Optional[str] = None
    status: Optional[StatusKandang] = None


class KandangPublic(BaseModel):
    id: uuid.UUID
    pemilik_id: uuid.UUID
    nama: str
    lokasi: Optional[str] = None
    status: StatusKandang

    class Config:
        from_attributes = True


class AlatPublic(BaseModel):
    id: uuid.UUID
    kandang_id: uuid.UUID
    status: StatusAlat
    versi_jadwal_aktif: Optional[int] = None
    waktu_terakhir_sinkron: Optional[datetime] = None

    class Config:
        from_attributes = True


class AlatWithToken(AlatPublic):
    device_token: str


class TokenRotasiResponse(BaseModel):
    device_token: str


class WadahCreate(BaseModel):
    nomor_wadah: int
    bahan_pakan_id: Optional[uuid.UUID] = None


class WadahUpdate(BaseModel):
    bahan_pakan_id: Optional[uuid.UUID] = None


class WadahPublic(BaseModel):
    id: uuid.UUID
    alat_id: uuid.UUID
    nomor_wadah: int
    bahan_pakan_id: Optional[uuid.UUID] = None

    class Config:
        from_attributes = True
