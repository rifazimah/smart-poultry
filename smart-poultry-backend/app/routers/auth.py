from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

from app.database import get_session
from app.models.akses import User
from app.schemas.auth import LoginRequest, TokenResponse, GantiKataSandiRequest
from app.schemas.user import UserPublic
from app.services.auth import (
    autentikasi_pengguna,
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


def _alamat_klien(request: Request) -> str:
    """Alamat klien langsung. Di balik reverse proxy, jalankan uvicorn dengan --proxy-headers (UVICORN_ARGS)."""
    return request.client.host if request.client else "tidak-diketahui"


@router.post("/login", response_model=TokenResponse)
def login(
    login_req: LoginRequest,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
):
    """
    Login endpoint UTAMA untuk Frontend (menerima JSON).
    Body: {"email": "...", "kata_sandi": "..."}
    """
    user = autentikasi_pengguna(session, login_req.email, login_req.kata_sandi, _alamat_klien(request))
    access_token = create_access_token(data={"sub": user.email})
    return TokenResponse(access_token=access_token, token_type="bearer", user=user)


@router.post("/swagger-login", include_in_schema=False)
def swagger_login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    request: Request,
    session: Annotated[Session, Depends(get_session)],
):
    """
    Endpoint KHUSUS untuk fitur tombol 'Authorize' bawaan Swagger UI (/docs).
    Frontend TIDAK BOLEH memanggil endpoint ini. Endpoint ini disembunyikan dari dokumentasi.
    Menerima: application/x-www-form-urlencoded (username, password).
    """
    user = autentikasi_pengguna(session, form_data.username, form_data.password, _alamat_klien(request))
    access_token = create_access_token(data={"sub": user.email})
    # Swagger UI hanya membaca access_token dan token_type
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserPublic)
def get_me(current_user: Annotated[User, Depends(get_current_user)]):
    """Mendapatkan profil user yang sedang login."""
    return current_user


@router.post("/ganti-kata-sandi", status_code=status.HTTP_204_NO_CONTENT)
def ganti_kata_sandi(
    req: GantiKataSandiRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Ganti kata sandi untuk user yang sedang login."""
    if not verify_password(req.kata_sandi_lama, current_user.kata_sandi_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kata sandi lama salah",
        )
        
    current_user.kata_sandi_hash = get_password_hash(req.kata_sandi_baru)
    session.add(current_user)
    session.commit()
