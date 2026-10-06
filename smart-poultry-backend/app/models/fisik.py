"""
Kelompok Fisik dan Stok.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

from sqlmodel import SQLModel, Field, Relationship

from .enums import StatusKandang, StatusAlat, JenisTransaksi

if TYPE_CHECKING:
    from .akses import User, PenugasanKandang
    from .masterdata import BahanPakan
    from .operasional import SiklusKandang, Formulasi, Perintah


def utc_now():
    return datetime.now(timezone.utc)


class Kandang(SQLModel, table=True):
    __tablename__ = "kandang"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    pemilik_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    nama: str
    lokasi: Optional[str] = None
    status: StatusKandang = Field(default=StatusKandang.AKTIF)

    pemilik: "User" = Relationship(back_populates="kandang")
    penugasan: list["PenugasanKandang"] = Relationship(back_populates="kandang")

    # R11 (agregasi): satu Kandang dilayani 0..1 Alat. Alat bisa dicabut
    # tanpa datanya ikut terhapus -> agregasi, bukan komposisi.
    alat: Optional["Alat"] = Relationship(back_populates="kandang", sa_relationship_kwargs={"uselist": False})

    siklus: list["SiklusKandang"] = Relationship(back_populates="kandang")


class Alat(SQLModel, table=True):
    __tablename__ = "alat"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    kandang_id: uuid.UUID = Field(foreign_key="kandang.id", unique=True, index=True)
    device_token: str = Field(unique=True, index=True)
    status: StatusAlat = Field(default=StatusAlat.OFFLINE)
    versi_jadwal_aktif: Optional[int] = None  # disiapkan untuk Fase 2, tidak dipakai di MVP
    waktu_terakhir_sinkron: Optional[datetime] = None

    kandang: "Kandang" = Relationship(back_populates="alat")

    # R12 (komposisi): Wadah tidak bermakna tanpa Alat -> cascade delete.
    wadah: list["Wadah"] = Relationship(
        back_populates="alat",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    perintah: list["Perintah"] = Relationship(back_populates="alat")


class Wadah(SQLModel, table=True):
    """R13: Wadah berisi 0..1 BahanPakan (boleh kosong saat baru didaftarkan)."""
    __tablename__ = "wadah"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    alat_id: uuid.UUID = Field(foreign_key="alat.id", index=True)
    bahan_pakan_id: Optional[uuid.UUID] = Field(default=None, foreign_key="bahan_pakan.id")
    nomor_wadah: int
    # CATATAN: stok TIDAK disimpan di sini -> lihat kelas Stok (hindari duplikasi).

    alat: "Alat" = Relationship(back_populates="wadah")
    bahan_pakan: Optional["BahanPakan"] = Relationship(back_populates="wadah")

    # R14 (komposisi 1-ke-1): Stok tidak bermakna tanpa Wadah.
    stok: Optional["Stok"] = Relationship(
        back_populates="wadah",
        sa_relationship_kwargs={"uselist": False, "cascade": "all, delete-orphan"},
    )
    transaksi_stok: list["TransaksiStok"] = Relationship(back_populates="wadah")


class Stok(SQLModel, table=True):
    __tablename__ = "stok"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    wadah_id: uuid.UUID = Field(foreign_key="wadah.id", unique=True, index=True)
    jumlah_estimasi: float = Field(default=0)
    ambang_menipis: Optional[float] = None

    wadah: "Wadah" = Relationship(back_populates="stok")


class TransaksiStok(SQLModel, table=True):
    """R34: alasan WAJIB diisi untuk jenis KOREKSI_MANUAL (divalidasi di level API,
    bukan di level database, supaya pesan error lebih ramah pengguna)."""
    __tablename__ = "transaksi_stok"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    wadah_id: uuid.UUID = Field(foreign_key="wadah.id", index=True)
    dilakukan_oleh_id: uuid.UUID = Field(foreign_key="user.id")
    jenis: JenisTransaksi
    jumlah: float
    alasan: Optional[str] = None
    dibuat_pada: datetime = Field(default_factory=utc_now)

    wadah: "Wadah" = Relationship(back_populates="transaksi_stok")
    dilakukan_oleh: "User" = Relationship(back_populates="transaksi_stok")
