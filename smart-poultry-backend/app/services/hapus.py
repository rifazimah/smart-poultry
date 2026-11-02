import uuid
from typing import Iterable, List, Tuple

from fastapi import HTTPException
from sqlalchemy import delete, func
from sqlmodel import Session, select

from app.models.enums import JenisNotifikasi, JenisTransaksi, StatusFormulasi, StatusSiklus
from app.models.fisik import Alat, Stok, TransaksiStok, Wadah
from app.models.operasional import Formulasi, Perintah, SiklusKandang
from app.services.notifikasi import notify

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


def pastikan_stok_nol(session: Session, wadah_list: List[Wadah]) -> None:
    """Wadah hanya boleh dihapus bila stoknya sudah 0 (koreksi dulu agar jumlah fisik tercatat)."""
    sisa = []
    for w in wadah_list:
        stok = session.exec(select(Stok).where(Stok.wadah_id == w.id)).first()
        if stok and stok.jumlah_estimasi > 0:
            sisa.append(f"wadah {w.nomor_wadah} ({stok.jumlah_estimasi:.1f} g)")
    if sisa:
        raise HTTPException(
            status_code=409,
            detail="Stok belum 0: " + ", ".join(sisa) + ". Koreksi stok ke 0 dulu (POST /wadah/{id}/stok/koreksi).",
        )


def tolak_bila_wadah_pernah_dipakai(session: Session, wadah_list: List[Wadah]) -> None:
    """Wadah yang pernah mengeluarkan pakan menyimpan riwayat stok yang tidak boleh dihapus."""
    ids = [w.id for w in wadah_list]
    if not ids:
        return
    n = session.exec(
        select(func.count()).select_from(TransaksiStok).where(
            TransaksiStok.wadah_id.in_(ids), TransaksiStok.jenis == JenisTransaksi.PENGELUARAN
        )
    ).one()
    if n:
        raise HTTPException(
            status_code=409,
            detail=f"Tidak dapat menghapus: wadah sudah punya {n} riwayat pengeluaran pakan",
        )


def hapus_wadah_beserta_stok(session: Session, wadah: Wadah) -> None:
    """Hapus transaksi stok (isi ulang/koreksi), Stok, dan Wadah. Tidak commit."""
    session.exec(delete(TransaksiStok).where(TransaksiStok.wadah_id == wadah.id))
    session.delete(wadah)  # Stok ikut terhapus (cascade R14)


def tandai_formulasi_perlu_ditinjau(session: Session, kandang_id: uuid.UUID, alasan: str) -> None:
    """Formulasi aktif siklus aktif kandang ini -> PERLU_DITINJAU + notifikasi. Tidak commit."""
    aktif = session.exec(
        select(Formulasi).join(SiklusKandang, SiklusKandang.id == Formulasi.siklus_id).where(
            SiklusKandang.kandang_id == kandang_id,
            SiklusKandang.status == StatusSiklus.AKTIF,
            Formulasi.aktif == True,  # noqa: E712
        )
    ).all()
    for f in aktif:
        f.status = StatusFormulasi.PERLU_DITINJAU
        session.add(f)
    if aktif:
        notify(session, kandang_id, JenisNotifikasi.PERLU_DITINJAU, "Formulasi perlu ditinjau", alasan)


def jumlah_perintah_alat(session: Session, alat_id: uuid.UUID) -> int:
    return session.exec(select(func.count()).select_from(Perintah).where(Perintah.alat_id == alat_id)).one()


def hapus_alat_beserta_isi(session: Session, alat: Alat) -> None:
    """Hapus alat + wadah + stok + transaksi stok. Tidak commit. Syarat (cek sebelumnya): tanpa perintah, stok 0."""
    for w in session.exec(select(Wadah).where(Wadah.alat_id == alat.id)).all():
        session.exec(delete(TransaksiStok).where(TransaksiStok.wadah_id == w.id))
    session.delete(alat)  # wadah & stok ikut terhapus (cascade R12/R14)
