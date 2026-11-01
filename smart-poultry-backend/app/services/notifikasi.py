import uuid

from sqlmodel import Session, select

from app.models.akses import PenugasanKandang
from app.models.enums import JenisNotifikasi, StatusPenugasan
from app.models.fisik import Kandang
from app.models.operasional import Notifikasi


def penerima_kandang(session: Session, kandang_id: uuid.UUID) -> list[uuid.UUID]:
    """Pemilik kandang + Pekerja yang masih ditugaskan."""
    kandang = session.get(Kandang, kandang_id)
    if not kandang:
        return []
    pekerja = session.exec(
        select(PenugasanKandang.user_id).where(
            PenugasanKandang.kandang_id == kandang_id,
            PenugasanKandang.status == StatusPenugasan.AKTIF,
        )
    ).all()
    return list(dict.fromkeys([kandang.pemilik_id, *pekerja]))


def notify(session: Session, kandang_id: uuid.UUID, jenis: JenisNotifikasi, judul: str, pesan: str) -> None:
    """Tambah notifikasi untuk semua penerima kandang. Tidak melakukan commit."""
    for user_id in penerima_kandang(session, kandang_id):
        session.add(Notifikasi(user_id=user_id, jenis=jenis, judul=judul, pesan=pesan))
