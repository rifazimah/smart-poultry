import uuid
from typing import Optional
from pydantic import BaseModel
from app.models.enums import TipeBatas, StatusBahan


# --- JENIS AYAM ---
class JenisAyamCreate(BaseModel):
    nama: str


class JenisAyamUpdate(BaseModel):
    nama: Optional[str] = None


class JenisAyamPublic(BaseModel):
    id: uuid.UUID
    pemilik_id: uuid.UUID
    nama: str

    class Config:
        from_attributes = True


# --- FASE ---
class FaseCreate(BaseModel):
    nama: str
    umur_min_hari: int
    umur_max_hari: int


class FaseUpdate(BaseModel):
    nama: Optional[str] = None
    umur_min_hari: Optional[int] = None
    umur_max_hari: Optional[int] = None


class FasePublic(BaseModel):
    id: uuid.UUID
    jenis_ayam_id: uuid.UUID
    nama: str
    umur_min_hari: int
    umur_max_hari: int

    class Config:
        from_attributes = True


# --- NUTRISI ---
class NutrisiCreate(BaseModel):
    nama: str
    satuan: str
    tipe_batas: TipeBatas


class NutrisiUpdate(BaseModel):
    nama: Optional[str] = None
    satuan: Optional[str] = None
    tipe_batas: Optional[TipeBatas] = None


class NutrisiPublic(BaseModel):
    id: uuid.UUID
    pemilik_id: uuid.UUID
    nama: str
    satuan: str
    tipe_batas: TipeBatas

    class Config:
        from_attributes = True


# --- BAHAN PAKAN ---
class BahanPakanCreate(BaseModel):
    nama: str
    harga: Optional[float] = None
    batas_maksimum: Optional[float] = None


class BahanPakanUpdate(BaseModel):
    nama: Optional[str] = None
    harga: Optional[float] = None
    batas_maksimum: Optional[float] = None
    status_sistem: Optional[StatusBahan] = None


class BahanPakanPublic(BaseModel):
    id: uuid.UUID
    pemilik_id: uuid.UUID
    nama: str
    harga: Optional[float] = None
    status_sistem: StatusBahan
    batas_maksimum: Optional[float] = None

    class Config:
        from_attributes = True


# --- STANDAR KONSUMSI ---
class StandarKonsumsiCreateUpdate(BaseModel):
    gram_per_ekor_per_hari: float
    frekuensi_makan: int
    durasi_aduk: int
    volume_air: float


class StandarKonsumsiPublic(BaseModel):
    id: uuid.UUID
    fase_id: uuid.UUID
    gram_per_ekor_per_hari: float
    frekuensi_makan: int
    durasi_aduk: int
    volume_air: float

    class Config:
        from_attributes = True


# --- KANDUNGAN NUTRISI BAHAN ---
class KandunganNutrisiBahanInput(BaseModel):
    nutrisi_id: uuid.UUID
    nilai_per_kg: float


class KandunganNutrisiBahanPublic(BaseModel):
    id: uuid.UUID
    bahan_pakan_id: uuid.UUID
    nutrisi_id: uuid.UUID
    nilai_per_kg: float

    class Config:
        from_attributes = True


# --- KEBUTUHAN NUTRISI FASE ---
class KebutuhanNutrisiFaseInput(BaseModel):
    nutrisi_id: uuid.UUID
    batas_min: Optional[float] = None
    batas_max: Optional[float] = None


class KebutuhanNutrisiFasePublic(BaseModel):
    id: uuid.UUID
    fase_id: uuid.UUID
    nutrisi_id: uuid.UUID
    batas_min: Optional[float] = None
    batas_max: Optional[float] = None

    class Config:
        from_attributes = True
