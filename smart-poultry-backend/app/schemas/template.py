from typing import List, Optional

from pydantic import BaseModel


class TemplateKebutuhan(BaseModel):
    nutrisi: str
    batas_min: Optional[float] = None
    batas_max: Optional[float] = None


class TemplateStandarKonsumsi(BaseModel):
    gram_per_ekor_per_hari: float
    frekuensi_makan: int
    durasi_aduk: int
    volume_air: float


class TemplateFase(BaseModel):
    nama: str
    umur_min_hari: int
    umur_max_hari: int
    kebutuhan: List[TemplateKebutuhan]
    standar_konsumsi: TemplateStandarKonsumsi


class TemplateJenisAyam(BaseModel):
    id: str
    nama: str
    deskripsi: str
    fase: List[TemplateFase]


class SalinTemplateRequest(BaseModel):
    """Body opsional: nama lain untuk jenis ayam hasil salinan (default nama template)."""
    nama: Optional[str] = None
