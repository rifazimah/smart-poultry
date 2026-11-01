from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/smart_poultry"
    jwt_secret: str = "ganti-ini-di-.env"
    jwt_expire_minutes: int = 60 * 24
    device_heartbeat_interval_seconds: int = 10  # dikirim ke alat, lihat API_CONTRACT.md
    perintah_timeout_pending_seconds: int = 60  # PENDING/DIAMBIL tak diproses alat
    perintah_timeout_berjalan_seconds: int = 300  # BERJALAN tak melapor
    alat_offline_after_seconds: int = 0  # 0 = 3x heartbeat interval
    sql_echo: bool = False  # True untuk melihat SQL saat debugging
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]  # origin React dev


settings = Settings()
