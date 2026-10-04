"""
Import semua model di sini supaya SQLModel.metadata lengkap saat Alembic
melakukan autogenerate, dan supaya forward-reference antar file (string type
hint di Relationship) berhasil di-resolve oleh SQLAlchemy.

Urutan import tidak masalah; SQLAlchemy me-resolve relationship secara lazy.
"""
from .enums import *  # noqa: F401,F403

from .akses import User, PenugasanKandang, AuditLog  # noqa: F401
from .fisik import Kandang, Alat, Wadah, Stok, TransaksiStok  # noqa: F401
from .masterdata import (  # noqa: F401
    Nutrisi,
    BahanPakan,
    KandunganNutrisiBahan,
    JenisAyam,
    Fase,
    StandarKonsumsi,
    KebutuhanNutrisiFase,
)
from .operasional import (  # noqa: F401
    SiklusKandang,
    PerubahanPopulasi,
    Formulasi,
    FormulasiItem,
    FormulasiNutrisiHasil,
    Perintah,
    LogEksekusi,
    Notifikasi,
)
