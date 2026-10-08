import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models.enums import JenisTransaksi


class IsiUlangStokRequest(BaseModel):
    jumlah: float


class KoreksiStokRequest(BaseModel):
    jumlah_baru: float
    alasan: str


class StokPublic(BaseModel):
    id: uuid.UUID
    wadah_id: uuid.UUID
    jumlah_estimasi: float
    ambang_menipis: Optional[float] = None
    nama_bahan: Optional[str] = None # Akan diisi secara manual saat query

    class Config:
        from_attributes = True


class TransaksiStokPublic(BaseModel):
    id: uuid.UUID
    wadah_id: uuid.UUID
    dilakukan_oleh_id: uuid.UUID
    jenis: JenisTransaksi
    jumlah: float
    alasan: Optional[str] = None
    dibuat_pada: datetime

    class Config:
        from_attributes = True
