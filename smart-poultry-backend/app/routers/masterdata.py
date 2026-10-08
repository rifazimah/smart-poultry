import uuid
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.database import get_session
from app.models.akses import User
from app.models.masterdata import (
    JenisAyam, Fase, Nutrisi, BahanPakan, StandarKonsumsi,
    KandunganNutrisiBahan, KebutuhanNutrisiFase
)
from app.schemas.masterdata import (
    JenisAyamCreate, JenisAyamUpdate, JenisAyamPublic,
    FaseCreate, FaseUpdate, FasePublic,
    NutrisiCreate, NutrisiUpdate, NutrisiPublic,
    BahanPakanCreate, BahanPakanUpdate, BahanPakanPublic,
    StandarKonsumsiCreateUpdate, StandarKonsumsiPublic,
    KandunganNutrisiBahanInput, KandunganNutrisiBahanPublic,
    KebutuhanNutrisiFaseInput, KebutuhanNutrisiFasePublic
)
from app.services.auth import get_current_pemilik

router = APIRouter(tags=["Master Data"])


# --- Helper ---
def get_entity_or_404(session: Session, model_class, entity_id: uuid.UUID, pemilik_id: uuid.UUID):
    entity = session.get(model_class, entity_id)
    if not entity or entity.pemilik_id != pemilik_id:
        raise HTTPException(status_code=404, detail=f"{model_class.__name__} tidak ditemukan")
    return entity


# --- JENIS AYAM ---
@router.post("/jenis-ayam", response_model=JenisAyamPublic, status_code=status.HTTP_201_CREATED)
def create_jenis_ayam(
    data_in: JenisAyamCreate,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)]
):
    db_obj = JenisAyam(pemilik_id=current_pemilik.id, **data_in.model_dump())
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


@router.get("/jenis-ayam", response_model=List[JenisAyamPublic])
def list_jenis_ayam(
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)]
):
    return session.exec(select(JenisAyam).where(JenisAyam.pemilik_id == current_pemilik.id)).all()


@router.get("/jenis-ayam/{id}", response_model=JenisAyamPublic)
def get_jenis_ayam(
    id: uuid.UUID,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)]
):
    return get_entity_or_404(session, JenisAyam, id, current_pemilik.id)


@router.patch("/jenis-ayam/{id}", response_model=JenisAyamPublic)
def update_jenis_ayam(
    id: uuid.UUID,
    data_in: JenisAyamUpdate,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)]
):
    db_obj = get_entity_or_404(session, JenisAyam, id, current_pemilik.id)
    update_data = data_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_obj, key, value)
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


@router.delete("/jenis-ayam/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_jenis_ayam(
    id: uuid.UUID,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)]
):
    db_obj = get_entity_or_404(session, JenisAyam, id, current_pemilik.id)
    session.delete(db_obj)
    session.commit()


# --- FASE ---
@router.post("/jenis-ayam/{id}/fase", response_model=FasePublic, status_code=status.HTTP_201_CREATED)
def create_fase(
    id: uuid.UUID,
    data_in: FaseCreate,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)]
):
    get_entity_or_404(session, JenisAyam, id, current_pemilik.id)
    db_obj = Fase(jenis_ayam_id=id, **data_in.model_dump())
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


@router.get("/jenis-ayam/{id}/fase", response_model=List[FasePublic])
def list_fase(
    id: uuid.UUID,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)]
):
    get_entity_or_404(session, JenisAyam, id, current_pemilik.id)
    return session.exec(select(Fase).where(Fase.jenis_ayam_id == id)).all()


@router.get("/fase/{id}", response_model=FasePublic)
def get_fase(
    id: uuid.UUID,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)]
):
    fase = session.get(Fase, id)
    if not fase:
        raise HTTPException(status_code=404, detail="Fase tidak ditemukan")
    get_entity_or_404(session, JenisAyam, fase.jenis_ayam_id, current_pemilik.id)
    return fase


@router.patch("/fase/{id}", response_model=FasePublic)
def update_fase(
    id: uuid.UUID,
    data_in: FaseUpdate,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)]
):
    fase = session.get(Fase, id)
    if not fase:
        raise HTTPException(status_code=404, detail="Fase tidak ditemukan")
    get_entity_or_404(session, JenisAyam, fase.jenis_ayam_id, current_pemilik.id)
    
    update_data = data_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(fase, key, value)
    session.add(fase)
    session.commit()
    session.refresh(fase)
    return fase


@router.delete("/fase/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_fase(
    id: uuid.UUID,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)]
):
    fase = session.get(Fase, id)
    if not fase:
        raise HTTPException(status_code=404, detail="Fase tidak ditemukan")
    get_entity_or_404(session, JenisAyam, fase.jenis_ayam_id, current_pemilik.id)
    session.delete(fase)
    session.commit()


# --- STANDAR KONSUMSI ---
@router.put("/fase/{id}/standar-konsumsi", response_model=StandarKonsumsiPublic)
def upsert_standar_konsumsi(
    id: uuid.UUID,
    data_in: StandarKonsumsiCreateUpdate,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)]
):
    fase = session.get(Fase, id)
    if not fase:
        raise HTTPException(status_code=404, detail="Fase tidak ditemukan")
    get_entity_or_404(session, JenisAyam, fase.jenis_ayam_id, current_pemilik.id)

    db_obj = session.exec(select(StandarKonsumsi).where(StandarKonsumsi.fase_id == id)).first()
    if db_obj:
        for key, value in data_in.model_dump().items():
            setattr(db_obj, key, value)
    else:
        db_obj = StandarKonsumsi(fase_id=id, **data_in.model_dump())
    
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


@router.put("/fase/{id}/kebutuhan-nutrisi", response_model=List[KebutuhanNutrisiFasePublic])
def upsert_kebutuhan_nutrisi_fase(
    id: uuid.UUID,
    data_in: List[KebutuhanNutrisiFaseInput],
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)]
):
    fase = session.get(Fase, id)
    if not fase:
        raise HTTPException(status_code=404, detail="Fase tidak ditemukan")
    get_entity_or_404(session, JenisAyam, fase.jenis_ayam_id, current_pemilik.id)

    # Delete existing requirements for this phase
    session.query(KebutuhanNutrisiFase).filter(KebutuhanNutrisiFase.fase_id == id).delete()

    new_items = []
    for item in data_in:
        # Validate nutrisi exists and belongs to pemilik
        get_entity_or_404(session, Nutrisi, item.nutrisi_id, current_pemilik.id)
        
        db_obj = KebutuhanNutrisiFase(
            fase_id=id,
            nutrisi_id=item.nutrisi_id,
            batas_min=item.batas_min,
            batas_max=item.batas_max
        )
        session.add(db_obj)
        new_items.append(db_obj)
        
    session.commit()
    for obj in new_items:
        session.refresh(obj)
        
    return new_items


# --- NUTRISI ---
@router.post("/nutrisi", response_model=NutrisiPublic, status_code=status.HTTP_201_CREATED)
def create_nutrisi(
    data_in: NutrisiCreate,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)]
):
    db_obj = Nutrisi(pemilik_id=current_pemilik.id, **data_in.model_dump())
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


@router.get("/nutrisi", response_model=List[NutrisiPublic])
def list_nutrisi(
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)]
):
    return session.exec(select(Nutrisi).where(Nutrisi.pemilik_id == current_pemilik.id)).all()


@router.get("/nutrisi/{id}", response_model=NutrisiPublic)
def get_nutrisi(
    id: uuid.UUID,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)]
):
    return get_entity_or_404(session, Nutrisi, id, current_pemilik.id)


@router.patch("/nutrisi/{id}", response_model=NutrisiPublic)
def update_nutrisi(
    id: uuid.UUID,
    data_in: NutrisiUpdate,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)]
):
    db_obj = get_entity_or_404(session, Nutrisi, id, current_pemilik.id)
    update_data = data_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_obj, key, value)
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


@router.delete("/nutrisi/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_nutrisi(
    id: uuid.UUID,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)]
):
    db_obj = get_entity_or_404(session, Nutrisi, id, current_pemilik.id)
    session.delete(db_obj)
    session.commit()


# --- BAHAN PAKAN ---
@router.post("/bahan-pakan", response_model=BahanPakanPublic, status_code=status.HTTP_201_CREATED)
def create_bahan_pakan(
    data_in: BahanPakanCreate,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)]
):
    db_obj = BahanPakan(pemilik_id=current_pemilik.id, **data_in.model_dump())
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


@router.get("/bahan-pakan", response_model=List[BahanPakanPublic])
def list_bahan_pakan(
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)]
):
    return session.exec(select(BahanPakan).where(BahanPakan.pemilik_id == current_pemilik.id)).all()


@router.get("/bahan-pakan/{id}", response_model=BahanPakanPublic)
def get_bahan_pakan(
    id: uuid.UUID,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)]
):
    return get_entity_or_404(session, BahanPakan, id, current_pemilik.id)


@router.patch("/bahan-pakan/{id}", response_model=BahanPakanPublic)
def update_bahan_pakan(
    id: uuid.UUID,
    data_in: BahanPakanUpdate,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)]
):
    db_obj = get_entity_or_404(session, BahanPakan, id, current_pemilik.id)
    update_data = data_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_obj, key, value)
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


@router.delete("/bahan-pakan/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bahan_pakan(
    id: uuid.UUID,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)]
):
    db_obj = get_entity_or_404(session, BahanPakan, id, current_pemilik.id)
    session.delete(db_obj)
    session.commit()


@router.put("/bahan-pakan/{id}/nutrisi", response_model=List[KandunganNutrisiBahanPublic])
def upsert_kandungan_nutrisi_bahan(
    id: uuid.UUID,
    data_in: List[KandunganNutrisiBahanInput],
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)]
):
    bahan = get_entity_or_404(session, BahanPakan, id, current_pemilik.id)

    # Delete existing requirements for this ingredient
    session.query(KandunganNutrisiBahan).filter(KandunganNutrisiBahan.bahan_pakan_id == id).delete()

    new_items = []
    for item in data_in:
        # Validate nutrisi exists and belongs to pemilik
        get_entity_or_404(session, Nutrisi, item.nutrisi_id, current_pemilik.id)
        
        db_obj = KandunganNutrisiBahan(
            bahan_pakan_id=id,
            nutrisi_id=item.nutrisi_id,
            nilai_per_kg=item.nilai_per_kg
        )
        session.add(db_obj)
        new_items.append(db_obj)
        
    session.commit()
    for obj in new_items:
        session.refresh(obj)
        
    return new_items
