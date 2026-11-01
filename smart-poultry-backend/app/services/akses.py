import uuid

from fastapi import HTTPException
from sqlmodel import Session


def get_entity_or_404(session: Session, model_class, entity_id: uuid.UUID, pemilik_id: uuid.UUID):
    """Ambil entitas ber-`pemilik_id`; 404 bila tidak ada atau milik Pemilik lain."""
    entity = session.get(model_class, entity_id)
    if not entity or entity.pemilik_id != pemilik_id:
        raise HTTPException(status_code=404, detail=f"{model_class.__name__} tidak ditemukan")
    return entity
