import secrets
import uuid
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete
from sqlmodel import Session, select

from app.database import get_session
from app.models.akses import User, PenugasanKandang
from app.models.fisik import Kandang, Alat, Wadah, Stok
from app.models.enums import PeranUser, StatusPenugasan
from app.schemas.fisik import (
    KandangCreate, KandangUpdate, KandangPublic, KandangDetailPublic,
    AlatWithToken, AlatDetailPublic, WadahDetailPublic, TokenRotasiResponse,
    WadahCreate, WadahUpdate, WadahPublic
)
from app.models.masterdata import BahanPakan
from app.services.akses import get_entity_or_404
from app.services.audit import catat_audit
from app.services.hapus import (
    hapus_alat_beserta_isi, hapus_wadah_beserta_stok, jumlah_perintah_alat, pastikan_stok_nol,
    tandai_formulasi_perlu_ditinjau, tolak_bila_dipakai, tolak_bila_wadah_pernah_dipakai,
)
from app.services.perintah import deteksi_offline
from app.services.paginasi import Paginasi, terapkan
from app.services.auth import get_current_user, get_current_pemilik

router = APIRouter(tags=["Kandang & Alat"])


@router.post("/kandang", response_model=KandangPublic, status_code=status.HTTP_201_CREATED)
def create_kandang(
    kandang_in: KandangCreate,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)],
):
    """Mendaftarkan kandang baru. Hanya Pemilik."""
    kandang = Kandang(
        pemilik_id=current_pemilik.id,
        nama=kandang_in.nama,
        lokasi=kandang_in.lokasi,
    )
    session.add(kandang)
    session.commit()
    session.refresh(kandang)
    return kandang


@router.get("/kandang", response_model=List[KandangPublic])
def list_kandang(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    response: Response,
    p: Annotated[Paginasi, Depends()],
):
    """
    List kandang.
    Jika Pemilik: kembalikan kandang miliknya.
    Jika Pekerja: kembalikan kandang yang ditugaskan kepadanya.
    """
    if current_user.role == PeranUser.PEMILIK:
        statement = select(Kandang).where(Kandang.pemilik_id == current_user.id).order_by(Kandang.nama, Kandang.id)
        return terapkan(session, response, statement, p)
    else:
        # Pekerja
        statement = (
            select(Kandang)
            .join(PenugasanKandang, PenugasanKandang.kandang_id == Kandang.id)
            .where(
                PenugasanKandang.user_id == current_user.id,
                PenugasanKandang.status == StatusPenugasan.AKTIF
            )
            .order_by(Kandang.nama, Kandang.id)
        )
        return terapkan(session, response, statement, p)


def _get_kandang_or_404(session: Session, kandang_id: uuid.UUID, user: User) -> Kandang:
    kandang = session.get(Kandang, kandang_id)
    if not kandang:
        raise HTTPException(status_code=404, detail="Kandang tidak ditemukan")
        
    if user.role == PeranUser.PEMILIK:
        if kandang.pemilik_id != user.id:
            raise HTTPException(status_code=403, detail="Tidak berhak mengakses kandang ini")
    else:
        # Pekerja
        assigned = session.exec(
            select(PenugasanKandang).where(
                PenugasanKandang.kandang_id == kandang_id,
                PenugasanKandang.user_id == user.id,
                PenugasanKandang.status == StatusPenugasan.AKTIF
            )
        ).first()
        if not assigned:
            raise HTTPException(status_code=403, detail="Anda tidak ditugaskan ke kandang ini")
            
    return kandang


@router.get("/kandang/{id}", response_model=KandangDetailPublic)
def get_kandang(
    id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Detail kandang. Pemilik & Pekerja yang ditugaskan."""
    kandang = _get_kandang_or_404(session, id, current_user)
    
    # Enrich response
    detail = KandangDetailPublic.model_validate(kandang)
    
    alat = session.exec(select(Alat).where(Alat.kandang_id == kandang.id)).first()
    if alat:
        detail.status_alat = deteksi_offline(session, alat)

    # Lazy import to avoid circular dependency
    from app.models.operasional import SiklusKandang
    from app.models.enums import StatusSiklus
    siklus_aktif = session.exec(
        select(SiklusKandang).where(
            SiklusKandang.kandang_id == kandang.id,
            SiklusKandang.status == StatusSiklus.AKTIF
        )
    ).first()
    if siklus_aktif:
        detail.siklus_aktif_id = siklus_aktif.id
        detail.siklus_aktif_status = siklus_aktif.status.value
        
    return detail


@router.get("/kandang/{id}/alat", response_model=Optional[AlatDetailPublic])
def get_alat_kandang(
    id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """
    Alat kandang ini beserta wadah, bahan, dan stok (untuk layar kandang). `null` bila belum ada alat.
    Status alat sudah memperhitungkan heartbeat kedaluwarsa. `device_token` tidak pernah dikembalikan.
    """
    _get_kandang_or_404(session, id, current_user)
    alat = session.exec(select(Alat).where(Alat.kandang_id == id)).first()
    if not alat:
        return None
    deteksi_offline(session, alat)

    wadah_list = session.exec(select(Wadah).where(Wadah.alat_id == alat.id).order_by(Wadah.nomor_wadah)).all()
    stok_map = {
        s.wadah_id: s
        for s in session.exec(select(Stok).where(Stok.wadah_id.in_([w.id for w in wadah_list]))).all()
    } if wadah_list else {}
    bahan_ids = {w.bahan_pakan_id for w in wadah_list if w.bahan_pakan_id}
    nama_bahan = {
        b.id: b.nama for b in session.exec(select(BahanPakan).where(BahanPakan.id.in_(bahan_ids))).all()
    } if bahan_ids else {}

    return AlatDetailPublic(
        id=alat.id,
        kandang_id=alat.kandang_id,
        status=alat.status,
        versi_jadwal_aktif=alat.versi_jadwal_aktif,
        waktu_terakhir_sinkron=alat.waktu_terakhir_sinkron,
        wadah=[WadahDetailPublic(
            id=w.id,
            nomor_wadah=w.nomor_wadah,
            bahan_pakan_id=w.bahan_pakan_id,
            nama_bahan=nama_bahan.get(w.bahan_pakan_id),
            jumlah_stok=stok_map[w.id].jumlah_estimasi if w.id in stok_map else 0,
            ambang_menipis=stok_map[w.id].ambang_menipis if w.id in stok_map else None,
        ) for w in wadah_list],
    )


@router.patch("/kandang/{id}", response_model=KandangPublic)
def update_kandang(
    id: uuid.UUID,
    kandang_update: KandangUpdate,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)],
):
    """Update kandang. Hanya Pemilik."""
    kandang = _get_kandang_or_404(session, id, current_pemilik)
    
    update_data = kandang_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(kandang, key, value)
        
    session.add(kandang)
    session.commit()
    session.refresh(kandang)
    return kandang


@router.post("/kandang/{id}/alat", response_model=AlatWithToken, status_code=status.HTTP_201_CREATED)
def register_alat(
    id: uuid.UUID,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)],
):
    """
    Mendaftarkan alat IoT ke sebuah kandang.
    device_token di-generate dan HANYA DIKEMBALIKAN SEKALI di endpoint ini.
    """
    _get_kandang_or_404(session, id, current_pemilik)  # validasi kepemilikan
    
    # Cek apakah sudah ada alat (karena 1 kandang = max 1 alat di skema kita, unique index)
    existing_alat = session.exec(select(Alat).where(Alat.kandang_id == id)).first()
    if existing_alat:
        raise HTTPException(status_code=409, detail="Kandang ini sudah memiliki Alat IoT")
        
    new_token = secrets.token_hex(32)
    alat = Alat(
        kandang_id=id,
        device_token=new_token,
    )
    
    session.add(alat)
    session.commit()
    session.refresh(alat)
    
    return alat


@router.post("/alat/{id}/rotasi-token", response_model=TokenRotasiResponse)
def rotasi_token_alat(
    id: uuid.UUID,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)],
):
    """Ganti device_token alat dengan yang baru. Hanya Pemilik."""
    alat = session.get(Alat, id)
    if not alat:
        raise HTTPException(status_code=404, detail="Alat tidak ditemukan")
        
    # Validasi kepemilikan alat via kandang
    _get_kandang_or_404(session, alat.kandang_id, current_pemilik)
    
    new_token = secrets.token_hex(32)
    alat.device_token = new_token
    session.add(alat)
    session.commit()
    
    return TokenRotasiResponse(device_token=new_token)


@router.post("/alat/{id}/wadah", response_model=WadahPublic, status_code=status.HTTP_201_CREATED)
def create_wadah(
    id: uuid.UUID,
    wadah_in: WadahCreate,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)],
):
    """Menambahkan wadah pakan ke Alat IoT."""
    alat = session.get(Alat, id)
    if not alat:
        raise HTTPException(status_code=404, detail="Alat tidak ditemukan")
        
    _get_kandang_or_404(session, alat.kandang_id, current_pemilik)
    
    # Cek apakah nomor wadah sudah dipakai di alat ini
    existing_wadah = session.exec(
        select(Wadah).where(Wadah.alat_id == id, Wadah.nomor_wadah == wadah_in.nomor_wadah)
    ).first()
    if existing_wadah:
        raise HTTPException(status_code=409, detail=f"Wadah nomor {wadah_in.nomor_wadah} sudah ada")

    if wadah_in.bahan_pakan_id is not None:
        get_entity_or_404(session, BahanPakan, wadah_in.bahan_pakan_id, current_pemilik.id)

    wadah = Wadah(
        alat_id=id,
        nomor_wadah=wadah_in.nomor_wadah,
        bahan_pakan_id=wadah_in.bahan_pakan_id,
        stok=Stok(jumlah_estimasi=0),  # R14: Stok selalu ada bersama Wadah
    )
    session.add(wadah)
    session.commit()
    session.refresh(wadah)
    return wadah


@router.patch("/wadah/{id}", response_model=WadahPublic)
def update_wadah(
    id: uuid.UUID,
    wadah_update: WadahUpdate,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)],
):
    """Mapping ulang bahan pakan ke wadah tertentu."""
    wadah = session.get(Wadah, id)
    if not wadah:
        raise HTTPException(status_code=404, detail="Wadah tidak ditemukan")
        
    # Validasi kepemilikan via wadah -> alat -> kandang
    alat = session.get(Alat, wadah.alat_id)
    _get_kandang_or_404(session, alat.kandang_id, current_pemilik)
    
    # exclude_unset: null eksplisit berarti melepas bahan dari wadah
    if "bahan_pakan_id" in wadah_update.model_fields_set:
        if wadah_update.bahan_pakan_id is not None:
            get_entity_or_404(session, BahanPakan, wadah_update.bahan_pakan_id, current_pemilik.id)
        wadah.bahan_pakan_id = wadah_update.bahan_pakan_id

    session.add(wadah)
    session.commit()
    session.refresh(wadah)
    return wadah


@router.delete("/wadah/{id}", status_code=status.HTTP_204_NO_CONTENT)
def hapus_wadah(
    id: uuid.UUID,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)],
):
    """Hapus wadah yang salah input. Ditolak bila sudah pernah mengeluarkan pakan atau stok belum 0."""
    wadah = session.get(Wadah, id)
    if not wadah:
        raise HTTPException(status_code=404, detail="Wadah tidak ditemukan")
    alat = session.get(Alat, wadah.alat_id)
    _get_kandang_or_404(session, alat.kandang_id, current_pemilik)

    tolak_bila_wadah_pernah_dipakai(session, [wadah])
    pastikan_stok_nol(session, [wadah])

    bahan_id, nomor = wadah.bahan_pakan_id, wadah.nomor_wadah
    masih_ada_bahan = bahan_id is not None and session.exec(
        select(Wadah).where(Wadah.alat_id == alat.id, Wadah.bahan_pakan_id == bahan_id, Wadah.id != wadah.id)
    ).first() is not None

    catat_audit(session, current_pemilik.id, "HAPUS_WADAH", "wadah", wadah.id, nilai_lama=f"nomor {nomor}, bahan {bahan_id}")
    hapus_wadah_beserta_stok(session, wadah)
    if bahan_id is not None and not masih_ada_bahan:
        tandai_formulasi_perlu_ditinjau(
            session, alat.kandang_id, f"Wadah {nomor} dihapus; bahannya tidak lagi terpasang. Formulasi aktif perlu dihitung ulang."
        )
    session.commit()


@router.delete("/alat/{id}", status_code=status.HTTP_204_NO_CONTENT)
def hapus_alat(
    id: uuid.UUID,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)],
):
    """Hapus alat yang salah daftar beserta wadah dan stoknya. Ditolak bila sudah punya perintah atau stok belum 0."""
    alat = session.get(Alat, id)
    if not alat:
        raise HTTPException(status_code=404, detail="Alat tidak ditemukan")
    _get_kandang_or_404(session, alat.kandang_id, current_pemilik)

    n = jumlah_perintah_alat(session, alat.id)
    if n:
        raise HTTPException(status_code=409, detail=f"Tidak dapat menghapus alat: sudah punya {n} perintah (riwayat)")
    wadah_list = session.exec(select(Wadah).where(Wadah.alat_id == alat.id)).all()
    pastikan_stok_nol(session, wadah_list)

    catat_audit(session, current_pemilik.id, "HAPUS_ALAT", "alat", alat.id, nilai_lama=f"kandang {alat.kandang_id}, {len(wadah_list)} wadah")
    kandang_id = alat.kandang_id
    hapus_alat_beserta_isi(session, alat)
    tandai_formulasi_perlu_ditinjau(session, kandang_id, "Alat dihapus dari kandang. Formulasi aktif perlu ditinjau.")
    session.commit()


@router.delete("/kandang/{id}", status_code=status.HTTP_204_NO_CONTENT)
def hapus_kandang(
    id: uuid.UUID,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)],
):
    """
    Hapus kandang yang salah input beserta alat, wadah, stok, dan penugasannya.
    Ditolak bila pernah punya siklus atau perintah (gunakan PATCH status=NONAKTIF) atau stok belum 0.
    """
    from app.models.operasional import SiklusKandang

    kandang = _get_kandang_or_404(session, id, current_pemilik)
    alat = session.exec(select(Alat).where(Alat.kandang_id == id)).first()

    tolak_bila_dipakai(session, "kandang", [("siklus", SiklusKandang, SiklusKandang.kandang_id == id)])
    if alat:
        n = jumlah_perintah_alat(session, alat.id)
        if n:
            raise HTTPException(status_code=409, detail=f"Tidak dapat menghapus kandang: alatnya sudah punya {n} perintah (riwayat)")
        pastikan_stok_nol(session, session.exec(select(Wadah).where(Wadah.alat_id == alat.id)).all())

    catat_audit(session, current_pemilik.id, "HAPUS_KANDANG", "kandang", kandang.id,
                nilai_lama=f"{kandang.nama} ({kandang.lokasi or '-'})",
                catatan="penugasan, alat, wadah, dan stok ikut terhapus" if alat else "penugasan ikut terhapus")
    session.exec(delete(PenugasanKandang).where(PenugasanKandang.kandang_id == id))
    if alat:
        hapus_alat_beserta_isi(session, alat)
    session.delete(kandang)
    session.commit()
