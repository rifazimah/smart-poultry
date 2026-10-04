from sqlmodel import create_engine, Session

from .config import settings

# echo=True sementara berguna saat development untuk melihat SQL yang dijalankan.
# Matikan (False) sebelum demo/deploy.
engine = create_engine(settings.database_url, echo=True)


def get_session():
    """Dependency FastAPI: `session: Session = Depends(get_session)`."""
    with Session(engine) as session:
        yield session
