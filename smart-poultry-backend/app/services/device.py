from typing import Tuple

from fastapi import HTTPException
from sqlmodel import Session, select
from app.models.fisik import Alat, Wadah, TransaksiStok
from app.models.operasional import Perintah, LogEksekusi, FormulasiItem
from app.models.enums import StatusPerintah, JenisTransaksi, JenisNotifikasi, StatusEksekusi
from app.schemas.perintah import DeviceLogRequest
from app.services.notifikasi import notify
from app.services.perintah import ubah_status
from app.services.stok import get_or_create_stok


def proses_log_eksekusi(
    session: Session,
    alat: Alat,
    perintah: Perintah,
    req: DeviceLogRequest
) -> Tuple[LogEksekusi, bool]:
    """Proses log dari alat. Mengembalikan (log, baru); baru=False bila ini pengiriman ulang (idempoten)."""
    existing_log = session.exec(
        select(LogEksekusi).where(LogEksekusi.perintah_id == perintah.id)
    ).first()
    if existing_log:
        if existing_log.id_eksekusi_unik == req.id_eksekusi_unik:
            return existing_log, False
        raise HTTPException(status_code=409, detail="Perintah ini sudah memiliki log eksekusi lain")

    if session.exec(select(LogEksekusi).where(LogEksekusi.id_eksekusi_unik == req.id_eksekusi_unik)).first():
        raise HTTPException(status_code=409, detail="id_eksekusi_unik sudah dipakai perintah lain")
    if perintah.status not in (StatusPerintah.DIAMBIL, StatusPerintah.BERJALAN):
        raise HTTPException(
            status_code=409,
            detail=f"Log tidak dapat dikirim untuk perintah berstatus {perintah.status.value}",
        )

    sukses = req.status == StatusEksekusi.SUKSES
    ubah_status(perintah, StatusPerintah.SUKSES if sukses else StatusPerintah.GAGAL)

    log = LogEksekusi(
        perintah_id=perintah.id,
        id_eksekusi_unik=req.id_eksekusi_unik,
        berat_aktual=req.berat_aktual,
        status=req.status
    )
    session.add(log)

    # Kurangi stok hanya bila sukses dan ini perintah beri makan; SKIPPED_STOCK/GAGAL tidak mengurangi.
    if sukses and perintah.formulasi_id:
        items = session.exec(
            select(FormulasiItem).where(FormulasiItem.formulasi_id == perintah.formulasi_id)
        ).all()

        for item in items:
            wadah = session.exec(
                select(Wadah).where(
                    Wadah.alat_id == alat.id,
                    Wadah.bahan_pakan_id == item.bahan_pakan_id
                )
            ).first()
            if not wadah:
                continue

            stok = get_or_create_stok(session, wadah.id)
            stok.jumlah_estimasi = max(0.0, stok.jumlah_estimasi - item.berat_per_sesi)
            session.add(stok)
            session.add(TransaksiStok(
                wadah_id=wadah.id,
                dilakukan_oleh_id=perintah.dibuat_oleh_id,
                jenis=JenisTransaksi.PENGELUARAN,
                jumlah=item.berat_per_sesi,
                alasan="Pengeluaran otomatis untuk perintah pakan"
            ))

            nama = item.bahan_pakan.nama if item.bahan_pakan else "bahan"
            if stok.jumlah_estimasi <= 0:
                notify(session, alat.kandang_id, JenisNotifikasi.STOK_KOSONG,
                       "Stok habis", f"Stok {nama} di wadah {wadah.nomor_wadah} habis.")
            elif stok.ambang_menipis is not None and stok.jumlah_estimasi <= stok.ambang_menipis:
                notify(session, alat.kandang_id, JenisNotifikasi.STOK_MENIPIS,
                       "Stok menipis",
                       f"Stok {nama} di wadah {wadah.nomor_wadah} tersisa {stok.jumlah_estimasi:.0f} g.")

    if sukses:
        notify(session, alat.kandang_id, JenisNotifikasi.PERINTAH_SUKSES,
               "Eksekusi Perintah Selesai", f"Perintah {perintah.tipe.value} telah SUKSES.")
    else:
        notify(session, alat.kandang_id, JenisNotifikasi.PERINTAH_GAGAL,
               "Perintah Gagal", f"Perintah {perintah.tipe.value} berakhir {req.status.value}.")

    session.add(perintah)
    session.commit()
    session.refresh(log)
    return log, True
