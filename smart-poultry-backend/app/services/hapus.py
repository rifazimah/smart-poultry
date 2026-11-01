from typing import Iterable, Tuple

from fastapi import HTTPException
from sqlalchemy import func
from sqlmodel import Session, select

# (label untuk pesan, kelas model, kondisi where)
Referensi = Tuple[str, type, object]


def tolak_bila_dipakai(session: Session, nama: str, referensi: Iterable[Referensi]) -> None:
    """Lempar 409 beserta rincian bila `nama` masih direferensikan data lain (tidak ada penghapusan diam-diam)."""
    dipakai = []
    for label, model, kondisi in referensi:
        n = session.exec(select(func.count()).select_from(model).where(kondisi)).one()
        if n:
            dipakai.append(f"{n} {label}")
    if dipakai:
        raise HTTPException(
            status_code=409,
            detail=f"Tidak dapat menghapus {nama}: masih dipakai oleh " + ", ".join(dipakai),
        )
