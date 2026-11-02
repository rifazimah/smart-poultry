"""
Membuat akun Pemilik pertama. Idempoten: dilewati bila email sudah terdaftar.

Kredensial dari environment/.env: ADMIN_EMAIL (default admin@smartpoultry.com) dan ADMIN_PASSWORD.
- development tanpa ADMIN_PASSWORD : password bawaan `admin123` (hanya untuk komputer lokal)
- production  tanpa ADMIN_PASSWORD : password acak, dicetak SEKALI di akhir (simpan segera)
- production  dengan ADMIN_PASSWORD: dipakai apa adanya dan tidak dicetak
"""
import secrets
import uuid
from datetime import datetime, timezone

from sqlmodel import Session, select

from app.config import settings
from app.database import engine
from app.models.akses import User
from app.models.enums import PeranUser, StatusUser
from app.services.auth import get_password_hash

PASSWORD_DEV = "admin123"


def kredensial_admin():
    """Mengembalikan (email, password, acak). Di production tanpa ADMIN_PASSWORD password dibuat acak."""
    email, sandi = settings.admin_email, settings.admin_password
    if sandi:
        return email, sandi, False
    if settings.environment == "production":
        return email, secrets.token_urlsafe(12), True
    return email, PASSWORD_DEV, False


def create_initial_pemilik():
    """Mengembalikan (email, password) bila akun dibuat, atau None bila sudah ada."""
    email, sandi, acak = kredensial_admin()
    with Session(engine) as session:
        existing = session.exec(select(User).where(User.email == email)).first()
        if existing:
            print(f"Pemilik dengan email {email} sudah ada.")
            return None

        user = User(
            id=uuid.uuid4(),
            nama="Pemilik Pertama",
            email=email,
            kata_sandi_hash=get_password_hash(sandi),
            role=PeranUser.PEMILIK,
            status=StatusUser.AKTIF,
            dibuat_pada=datetime.now(timezone.utc),
        )
        session.add(user)
        session.commit()

    if settings.environment != "production":
        print(f"Berhasil membuat Pemilik perdana: {email} / {sandi}")
    elif acak:
        print(f"Berhasil membuat Pemilik perdana: {email}")
        print(f"Password acak (tampil SEKALI, simpan sekarang): {sandi}")
    else:
        print(f"Berhasil membuat Pemilik perdana: {email} (password dari ADMIN_PASSWORD)")
    return email, sandi


if __name__ == "__main__":
    create_initial_pemilik()
