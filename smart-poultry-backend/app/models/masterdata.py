"""
Kelompok Master Data: Nutrisi, BahanPakan, JenisAyam, Fase, dan tabel
penghubungnya (KandunganNutrisiBahan, KebutuhanNutrisiFase).
"""
import uuid
from typing import Optional, TYPE_CHECKING

from sqlmodel import SQLModel, Field, Relationship

from .enums import TipeBatas, StatusBahan

if TYPE_CHECKING:
    from .akses import User
    from .fisik import Wadah
    from .operasional import SiklusKandang, FormulasiItem, FormulasiNutrisiHasil


class Nutrisi(SQLModel, table=True):
    __tablename__ = "nutrisi"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    pemilik_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    nama: str
    satuan: str  # "%", "kkal/kg", "g/kg", dst.
    tipe_batas: TipeBatas

    pemilik: "User" = Relationship(back_populates="nutrisi")
    kandungan_pada_bahan: list["KandunganNutrisiBahan"] = Relationship(back_populates="nutrisi")
    kebutuhan_pada_fase: list["KebutuhanNutrisiFase"] = Relationship(back_populates="nutrisi")
    hasil_formulasi: list["FormulasiNutrisiHasil"] = Relationship(back_populates="nutrisi")


class BahanPakan(SQLModel, table=True):
    __tablename__ = "bahan_pakan"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    pemilik_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    nama: str
    harga: Optional[float] = None  # wajib diisi untuk mode formulasi OTOMATIS (BR-08)
    status_sistem: StatusBahan = Field(default=StatusBahan.DI_DALAM_SISTEM)
    batas_maksimum: Optional[float] = None  # proporsi maksimum 0-1, null = tanpa batas

    pemilik: "User" = Relationship(back_populates="bahan_pakan")
    wadah: list["Wadah"] = Relationship(back_populates="bahan_pakan")
    kandungan_nutrisi: list["KandunganNutrisiBahan"] = Relationship(
        back_populates="bahan_pakan",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    item_formulasi: list["FormulasiItem"] = Relationship(back_populates="bahan_pakan")


class KandunganNutrisiBahan(SQLModel, table=True):
    """R21+R22: kelas asosiasi BahanPakan <-> Nutrisi (banyak ke banyak)."""
    __tablename__ = "kandungan_nutrisi_bahan"
    __table_args__ = {"comment": "unique(bahan_pakan_id, nutrisi_id) ditegakkan di migrasi"}

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    bahan_pakan_id: uuid.UUID = Field(foreign_key="bahan_pakan.id", index=True)
    nutrisi_id: uuid.UUID = Field(foreign_key="nutrisi.id", index=True)
    nilai_per_kg: float

    bahan_pakan: "BahanPakan" = Relationship(back_populates="kandungan_nutrisi")
    nutrisi: "Nutrisi" = Relationship(back_populates="kandungan_pada_bahan")


class JenisAyam(SQLModel, table=True):
    __tablename__ = "jenis_ayam"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    pemilik_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    nama: str

    pemilik: "User" = Relationship(back_populates="jenis_ayam")
    fase: list["Fase"] = Relationship(
        back_populates="jenis_ayam",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    siklus: list["SiklusKandang"] = Relationship(back_populates="jenis_ayam")


class Fase(SQLModel, table=True):
    __tablename__ = "fase"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    jenis_ayam_id: uuid.UUID = Field(foreign_key="jenis_ayam.id", index=True)
    nama: str
    umur_min_hari: int
    umur_max_hari: int

    jenis_ayam: "JenisAyam" = Relationship(back_populates="fase")

    # R18 (komposisi 1-ke-0..1)
    standar_konsumsi: Optional["StandarKonsumsi"] = Relationship(
        back_populates="fase",
        sa_relationship_kwargs={"uselist": False, "cascade": "all, delete-orphan"},
    )
    kebutuhan_nutrisi: list["KebutuhanNutrisiFase"] = Relationship(
        back_populates="fase",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    siklus: list["SiklusKandang"] = Relationship(back_populates="fase")


class StandarKonsumsi(SQLModel, table=True):
    __tablename__ = "standar_konsumsi"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    fase_id: uuid.UUID = Field(foreign_key="fase.id", unique=True, index=True)
    gram_per_ekor_per_hari: float
    frekuensi_makan: int
    durasi_aduk: int  # detik
    volume_air: float  # ml

    fase: "Fase" = Relationship(back_populates="standar_konsumsi")


class KebutuhanNutrisiFase(SQLModel, table=True):
    """R19+R20: kelas asosiasi Fase <-> Nutrisi."""
    __tablename__ = "kebutuhan_nutrisi_fase"
    __table_args__ = {"comment": "unique(fase_id, nutrisi_id) ditegakkan di migrasi"}

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    fase_id: uuid.UUID = Field(foreign_key="fase.id", index=True)
    nutrisi_id: uuid.UUID = Field(foreign_key="nutrisi.id", index=True)
    batas_min: Optional[float] = None
    batas_max: Optional[float] = None

    fase: "Fase" = Relationship(back_populates="kebutuhan_nutrisi")
    nutrisi: "Nutrisi" = Relationship(back_populates="kebutuhan_pada_fase")
