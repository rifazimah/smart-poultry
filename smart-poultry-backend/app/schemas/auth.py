from typing import Optional

from pydantic import BaseModel, EmailStr
from app.schemas.user import UserPublic


class LoginRequest(BaseModel):
    email: EmailStr
    kata_sandi: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserPublic


class GantiKataSandiRequest(BaseModel):
    kata_sandi_lama: str
    kata_sandi_baru: str


class TokenData(BaseModel):
    email: Optional[str] = None
