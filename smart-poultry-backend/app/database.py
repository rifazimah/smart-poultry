from sqlmodel import create_engine, Session

from .config import settings

# SQL_ECHO=true di .env untuk melihat SQL yang dijalankan saat development.
# connect_timeout: server database tidak terjangkau harus gagal cepat (bukan menggantung);
# pool_pre_ping: buang koneksi basi (mis. database dimulai ulang) sebelum dipakai.
engine = create_engine(
    settings.database_url,
    echo=settings.sql_echo,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 5},
)


def get_session():
    """Dependency FastAPI: `session: Session = Depends(get_session)`."""
    with Session(engine) as session:
        yield session
