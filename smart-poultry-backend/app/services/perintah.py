import uuid

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.enums import StatusFormulasi, StatusSiklus
from app.models.fisik import Alat, Wadah
from app.models.operasional import Formulasi, FormulasiItem, SiklusKandang
from app.services.stok import get_or_create_stok


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
