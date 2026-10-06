from app.database import engine
from sqlmodel import Session, select
from app.models.akses import User
from app.models.enums import PeranUser, StatusUser
from app.services.auth import get_password_hash
import uuid

def create_initial_pemilik():
    with Session(engine) as session:
        email = "admin@smartpoultry.com"
        existing = session.exec(select(User).where(User.email == email)).first()
        if existing:
            print(f"Pemilik dengan email {email} sudah ada.")
            return

        from datetime import datetime, timezone
        user = User(
            id=uuid.uuid4(),
            nama="Pemilik Pertama",
            email=email,
            kata_sandi_hash=get_password_hash("admin123"),
            role=PeranUser.PEMILIK,
            status=StatusUser.AKTIF,
            dibuat_pada=datetime.now(timezone.utc)
        )
        session.add(user)
        session.commit()
        print(f"Berhasil membuat Pemilik perdana: {email} / admin123")

if __name__ == "__main__":
    create_initial_pemilik()
