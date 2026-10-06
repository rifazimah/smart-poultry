"""
Kelompok Operasional (versi MVP).

DIHAPUS dari versi penuh (Fase 2, UC-09):
- Jadwal, SesiJadwal, PengajuanJadwal
Konsekuensi: Perintah & LogEksekusi HANYA berasal dari aksi manual
(tombol "Beri Makan Sekarang" / Test / Stop Darurat), tidak ada lagi
sumber dari eksekusi terjadwal.
"""
import uuid
from datetime import date, datetime, timezone
from typing import Optional, TYPE_CHECKING

from sqlmodel import SQLModel, Field, Relationship

from .enums import (
    StatusSiklus, JenisPerubahan, ModeFormulasi, StatusFormulasi, StatusNutrisi,
    TipePerintah, StatusPerintah, StatusEksekusi, JenisNotifikasi, StatusNotifikasi,
)

if TYPE_CHECKING:
    from .akses import User
    from .fisik import Kandang, Alat
    from .masterdata import JenisAyam, Fase, BahanPakan, Nutrisi


def utc_now():
    return datetime.now(timezone.utc)


class SiklusKandang(SQLModel, table=True):
    __tablename__ = "siklus_kandang"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    kandang_id: uuid.UUID = Field(foreign_key="kandang.id", index=True)
    jenis_ayam_id: uuid.UUID = Field(foreign_key="jenis_ayam.id")
    fase_id: uuid.UUID = Field(foreign_key="fase.id")
    jumlah_ayam: int
    tanggal_mulai: date
    status: StatusSiklus = Field(default=StatusSiklus.AKTIF)

    kandang: "Kandang" = Relationship(back_populates="siklus")
    jenis_ayam: "JenisAyam" = Relationship(back_populates="siklus")
    fase: "Fase" = Relationship(back_populates="siklus")

    # R26 (komposisi): riwayat populasi melekat pada siklus ini saja.
    perubahan_populasi: list["PerubahanPopulasi"] = Relationship(
        back_populates="siklus",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    formulasi: list["Formulasi"] = Relationship(back_populates="siklus")


class PerubahanPopulasi(SQLModel, table=True):
    __tablename__ = "perubahan_populasi"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    siklus_id: uuid.UUID = Field(foreign_key="siklus_kandang.id", index=True)
    jenis: JenisPerubahan
    jumlah: int
    tanggal: date
    catatan: Optional[str] = None

    siklus: "SiklusKandang" = Relationship(back_populates="perubahan_populasi")


class Formulasi(SQLModel, table=True):
    __tablename__ = "formulasi"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    siklus_id: uuid.UUID = Field(foreign_key="siklus_kandang.id", index=True)
    dibuat_oleh_id: uuid.UUID = Field(foreign_key="user.id")
    mode: ModeFormulasi
    total_biaya_per_kg: Optional[float] = None
    status: StatusFormulasi
    dibuat_pada: datetime = Field(default_factory=utc_now)

    siklus: "SiklusKandang" = Relationship(back_populates="formulasi")
    dibuat_oleh: "User" = Relationship(back_populates="formulasi_dibuat")

    # R29 / R31 (komposisi): item & hasil nutrisi tidak bermakna tanpa Formulasi induknya.
    item: list["FormulasiItem"] = Relationship(
        back_populates="formulasi",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    nutrisi_hasil: list["FormulasiNutrisiHasil"] = Relationship(
        back_populates="formulasi",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    perintah: list["Perintah"] = Relationship(back_populates="formulasi")


class FormulasiItem(SQLModel, table=True):
    __tablename__ = "formulasi_item"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    formulasi_id: uuid.UUID = Field(foreign_key="formulasi.id", index=True)
    bahan_pakan_id: uuid.UUID = Field(foreign_key="bahan_pakan.id")
    proporsi: float  # 0-1
    berat_per_sesi: float  # gram, hasil BR-14

    formulasi: "Formulasi" = Relationship(back_populates="item")
    bahan_pakan: "BahanPakan" = Relationship(back_populates="item_formulasi")


class FormulasiNutrisiHasil(SQLModel, table=True):
    __tablename__ = "formulasi_nutrisi_hasil"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    formulasi_id: uuid.UUID = Field(foreign_key="formulasi.id", index=True)
    nutrisi_id: uuid.UUID = Field(foreign_key="nutrisi.id")
    nilai_hasil: float
    status: StatusNutrisi

    formulasi: "Formulasi" = Relationship(back_populates="nutrisi_hasil")
    nutrisi: "Nutrisi" = Relationship(back_populates="hasil_formulasi")


class Perintah(SQLModel, table=True):
    """R41: formulasi_id diisi untuk tipe BERI_MAKAN, kosong untuk
    TEST/STOP_DARURAT/RESET_ERROR (BR-32)."""
    __tablename__ = "perintah"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    alat_id: uuid.UUID = Field(foreign_key="alat.id", index=True)
    dibuat_oleh_id: uuid.UUID = Field(foreign_key="user.id")
    formulasi_id: Optional[uuid.UUID] = Field(default=None, foreign_key="formulasi.id")
    tipe: TipePerintah
    command_id: uuid.UUID = Field(default_factory=uuid.uuid4, unique=True, index=True)
    status: StatusPerintah = Field(default=StatusPerintah.PENDING)
    dibuat_pada: datetime = Field(default_factory=utc_now)

    alat: "Alat" = Relationship(back_populates="perintah")
    dibuat_oleh: "User" = Relationship(back_populates="perintah_dibuat")
    formulasi: Optional["Formulasi"] = Relationship(back_populates="perintah")

    # R42 (MVP): satu Perintah menghasilkan paling banyak satu LogEksekusi.
    log_eksekusi: Optional["LogEksekusi"] = Relationship(
        back_populates="perintah", sa_relationship_kwargs={"uselist": False}
    )


class LogEksekusi(SQLModel, table=True):
    __tablename__ = "log_eksekusi"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    perintah_id: uuid.UUID = Field(foreign_key="perintah.id", unique=True, index=True)
    id_eksekusi_unik: uuid.UUID = Field(unique=True, index=True)  # idempotency key dari alat
    berat_aktual: Optional[float] = None
    status: StatusEksekusi
    dilaporkan_pada: datetime = Field(default_factory=utc_now)

    perintah: "Perintah" = Relationship(back_populates="log_eksekusi")


class Notifikasi(SQLModel, table=True):
    __tablename__ = "notifikasi"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    jenis: JenisNotifikasi
    judul: str
    pesan: str
    status: StatusNotifikasi = Field(default=StatusNotifikasi.BELUM_DIBACA)
    dibuat_pada: datetime = Field(default_factory=utc_now)

    user: "User" = Relationship(back_populates="notifikasi")
