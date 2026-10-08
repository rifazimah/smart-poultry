import uuid
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.database import get_session
from app.models.akses import User
from app.models.enums import JenisTransaksi
from app.models.fisik import Alat, Wadah, Stok, TransaksiStok
from app.models.masterdata import BahanPakan
from app.schemas.stok import (
    IsiUlangStokRequest, KoreksiStokRequest, StokPublic, TransaksiStokPublic
)
from app.services.auth import get_current_user
from app.routers.kandang import _get_kandang_or_404

router = APIRouter(tags=["Manajemen Stok"])


@router.get("/kandang/{id}/stok", response_model=List[StokPublic])
def get_stok_kandang(
    id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
):
    _get_kandang_or_404(session, id, current_user)
    
    alat = session.exec(select(Alat).where(Alat.kandang_id == id)).first()
    if not alat:
        return []
        
    wadah_list = session.exec(select(Wadah).where(Wadah.alat_id == alat.id)).all()
    if not wadah_list:
        return []
        
    wadah_ids = [w.id for w in wadah_list]
    stok_list = session.exec(select(Stok).where(Stok.wadah_id.in_(wadah_ids))).all()
    
    # Isi nama bahan pakan
    bahan_ids = {w.bahan_pakan_id for w in wadah_list if w.bahan_pakan_id}
    bahan_dict = {}
    if bahan_ids:
        bahan_list = session.exec(select(BahanPakan).where(BahanPakan.id.in_(bahan_ids))).all()
        bahan_dict = {b.id: b.nama for b in bahan_list}
        
    wadah_to_bahan = {w.id: w.bahan_pakan_id for w in wadah_list}
    
    result = []
    for stok in stok_list:
        sp = StokPublic.model_validate(stok)
        bahan_id = wadah_to_bahan.get(stok.wadah_id)
        if bahan_id:
            sp.nama_bahan = bahan_dict.get(bahan_id)
        result.append(sp)
        
    return result


def _get_wadah_and_stok_or_404(session: Session, wadah_id: uuid.UUID, current_user: User):
    wadah = session.get(Wadah, wadah_id)
    if not wadah:
        raise HTTPException(status_code=404, detail="Wadah tidak ditemukan")
        
    alat = session.get(Alat, wadah.alat_id)
    # Validasi akses via kandang
    _get_kandang_or_404(session, alat.kandang_id, current_user)
    
    stok = session.exec(select(Stok).where(Stok.wadah_id == wadah.id)).first()
    if not stok:
        # Buat stok jika belum ada
        stok = Stok(wadah_id=wadah.id, jumlah_estimasi=0)
        session.add(stok)
        session.commit()
        session.refresh(stok)
        
    return wadah, stok


@router.post("/wadah/{id}/stok/isi-ulang", response_model=TransaksiStokPublic, status_code=status.HTTP_201_CREATED)
def isi_ulang_stok(
    id: uuid.UUID,
    req: IsiUlangStokRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
):
    wadah, stok = _get_wadah_and_stok_or_404(session, id, current_user)
    
    if req.jumlah <= 0:
        raise HTTPException(status_code=400, detail="Jumlah isi ulang harus lebih dari 0")
        
    stok.jumlah_estimasi += req.jumlah
    session.add(stok)
    
    tx = TransaksiStok(
        wadah_id=wadah.id,
        dilakukan_oleh_id=current_user.id,
        jenis=JenisTransaksi.ISI_ULANG,
        jumlah=req.jumlah,
        alasan="Isi ulang rutin"
    )
    session.add(tx)
    session.commit()
    session.refresh(tx)
    return tx


@router.post("/wadah/{id}/stok/koreksi", response_model=TransaksiStokPublic, status_code=status.HTTP_201_CREATED)
def koreksi_stok(
    id: uuid.UUID,
    req: KoreksiStokRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
):
    if not req.alasan or not req.alasan.strip():
        raise HTTPException(status_code=422, detail="Alasan koreksi wajib diisi")
        
    if req.jumlah_baru < 0:
        raise HTTPException(status_code=400, detail="Jumlah baru tidak boleh negatif")
        
    wadah, stok = _get_wadah_and_stok_or_404(session, id, current_user)
    
    selisih = req.jumlah_baru - stok.jumlah_estimasi
    stok.jumlah_estimasi = req.jumlah_baru
    session.add(stok)
    
    tx = TransaksiStok(
        wadah_id=wadah.id,
        dilakukan_oleh_id=current_user.id,
        jenis=JenisTransaksi.KOREKSI_MANUAL,
        jumlah=selisih,
        alasan=req.alasan
    )
    session.add(tx)
    session.commit()
    session.refresh(tx)
    return tx


@router.get("/wadah/{id}/stok/transaksi", response_model=List[TransaksiStokPublic])
def riwayat_transaksi_stok(
    id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
):
    _get_wadah_and_stok_or_404(session, id, current_user)
    
    return session.exec(
        select(TransaksiStok)
        .where(TransaksiStok.wadah_id == id)
        .order_by(TransaksiStok.dibuat_pada.desc())
    ).all()
