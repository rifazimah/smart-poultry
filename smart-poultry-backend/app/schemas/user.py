import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr

from app.models.enums import PeranUser, StatusUser, StatusPenugasan


class UserPublic(BaseModel):
    """Schema untuk mengembalikan data User tanpa kata_sandi_hash."""
    id: uuid.UUID
    nama: str
    email: str
    role: PeranUser
    status: StatusUser
    dibuat_pada: datetime

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    """Schema untuk membuat user baru."""
    nama: str
    email: EmailStr
    kata_sandi: str
    role: PeranUser


class UserStatusUpdate(BaseModel):
    """Schema untuk update status user."""
    status: StatusUser


class PenugasanKandangCreate(BaseModel):
    """Schema untuk membuat penugasan."""
    kandang_id: uuid.UUID
    tanggal_mulai: date


class PenugasanKandangPublic(BaseModel):
    """Schema untuk mengembalikan data penugasan."""
    id: uuid.UUID
    user_id: uuid.UUID
    kandang_id: uuid.UUID
    tanggal_mulai: date
    status: StatusPenugasan

    class Config:
        from_attributes = True
