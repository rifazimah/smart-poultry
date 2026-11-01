import uuid
from typing import Optional

from sqlmodel import Session

from app.models.akses import AuditLog


def catat_audit(
    session: Session,
    user_id: Optional[uuid.UUID],
    aksi: str,
    entitas: str,
    entitas_id: uuid.UUID,
    nilai_lama: Optional[str] = None,
    nilai_baru: Optional[str] = None,
    catatan: Optional[str] = None,
) -> None:
    """Tambah baris AuditLog (BR-03, BR-34). Tidak melakukan commit."""
    session.add(AuditLog(
        user_id=user_id, aksi=aksi, entitas=entitas, entitas_id=entitas_id,
        nilai_lama=nilai_lama, nilai_baru=nilai_baru, catatan=catatan,
    ))
