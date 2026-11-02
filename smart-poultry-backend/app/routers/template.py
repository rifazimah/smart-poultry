from typing import Annotated, List

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.database import get_session
from app.models.akses import User
from app.schemas.masterdata import JenisAyamPublic
from app.schemas.template import SalinTemplateRequest, TemplateJenisAyam
from app.services.auth import get_current_pemilik
from app.services.template_jenis_ayam import daftar_template, salin_template

router = APIRouter(tags=["Template Referensi"])


@router.get("/template/jenis-ayam", response_model=List[TemplateJenisAyam])
def list_template(_: Annotated[User, Depends(get_current_pemilik)]):
    """Daftar template bawaan (read-only, tidak terikat Pemilik). Nilai hanya contoh, sesuaikan sebelum dipakai."""
    return daftar_template()


@router.post("/template/jenis-ayam/{template_id}/salin", response_model=JenisAyamPublic, status_code=status.HTTP_201_CREATED)
def salin(
    template_id: str,
    current_pemilik: Annotated[User, Depends(get_current_pemilik)],
    session: Annotated[Session, Depends(get_session)],
    body: SalinTemplateRequest = SalinTemplateRequest(),
):
    """
    Salin template ke akun Pemilik: jenis ayam + fase + kebutuhan nutrisi + standar konsumsi.
    Nutrisi dicocokkan berdasarkan nama dengan nutrisi milik Pemilik; yang belum ada dibuat otomatis.
    """
    return salin_template(session, current_pemilik, template_id, body.nama)
