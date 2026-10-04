from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/smart_poultry"
    jwt_secret: str = "ganti-ini-di-.env"
    jwt_expire_minutes: int = 60 * 24
    device_heartbeat_interval_seconds: int = 10  # dikirim ke alat, lihat API_CONTRACT.md


settings = Settings()
