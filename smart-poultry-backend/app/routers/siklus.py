import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.database import get_session
from app.models.akses import User
from app.models.enums import StatusSiklus, JenisPerubahan, StatusFormulasi, JenisNotifikasi
from app.services.notifikasi import notify
from app.models.fisik import Kandang
from app.models.operasional import SiklusKandang, PerubahanPopulasi, Formulasi
from app.models.masterdata import JenisAyam, Fase
from app.schemas.operasional import (
    SiklusKandangCreate, SiklusKandangUpdate, SiklusKandangUpdateFase, SiklusKandangPublic,
    PerubahanPopulasiCreate, PerubahanPopulasiPublic
)
from app.services.audit import catat_audit
from app.services.auth import get_current_pemilik, get_current_user
from app.routers.kandang import _get_kandang_or_404

router = APIRouter(tags=["Siklus & Populasi"])


def _get_siklus_or_404(session: Session, siklus_id: uuid.UUID, user: User) -> SiklusKandang:
    siklus = session.get(SiklusKandang, siklus_id)
    if not siklus:
        raise HTTPException(status_code=404, detail="Siklus tidak ditemukan")
    
    # Verifikasi hak akses lewat kandang
    _get_kandang_or_404(session, siklus.kandang_id, user)
    return siklus


@router.post("/kandang/{id}/siklus", response_model=SiklusKandangPublic, status_code=status.HTTP_201_CREATED)
def create_siklus(
    id: uuid.UUID,
    siklus_in: SiklusKandangCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
):
    """Memulai siklus baru di sebuah kandang. Ditolak jika masih ada siklus aktif."""
    kandang = _get_kandang_or_404(session, id, current_user)
    
    # Cek apakah ada siklus aktif
    active_siklus = session.exec(
        select(SiklusKandang).where(
            SiklusKandang.kandang_id == id,
            SiklusKandang.status == StatusSiklus.AKTIF
        )
    ).first()
    if active_siklus:
        raise HTTPException(status_code=409, detail="Kandang masih memiliki siklus aktif")
        
    # Validasi master data
    jenis = session.get(JenisAyam, siklus_in.jenis_ayam_id)
    if not jenis:
        raise HTTPException(status_code=404, detail="Jenis Ayam tidak ditemukan")
        
    fase = session.get(Fase, siklus_in.fase_id)
    if not fase or fase.jenis_ayam_id != jenis.id:
        raise HTTPException(status_code=400, detail="Fase tidak valid untuk Jenis Ayam ini")
        
    new_siklus = SiklusKandang(
        kandang_id=id,
        jenis_ayam_id=siklus_in.jenis_ayam_id,
        fase_id=siklus_in.fase_id,
        jumlah_ayam=siklus_in.jumlah_ayam,
        tanggal_mulai=siklus_in.tanggal_mulai,
        status=StatusSiklus.AKTIF
    )
    
    session.add(new_siklus)
    session.commit()
    session.refresh(new_siklus)
    return new_siklus


@router.get("/kandang/{id}/siklus/aktif", response_model=Optional[SiklusKandangPublic])
def get_active_siklus(
    id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
):
    """Mendapatkan siklus yang sedang aktif di suatu kandang (bisa null)."""
    _get_kandang_or_404(session, id, current_user)
    
    active_siklus = session.exec(
        select(SiklusKandang).where(
            SiklusKandang.kandang_id == id,
            SiklusKandang.status == StatusSiklus.AKTIF
        )
    ).first()
    
    return active_siklus


@router.patch("/siklus/{id}/fase", response_model=SiklusKandangPublic)
def update_fase_siklus(
    id: uuid.UUID,
    fase_update: SiklusKandangUpdateFase,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
):
    """
    Pindah fase ayam. Formulasi lama akan otomatis ditandai PERLU_DITINJAU
    karena kebutuhan nutrisinya berubah.
    """
    siklus = _get_siklus_or_404(session, id, current_user)
    
    if siklus.status != StatusSiklus.AKTIF:
        raise HTTPException(status_code=400, detail="Siklus sudah selesai")
        
    # Validasi fase baru
    fase_baru = session.get(Fase, fase_update.fase_id)
    if not fase_baru or fase_baru.jenis_ayam_id != siklus.jenis_ayam_id:
        raise HTTPException(status_code=400, detail="Fase baru tidak valid")
        
    siklus.fase_id = fase_update.fase_id
    session.add(siklus)
    
    # Tandai formulasi aktif menjadi PERLU_DITINJAU
    active_formulas = session.exec(
        select(Formulasi).where(
            Formulasi.siklus_id == id,
            Formulasi.aktif == True  # noqa: E712
        )
    ).all()
    for f in active_formulas:
        f.status = StatusFormulasi.PERLU_DITINJAU
        session.add(f)
    if active_formulas:
        notify(session, siklus.kandang_id, JenisNotifikasi.PERLU_DITINJAU,
               "Formulasi perlu ditinjau",
               f"Fase berpindah ke {fase_baru.nama}; formulasi aktif perlu dihitung ulang.")
        
    session.commit()
    session.refresh(siklus)
    return siklus


@router.post("/siklus/{id}/populasi", response_model=PerubahanPopulasiPublic, status_code=status.HTTP_201_CREATED)
def catat_perubahan_populasi(
    id: uuid.UUID,
    data_in: PerubahanPopulasiCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
):
    """Mencatat mortalitas, panen, atau penambahan ayam."""
    siklus = _get_siklus_or_404(session, id, current_user)
    
    if siklus.status != StatusSiklus.AKTIF:
        raise HTTPException(status_code=400, detail="Siklus sudah selesai")
        
    perubahan = PerubahanPopulasi(
        siklus_id=id,
        jenis=data_in.jenis,
        jumlah=data_in.jumlah,
        tanggal=data_in.tanggal,
        catatan=data_in.catatan
    )
    session.add(perubahan)
    
    # Update populasi total di siklus
    if data_in.jenis in [JenisPerubahan.MORTALITAS, JenisPerubahan.PANEN]:
        siklus.jumlah_ayam -= data_in.jumlah
    elif data_in.jenis == JenisPerubahan.PENAMBAHAN:
        siklus.jumlah_ayam += data_in.jumlah
        
    if siklus.jumlah_ayam < 0:
        raise HTTPException(status_code=400, detail="Jumlah ayam tidak bisa kurang dari 0")
        
    session.add(siklus)
    session.commit()
    session.refresh(perubahan)
    
    return perubahan


@router.post("/siklus/{id}/selesai", response_model=SiklusKandangPublic)
def akhiri_siklus(
    id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
):
    """Tandai siklus sebagai selesai."""
    siklus = _get_siklus_or_404(session, id, current_user)
    
    if siklus.status != StatusSiklus.AKTIF:
        raise HTTPException(status_code=400, detail="Siklus sudah selesai")
        
    siklus.status = StatusSiklus.SELESAI
    session.add(siklus)
    
    # Matikan formulasi yang aktif
    active_formulas = session.exec(
        select(Formulasi).where(
            Formulasi.siklus_id == id,
            Formulasi.aktif == True  # noqa: E712
        )
    ).all()
    for f in active_formulas:
        f.aktif = False
        session.add(f)
        
    session.commit()
    session.refresh(siklus)
    return siklus


@router.patch("/siklus/{id}", response_model=SiklusKandangPublic)
def koreksi_siklus(
    id: uuid.UUID,
    data_in: SiklusKandangUpdate,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)]
):
    """
    Koreksi jumlah ayam / tanggal mulai yang salah input (Pemilik, siklus aktif).
    `jumlah_ayam` menggantikan nilai saat ini; formulasi aktif ditandai PERLU_DITINJAU karena berat per sesi bergantung populasi.
    """
    siklus = _get_siklus_or_404(session, id, current_pemilik)
    if siklus.status != StatusSiklus.AKTIF:
        raise HTTPException(status_code=400, detail="Siklus sudah selesai")

    perubahan = data_in.model_dump(exclude_unset=True, exclude_none=True)
    if not perubahan:
        raise HTTPException(status_code=400, detail="Tidak ada data yang diubah")

    lama = f"jumlah_ayam={siklus.jumlah_ayam}, tanggal_mulai={siklus.tanggal_mulai}"
    populasi_berubah = "jumlah_ayam" in perubahan and perubahan["jumlah_ayam"] != siklus.jumlah_ayam
    for key, value in perubahan.items():
        setattr(siklus, key, value)
    session.add(siklus)
    catat_audit(session, current_pemilik.id, "KOREKSI_SIKLUS", "siklus_kandang", siklus.id,
                nilai_lama=lama, nilai_baru=f"jumlah_ayam={siklus.jumlah_ayam}, tanggal_mulai={siklus.tanggal_mulai}")

    if populasi_berubah:
        aktif = session.exec(
            select(Formulasi).where(Formulasi.siklus_id == id, Formulasi.aktif == True)  # noqa: E712
        ).all()
        for f in aktif:
            f.status = StatusFormulasi.PERLU_DITINJAU
            session.add(f)
        if aktif:
            notify(session, siklus.kandang_id, JenisNotifikasi.PERLU_DITINJAU,
                   "Formulasi perlu ditinjau",
                   "Jumlah ayam dikoreksi; formulasi aktif perlu dihitung ulang.")

    session.commit()
    session.refresh(siklus)
    return siklus


@router.delete("/siklus/{id}/populasi/{populasi_id}", status_code=status.HTTP_204_NO_CONTENT)
def hapus_perubahan_populasi(
    id: uuid.UUID,
    populasi_id: uuid.UUID,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)]
):
    """Hapus catatan populasi yang salah input; efeknya pada jumlah ayam dibalik (Pemilik, siklus aktif)."""
    siklus = _get_siklus_or_404(session, id, current_pemilik)
    if siklus.status != StatusSiklus.AKTIF:
        raise HTTPException(status_code=400, detail="Siklus sudah selesai")

    perubahan = session.get(PerubahanPopulasi, populasi_id)
    if not perubahan or perubahan.siklus_id != siklus.id:
        raise HTTPException(status_code=404, detail="Catatan populasi tidak ditemukan")

    if perubahan.jenis == JenisPerubahan.PENAMBAHAN:
        baru = siklus.jumlah_ayam - perubahan.jumlah
        if baru < 0:
            raise HTTPException(
                status_code=409,
                detail="Tidak dapat dihapus: jumlah ayam akan menjadi negatif. Koreksi jumlah ayam lewat PATCH /siklus/{id}.",
            )
    else:  # MORTALITAS / PANEN dikembalikan ke populasi
        baru = siklus.jumlah_ayam + perubahan.jumlah

    catat_audit(session, current_pemilik.id, "HAPUS_PERUBAHAN_POPULASI", "perubahan_populasi", perubahan.id,
                nilai_lama=f"{perubahan.jenis.value} {perubahan.jumlah} ({perubahan.tanggal}); jumlah_ayam {siklus.jumlah_ayam}",
                nilai_baru=f"jumlah_ayam {baru}", catatan=perubahan.catatan)
    siklus.jumlah_ayam = baru
    session.add(siklus)
    session.delete(perubahan)
    session.commit()
