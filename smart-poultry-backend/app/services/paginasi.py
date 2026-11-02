from fastapi import Query, Response
from sqlalchemy import func
from sqlmodel import Session, select


class Paginasi:
    """Dependency `?skip=0&limit=20` (default limit 20, maksimum 100) sesuai API_CONTRACT."""

    def __init__(
        self,
        skip: int = Query(0, ge=0, description="Jumlah data yang dilewati"),
        limit: int = Query(20, ge=1, le=100, description="Jumlah data per halaman (maksimum 100)"),
    ):
        self.skip = skip
        self.limit = limit


def terapkan(session: Session, response: Response, query, p: Paginasi):
    """
    Jalankan `query` dengan offset/limit. Total seluruh data (tanpa paginasi) dikirim di header `X-Total-Count`.
    `query` harus punya order_by yang deterministik agar halaman tidak tumpang tindih.
    """
    total = session.exec(select(func.count()).select_from(query.order_by(None).subquery())).one()
    response.headers["X-Total-Count"] = str(total)
    return session.exec(query.offset(p.skip).limit(p.limit)).all()
