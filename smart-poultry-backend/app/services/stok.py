import uuid

from sqlmodel import Session, select

from app.models.fisik import Stok


def get_or_create_stok(session: Session, wadah_id: uuid.UUID) -> Stok:
    """Ambil baris Stok wadah; dibuat (belum di-commit) bila belum ada, mis. data lama."""
    stok = session.exec(select(Stok).where(Stok.wadah_id == wadah_id)).first()
    if not stok:
        stok = Stok(wadah_id=wadah_id, jumlah_estimasi=0)
        session.add(stok)
        session.flush()
    return stok
