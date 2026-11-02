"""
Fixture test. Memakai database terpisah (smart_poultry_test) di server Postgres yang sama
dengan DATABASE_URL; dibuat otomatis bila belum ada. Override via env TEST_DATABASE_URL.

DATABASE_URL harus di-set SEBELUM `app` diimport, karena engine dibuat saat import.
"""
import os
import re
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError


def _test_database_url() -> str:
    explicit = os.environ.get("TEST_DATABASE_URL")
    if explicit:
        return explicit
    # Jangan import app.config di sini: modul itu membuat `settings` saat diimport,
    # sehingga akan membaca DATABASE_URL dev sebelum kita sempat menimpanya.
    from dotenv import dotenv_values
    base = os.environ.get("DATABASE_URL") or dotenv_values(BACKEND_DIR / ".env").get("DATABASE_URL")
    if not base:
        raise RuntimeError("Set TEST_DATABASE_URL atau DATABASE_URL di .env untuk menjalankan test")
    return base.rsplit("/", 1)[0] + "/smart_poultry_test"


BACKEND_DIR = Path(__file__).resolve().parents[1]
TEST_URL = _test_database_url()
# Pengaman: test menghapus seluruh schema, jadi hanya boleh berjalan pada database *_test.
if not TEST_URL.rsplit("/", 1)[-1].split("?")[0].endswith("_test"):
    raise RuntimeError(f"Nama database test harus berakhiran '_test': {TEST_URL.rsplit('/', 1)[-1]}")


def _pastikan_database_test_ada(url_str: str) -> None:
    """Buat database *_test bila belum ada (konek ke database `postgres` pada server yang sama)."""
    url = make_url(url_str)
    nama = url.database
    if not re.fullmatch(r"[A-Za-z0-9_]+_test", nama or ""):
        raise RuntimeError(f"Nama database test tidak valid: {nama!r}")
    admin = create_engine(
        url.set(database="postgres"), isolation_level="AUTOCOMMIT", connect_args={"connect_timeout": 5}
    )
    try:
        with admin.connect() as conn:
            ada = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": nama}).scalar()
            if not ada:
                conn.execute(text(f'CREATE DATABASE "{nama}"'))
    except OperationalError as e:
        raise RuntimeError(
            f"Tidak bisa tersambung ke Postgres di {url.host}:{url.port}. Jalankan `docker compose up -d` "
            f"dan periksa DATABASE_URL di .env. Detail: {e.orig}"
        ) from e
    finally:
        admin.dispose()


_pastikan_database_test_ada(TEST_URL)
os.environ["DATABASE_URL"] = TEST_URL

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import SQLModel, Session  # noqa: E402

from app.main import app  # noqa: E402
from app.database import engine  # noqa: E402
from app.models.akses import User  # noqa: E402
from app.models.enums import PeranUser, StatusUser  # noqa: E402
from app.services.auth import get_password_hash  # noqa: E402

assert engine.url.database.endswith("_test"), f"Engine menunjuk ke {engine.url.database}, bukan database test"


@pytest.fixture(scope="session", autouse=True)
def _migrasi():
    """Jalankan migrasi dari nol sekali per sesi (sekaligus menguji migrasi)."""
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def _bersihkan_data():
    yield
    tabel = [t.name for t in SQLModel.metadata.sorted_tables]
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE " + ", ".join(f'"{t}"' for t in tabel) + " CASCADE"))


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def buat_user(email: str, role: PeranUser = PeranUser.PEMILIK, sandi: str = "rahasia123", nama: str = "Uji", **extra):
    with Session(engine) as s:
        u = User(
            nama=nama, email=email, kata_sandi_hash=get_password_hash(sandi),
            role=role, status=StatusUser.AKTIF, **extra,
        )
        s.add(u)
        s.commit()
        s.refresh(u)
        return u.id


def login(client: TestClient, email: str, sandi: str = "rahasia123") -> dict:
    r = client.post("/api/v1/auth/login", json={"email": email, "kata_sandi": sandi})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def pemilik(client):
    buat_user("pemilik@example.com", nama="Pemilik Uji")
    return login(client, "pemilik@example.com")


@pytest.fixture
def pemilik_lain(client):
    buat_user("lain@example.com", nama="Pemilik Lain")
    return login(client, "lain@example.com")
