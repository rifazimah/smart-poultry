import hashlib
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlmodel import Session, select

from app.config import settings
from app.database import get_session
from app.models.akses import User
from app.models.enums import StatusUser, PeranUser
from app.schemas.auth import TokenData
from app.services.ratelimit import pembatas_login

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# tokenUrl is used exclusively by Swagger UI's 'Authorize' button. 
# We point it to a special swagger-only endpoint so our main /login stays pure JSON.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/swagger-login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def hash_device_token(token: str) -> str:
    """
    SHA-256 (hex) dari token alat. Token alat adalah 256-bit acak (secrets.token_hex(32)), sehingga hash tanpa salt
    cukup; yang disimpan di database hanya hash ini, token mentah hanya ditampilkan sekali saat dibuat/dirotasi.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def autentikasi_pengguna(session: Session, email: str, kata_sandi: str, klien: str) -> User:
    """
    Verifikasi email+kata sandi untuk login. Percobaan gagal dibatasi per (email, alamat klien):
    429 + Retry-After bila melewati batas. User NONAKTIF ditolak dengan 403 (setelah kata sandi benar,
    agar status akun tidak bocor ke penebak kata sandi).
    """
    kunci = f"{email.strip().lower()}|{klien}"
    pembatas_login.periksa(kunci)

    user = session.exec(select(User).where(User.email == email)).first()
    if not user or not verify_password(kata_sandi, user.kata_sandi_hash):
        pembatas_login.catat_gagal(kunci)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau kata sandi salah",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.status == StatusUser.NONAKTIF:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User nonaktif")

    pembatas_login.reset(kunci)
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm="HS256")
    return encoded_jwt

def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[Session, Depends(get_session)]
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    
    user = session.exec(select(User).where(User.email == token_data.email)).first()
    if user is None:
        raise credentials_exception
        
    if user.status == StatusUser.NONAKTIF:
        raise HTTPException(status_code=403, detail="User nonaktif")
        
    return user

def get_current_pemilik(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    if current_user.role != PeranUser.PEMILIK:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Endpoint ini hanya dapat diakses oleh PEMILIK",
        )
    return current_user
