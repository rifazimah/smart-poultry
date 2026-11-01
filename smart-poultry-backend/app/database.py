from sqlmodel import create_engine, Session

from .config import settings

# SQL_ECHO=true di .env untuk melihat SQL yang dijalankan saat development.
engine = create_engine(settings.database_url, echo=settings.sql_echo)


def get_session():
    """Dependency FastAPI: `session: Session = Depends(get_session)`."""
    with Session(engine) as session:
        yield session
