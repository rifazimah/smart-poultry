"""
Kelompok Akses (versi MVP, disederhanakan).
Role & Permission TIDAK dibuat sebagai tabel - lihat PeranUser di enums.py.
"""
import uuid
from datetime import date, datetime, timezone
from typing import Optional, TYPE_CHECKING

from sqlmodel import SQLModel, Field, Relationship

from .enums import PeranUser, StatusUser, StatusPenugasan

if TYPE_CHECKING:
    from .fisik import Kandang, TransaksiStok
    from .masterdata import JenisAyam, Nutrisi, BahanPakan
    from .operasional import Formulasi, Perintah, Notifikasi


def utc_now():
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    __tablename__ = "user"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    nama: str
    email: str = Field(unique=True, index=True)
    kata_sandi_hash: str
    role: PeranUser
    status: StatusUser = Field(default=StatusUser.AKTIF)
    dibuat_pada: datetime = Field(default_factory=utc_now)

    # Relasi R7-R10: master data dimiliki per Pemilik
    kandang: list["Kandang"] = Relationship(back_populates="pemilik")
    jenis_ayam: list["JenisAyam"] = Relationship(back_populates="pemilik")
    nutrisi: list["Nutrisi"] = Relationship(back_populates="pemilik")
    bahan_pakan: list["BahanPakan"] = Relationship(back_populates="pemilik")

    penugasan: list["PenugasanKandang"] = Relationship(back_populates="user")
    audit_log: list["AuditLog"] = Relationship(back_populates="user")
    notifikasi: list["Notifikasi"] = Relationship(back_populates="user")
    transaksi_stok: list["TransaksiStok"] = Relationship(back_populates="dilakukan_oleh")
    formulasi_dibuat: list["Formulasi"] = Relationship(back_populates="dibuat_oleh")
    perintah_dibuat: list["Perintah"] = Relationship(back_populates="dibuat_oleh")


class PenugasanKandang(SQLModel, table=True):
    """R3 + R4: Pekerja ditugaskan ke satu atau lebih Kandang (BR-03)."""
    __tablename__ = "penugasan_kandang"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    kandang_id: uuid.UUID = Field(foreign_key="kandang.id", index=True)
    tanggal_mulai: date
    status: StatusPenugasan = Field(default=StatusPenugasan.AKTIF)

    user: "User" = Relationship(back_populates="penugasan")
    kandang: "Kandang" = Relationship(back_populates="penugasan")


class AuditLog(SQLModel, table=True):
    """R5: entitas/entitas_id adalah referensi generik (bukan FK sungguhan),
    karena satu baris log bisa merujuk ke tabel apa saja (BR-03, BR-34)."""
    __tablename__ = "audit_log"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="user.id", index=True)
    aksi: str
    entitas: str
    entitas_id: uuid.UUID
    nilai_lama: Optional[str] = None
    nilai_baru: Optional[str] = None
    catatan: Optional[str] = None
    waktu: datetime = Field(default_factory=utc_now)

    user: Optional["User"] = Relationship(back_populates="audit_log")
