"""
Seluruh enum dipakai sebagai native PostgreSQL ENUM lewat SQLModel.
Dikelompokkan sesuai kelompok class diagram (Akses, Fisik, Master Data, Operasional).
Role & Permission SENGAJA tidak dibuat sebagai tabel (lihat keputusan penyederhanaan
MVP) - peran user cukup PeranUser di bawah ini.

CATATAN CAKUPAN MVP:
- Jadwal, SesiJadwal, PengajuanJadwal TIDAK dibuat (UC-09 ditunda ke Fase 2).
- StatusPerintah TIDAK punya nilai terkait jadwal karena hanya dipakai
  untuk perintah manual (BERI_MAKAN, TEST, STOP_DARURAT) di fase ini.
"""
from enum import Enum


# ---------- Akses ----------
class PeranUser(str, Enum):
    PEMILIK = "PEMILIK"
    PEKERJA = "PEKERJA"


class StatusUser(str, Enum):
    AKTIF = "AKTIF"
    NONAKTIF = "NONAKTIF"
    WAJIB_GANTI_SANDI = "WAJIB_GANTI_SANDI"


class StatusPenugasan(str, Enum):
    AKTIF = "AKTIF"
    BERAKHIR = "BERAKHIR"


# ---------- Fisik ----------
class StatusKandang(str, Enum):
    AKTIF = "AKTIF"
    NONAKTIF = "NONAKTIF"


class StatusAlat(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    ERROR = "ERROR"


# ---------- Master Data ----------
class TipeBatas(str, Enum):
    MINIMUM = "MINIMUM"
    MAKSIMUM = "MAKSIMUM"
    MIN_MAKS = "MIN_MAKS"


class StatusBahan(str, Enum):
    DI_DALAM_SISTEM = "DI_DALAM_SISTEM"
    DI_LUAR_SISTEM = "DI_LUAR_SISTEM"


# ---------- Operasional: Populasi & Formulasi ----------
class StatusSiklus(str, Enum):
    AKTIF = "AKTIF"
    SELESAI = "SELESAI"


class JenisPerubahan(str, Enum):
    MORTALITAS = "MORTALITAS"
    PANEN = "PANEN"
    PENAMBAHAN = "PENAMBAHAN"


class ModeFormulasi(str, Enum):
    OTOMATIS = "OTOMATIS"
    MANUAL = "MANUAL"


class StatusFormulasi(str, Enum):
    VALID = "VALID"
    TIDAK_SEMPURNA = "TIDAK_SEMPURNA"
    PERLU_DITINJAU = "PERLU_DITINJAU"


class StatusNutrisi(str, Enum):
    KURANG = "KURANG"
    SESUAI = "SESUAI"
    BERLEBIH = "BERLEBIH"


# ---------- Operasional: Perintah, Log, Stok, Notifikasi ----------
class TipePerintah(str, Enum):
    BERI_MAKAN = "BERI_MAKAN"
    TEST = "TEST"
    STOP_DARURAT = "STOP_DARURAT"
    RESET_ERROR = "RESET_ERROR"


class StatusPerintah(str, Enum):
    PENDING = "PENDING"
    DIAMBIL = "DIAMBIL"
    BERJALAN = "BERJALAN"
    SUKSES = "SUKSES"
    GAGAL = "GAGAL"
    TIMEOUT = "TIMEOUT"


class StatusEksekusi(str, Enum):
    SUKSES = "SUKSES"
    GAGAL = "GAGAL"
    SKIPPED_STOCK = "SKIPPED_STOCK"


class JenisTransaksi(str, Enum):
    ISI_ULANG = "ISI_ULANG"
    KOREKSI_MANUAL = "KOREKSI_MANUAL"
    PENGELUARAN = "PENGELUARAN"


class JenisNotifikasi(str, Enum):
    PERINTAH_SUKSES = "PERINTAH_SUKSES"
    PERINTAH_GAGAL = "PERINTAH_GAGAL"
    ALAT_OFFLINE = "ALAT_OFFLINE"
    ALAT_ERROR = "ALAT_ERROR"
    STOK_MENIPIS = "STOK_MENIPIS"
    STOK_KOSONG = "STOK_KOSONG"
    PERLU_DITINJAU = "PERLU_DITINJAU"


class StatusNotifikasi(str, Enum):
    BELUM_DIBACA = "BELUM_DIBACA"
    SUDAH_DIBACA = "SUDAH_DIBACA"
