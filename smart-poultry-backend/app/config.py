from typing import Literal, Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Nilai bawaan/contoh yang tidak boleh dipakai sebagai JWT_SECRET di production.
_JWT_SECRET_CONTOH = {"ganti-ini-di-.env", "ganti-dengan-string-acak-panjang", "dev-only-ganti-di-production"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # development | production. Pada production, konfigurasi berbahaya ditolak saat start (lihat validator).
    environment: Literal["development", "production"] = "development"

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/smart_poultry"
    jwt_secret: str = "ganti-ini-di-.env"
    jwt_expire_minutes: int = 60 * 24
    device_heartbeat_interval_seconds: int = 10  # dikirim ke alat, lihat API_CONTRACT.md
    perintah_timeout_pending_seconds: int = 60  # PENDING/DIAMBIL tak diproses alat
    perintah_timeout_berjalan_seconds: int = 300  # BERJALAN tak melapor
    alat_offline_after_seconds: int = 0  # 0 = 3x heartbeat interval
    sql_echo: bool = False  # True untuk melihat SQL saat debugging
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]  # origin React dev

    # Pembatasan percobaan login yang gagal (per email + alamat klien, in-memory per proses)
    login_max_gagal: int = 5
    login_jendela_detik: int = 300

    # Kredensial Pemilik pertama untuk seed_admin.py. Password kosong: bawaan hanya di development.
    admin_email: str = "admin@smartpoultry.com"
    admin_password: Optional[str] = None

    @model_validator(mode="after")
    def _validasi_production(self):
        if self.environment != "production":
            return self
        rahasia = self.jwt_secret
        if rahasia.lower() in _JWT_SECRET_CONTOH or "ganti" in rahasia.lower() or len(rahasia) < 32:
            raise ValueError(
                "ENVIRONMENT=production menolak JWT_SECRET bawaan/lemah. Isi JWT_SECRET dengan string acak "
                "minimal 32 karakter, mis.: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
            )
        self.sql_echo = False  # jangan mencetak SQL (berisi data) ke log production
        return self


settings = Settings()
