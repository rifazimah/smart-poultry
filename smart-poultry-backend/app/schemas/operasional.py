import uuid
from datetime import date
from typing import Optional
from pydantic import BaseModel, Field
from app.models.enums import StatusSiklus, JenisPerubahan


# --- SIKLUS KANDANG ---
class SiklusKandangCreate(BaseModel):
    jenis_ayam_id: uuid.UUID
    fase_id: uuid.UUID
    jumlah_ayam: int
    tanggal_mulai: date


class SiklusKandangUpdateFase(BaseModel):
    fase_id: uuid.UUID


class SiklusKandangUpdate(BaseModel):
    """Koreksi data siklus yang salah input (Pemilik)."""
    jumlah_ayam: Optional[int] = Field(default=None, ge=0)
    tanggal_mulai: Optional[date] = None


class SiklusKandangPublic(BaseModel):
    id: uuid.UUID
    kandang_id: uuid.UUID
    jenis_ayam_id: uuid.UUID
    fase_id: uuid.UUID
    jumlah_ayam: int
    tanggal_mulai: date
    status: StatusSiklus

    class Config:
        from_attributes = True


# --- PERUBAHAN POPULASI ---
class PerubahanPopulasiCreate(BaseModel):
    jenis: JenisPerubahan
    jumlah: int
    tanggal: date
    catatan: Optional[str] = None


class PerubahanPopulasiPublic(BaseModel):
    id: uuid.UUID
    siklus_id: uuid.UUID
    jenis: JenisPerubahan
    jumlah: int
    tanggal: date
    catatan: Optional[str] = None

    class Config:
        from_attributes = True
