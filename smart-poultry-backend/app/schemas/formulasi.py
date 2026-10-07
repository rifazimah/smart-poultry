import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from app.models.enums import ModeFormulasi, StatusFormulasi, StatusNutrisi


class FormulasiItemInput(BaseModel):
    bahan_pakan_id: uuid.UUID
    proporsi: float


class FormulasiManualRequest(BaseModel):
    item: List[FormulasiItemInput]


class FormulasiItemOutput(BaseModel):
    bahan_pakan_id: uuid.UUID
    nama_bahan: str
    proporsi: float
    berat_per_sesi: float


class NutrisiHasilOutput(BaseModel):
    nutrisi_id: uuid.UUID
    nama_nutrisi: str
    nilai_hasil: float
    batas_min: Optional[float] = None
    batas_max: Optional[float] = None
    status: StatusNutrisi


class FormulasiPreview(BaseModel):
    """
    Tidak disimpan ke DB langsung, ini adalah respon dari proses formulasi (baik OTOMATIS maupun MANUAL).
    Jika disimpan, struktur ini akan diubah jadi entitas Formulasi, FormulasiItem, FormulasiNutrisiHasil.
    """
    mode: ModeFormulasi
    status: StatusFormulasi
    total_biaya_per_kg: Optional[float] = None
    item: List[FormulasiItemOutput]
    nutrisi_hasil: List[NutrisiHasilOutput]
    pesan: Optional[str] = None


class FormulasiPublic(BaseModel):
    id: uuid.UUID
    siklus_id: uuid.UUID
    dibuat_oleh_id: uuid.UUID
    mode: ModeFormulasi
    total_biaya_per_kg: Optional[float] = None
    status: StatusFormulasi
    dibuat_pada: datetime

    class Config:
        from_attributes = True


class FormulasiItemPublic(BaseModel):
    id: uuid.UUID
    bahan_pakan_id: uuid.UUID
    proporsi: float
    berat_per_sesi: float

    class Config:
        from_attributes = True


class FormulasiNutrisiHasilPublic(BaseModel):
    id: uuid.UUID
    nutrisi_id: uuid.UUID
    nilai_hasil: float
    status: StatusNutrisi

    class Config:
        from_attributes = True


class FormulasiLengkapPublic(FormulasiPublic):
    item: List[FormulasiItemPublic]
    nutrisi_hasil: List[FormulasiNutrisiHasilPublic]
