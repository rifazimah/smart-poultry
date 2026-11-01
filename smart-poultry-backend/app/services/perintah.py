import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlmodel import Session, select

from app.config import settings
from app.models.enums import JenisNotifikasi, StatusAlat, StatusFormulasi, StatusPerintah, StatusSiklus
from app.models.fisik import Alat, Wadah
from app.models.operasional import Formulasi, FormulasiItem, Perintah, SiklusKandang
from app.services.notifikasi import notify
from app.services.stok import get_or_create_stok

P = StatusPerintah
FINAL = {P.SUKSES, P.GAGAL, P.TIMEOUT}
AKTIF = {P.PENDING, P.DIAMBIL, P.BERJALAN}

# Transisi legal status perintah (PRD: PENDING -> DIAMBIL -> BERJALAN -> SUKSES/GAGAL/TIMEOUT).
# DIAMBIL -> SUKSES/GAGAL diizinkan agar alat yang gagal sebelum "mulai" tetap bisa melapor.
TRANSISI = {
    P.PENDING: {P.DIAMBIL, P.GAGAL, P.TIMEOUT},
    P.DIAMBIL: {P.BERJALAN, P.SUKSES, P.GAGAL, P.TIMEOUT},
    P.BERJALAN: {P.SUKSES, P.GAGAL, P.TIMEOUT},
    P.SUKSES: set(), P.GAGAL: set(), P.TIMEOUT: set(),
}


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def ubah_status(perintah: Perintah, baru: StatusPerintah) -> None:
    if baru not in TRANSISI[perintah.status]:
        raise HTTPException(
            status_code=409,
            detail=f"Transisi status perintah tidak valid: {perintah.status.value} -> {baru.value}",
        )
    perintah.status = baru


def expire_perintah(session: Session, alat: Alat) -> None:
    """Lazy-timeout: perintah aktif yang melewati batas waktu menjadi TIMEOUT (+ notifikasi)."""
    sekarang = datetime.now(timezone.utc)
    berubah = False
    for p in session.exec(select(Perintah).where(Perintah.alat_id == alat.id, Perintah.status.in_(AKTIF))).all():
        batas = (settings.perintah_timeout_berjalan_seconds if p.status == P.BERJALAN
                 else settings.perintah_timeout_pending_seconds)
        if sekarang - _aware(p.dibuat_pada) > timedelta(seconds=batas):
            p.status = P.TIMEOUT
            session.add(p)
            notify(session, alat.kandang_id, JenisNotifikasi.PERINTAH_GAGAL,
                   "Perintah timeout", f"Perintah {p.tipe.value} tidak selesai tepat waktu (TIMEOUT).")
            berubah = True
    if berubah:
        session.commit()


def alat_kedaluwarsa(alat: Alat) -> bool:
    if alat.waktu_terakhir_sinkron is None:
        return True
    batas = settings.alat_offline_after_seconds or 3 * settings.device_heartbeat_interval_seconds
    return datetime.now(timezone.utc) - _aware(alat.waktu_terakhir_sinkron) > timedelta(seconds=batas)


def deteksi_offline(session: Session, alat: Alat) -> StatusAlat:
    """Set status alat OFFLINE bila heartbeat kedaluwarsa (sekali + notifikasi ALAT_OFFLINE). Mengembalikan status efektif."""
    if alat_kedaluwarsa(alat) and alat.status != StatusAlat.OFFLINE:
        alat.status = StatusAlat.OFFLINE
        session.add(alat)
        notify(session, alat.kandang_id, JenisNotifikasi.ALAT_OFFLINE,
               "Alat offline", "Alat tidak mengirim heartbeat. Periksa koneksi alat.")
        session.commit()
        session.refresh(alat)
    return alat.status


def batalkan_perintah_aktif(session: Session, alat: Alat) -> None:
    """Stop darurat: perintah aktif dibatalkan (GAGAL). Tidak melakukan commit."""
    for p in session.exec(select(Perintah).where(Perintah.alat_id == alat.id, Perintah.status.in_(AKTIF))).all():
        p.status = P.GAGAL
        session.add(p)


def validasi_formulasi_untuk_beri_makan(
    session: Session, kandang_id: uuid.UUID, alat: Alat, formulasi_id: uuid.UUID
) -> Formulasi:
    """Formulasi harus ada, milik siklus aktif kandang ini, aktif & VALID, dan stok wadah cukup."""
    formulasi = session.get(Formulasi, formulasi_id)
    if not formulasi:
        raise HTTPException(status_code=404, detail="Formulasi tidak ditemukan")

    siklus_aktif = session.exec(
        select(SiklusKandang).where(
            SiklusKandang.kandang_id == kandang_id,
            SiklusKandang.status == StatusSiklus.AKTIF,
        )
    ).first()
    if not siklus_aktif or formulasi.siklus_id != siklus_aktif.id:
        raise HTTPException(status_code=409, detail="Formulasi bukan milik siklus aktif kandang ini")

    if not formulasi.aktif or formulasi.status != StatusFormulasi.VALID:
        raise HTTPException(
            status_code=409,
            detail=f"Formulasi tidak dapat dipakai (aktif={formulasi.aktif}, status={formulasi.status.value})",
        )

    items = session.exec(select(FormulasiItem).where(FormulasiItem.formulasi_id == formulasi.id)).all()
    kurang = []
    for item in items:
        wadah = session.exec(
            select(Wadah).where(Wadah.alat_id == alat.id, Wadah.bahan_pakan_id == item.bahan_pakan_id)
        ).first()
        if not wadah:
            raise HTTPException(status_code=409, detail="Bahan formulasi tidak lagi terpasang di wadah alat")
        stok = get_or_create_stok(session, wadah.id)
        if stok.jumlah_estimasi < item.berat_per_sesi:
            nama = item.bahan_pakan.nama if item.bahan_pakan else str(item.bahan_pakan_id)
            kurang.append(f"{nama} (butuh {item.berat_per_sesi:.1f} g, tersedia {stok.jumlah_estimasi:.1f} g)")
    if kurang:
        session.rollback()  # buang baris Stok yang mungkin baru dibuat
        raise HTTPException(status_code=409, detail="Stok tidak cukup: " + "; ".join(kurang))
    return formulasi
