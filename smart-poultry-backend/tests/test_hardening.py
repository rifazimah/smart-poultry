"""Hardening Fase 4: guard production, login (NONAKTIF + rate-limit), seed admin, hash device token."""
import hashlib
import uuid

import pytest
from alembic import command
from alembic.config import Config
from pydantic import ValidationError
from sqlalchemy import inspect, text
from sqlmodel import Session, select

import seed_admin
import seed_demo
from app.config import Settings, settings
from app.database import engine
from app.models.fisik import Alat
from app.services.ratelimit import pembatas_login
from tests.conftest import BACKEND_DIR, login
from tests.helpers import API, buat_kandang, buat_master, get, post

SECRET_KUAT = "k" * 20 + "R4nd0m-Secret-9876543210"  # >= 32 karakter, tanpa kata 'ganti'


# ---------- guard konfigurasi production ----------

@pytest.mark.parametrize("rahasia", [
    "pendek",
    "ganti-ini-di-.env",
    "ganti-dengan-string-acak-panjang",   # 32 karakter tetapi placeholder
    "dev-only-ganti-di-production",
    "x" * 31,                              # kurang dari 32
])
def test_production_menolak_jwt_secret_lemah(rahasia):
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(_env_file=None, environment="production", jwt_secret=rahasia)


def test_production_menolak_secret_bawaan_bila_tidak_diisi(monkeypatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)  # CI mengisinya lewat environment
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(_env_file=None, environment="production")


def test_production_menerima_secret_kuat_dan_mematikan_sql_echo():
    s = Settings(_env_file=None, environment="production", jwt_secret=SECRET_KUAT, sql_echo=True)
    assert s.sql_echo is False


def test_development_menerima_secret_bawaan(monkeypatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)
    s = Settings(_env_file=None, environment="development")
    assert s.jwt_secret and s.environment == "development"


def test_environment_dari_variabel_lingkungan(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
    monkeypatch.setenv("JWT_SECRET", SECRET_KUAT)
    assert Settings(_env_file=None).environment == "production"


def test_environment_tidak_dikenal_ditolak():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, environment="staging")


# ---------- login: user NONAKTIF ----------

def buat_pekerja_nonaktif(client, pemilik):
    post(client, pemilik, "/users", {"nama": "Budi", "email": "budi@example.com", "kata_sandi": "budi12345", "role": "PEKERJA"})
    budi = get(client, pemilik, "/users")[0]["id"]
    r = client.patch(f"{API}/users/{budi}/status", json={"status": "NONAKTIF"}, headers=pemilik)
    assert r.status_code == 200
    return budi


def test_login_user_nonaktif_ditolak_403(client, pemilik):
    buat_pekerja_nonaktif(client, pemilik)
    r = client.post(f"{API}/auth/login", json={"email": "budi@example.com", "kata_sandi": "budi12345"})
    assert r.status_code == 403 and r.json()["detail"] == "User nonaktif"
    r = client.post(f"{API}/auth/swagger-login", data={"username": "budi@example.com", "password": "budi12345"})
    assert r.status_code == 403


def test_login_nonaktif_dengan_sandi_salah_tidak_membocorkan_status(client, pemilik):
    buat_pekerja_nonaktif(client, pemilik)
    r = client.post(f"{API}/auth/login", json={"email": "budi@example.com", "kata_sandi": "salah"})
    assert r.status_code == 401


# ---------- login: rate-limit ----------

def salah(client, email="pemilik@example.com"):
    return client.post(f"{API}/auth/login", json={"email": email, "kata_sandi": "salah"})


def benar(client, email="pemilik@example.com"):
    return client.post(f"{API}/auth/login", json={"email": email, "kata_sandi": "rahasia123"})


def test_batas_default_lima_percobaan():
    assert settings.login_max_gagal == 5 and settings.login_jendela_detik == 300


def test_percobaan_keenam_diblokir_429_walau_sandi_benar(client, pemilik):
    for _ in range(5):
        assert salah(client).status_code == 401
    r = salah(client)
    assert r.status_code == 429
    assert 1 <= int(r.headers["Retry-After"]) <= 300
    assert "Terlalu banyak" in r.json()["detail"]
    assert benar(client).status_code == 429  # terkunci meski sandi benar


def test_email_lain_tidak_terpengaruh(client, pemilik, pemilik_lain):
    for _ in range(5):
        salah(client)
    assert salah(client).status_code == 429
    assert benar(client, "lain@example.com").status_code == 200


def test_login_sukses_mereset_hitungan(client, pemilik):
    for _ in range(4):
        salah(client)
    assert benar(client).status_code == 200
    for _ in range(4):
        assert salah(client).status_code == 401  # tidak 429: hitungan dimulai dari nol


def test_kunci_berakhir_setelah_jendela_waktu(client, pemilik, monkeypatch):
    waktu = {"t": 1000.0}
    monkeypatch.setattr(pembatas_login, "clock", lambda: waktu["t"])
    for _ in range(5):
        salah(client)
    assert benar(client).status_code == 429
    waktu["t"] += 299
    assert benar(client).status_code == 429
    waktu["t"] += 2  # total 301 detik
    assert benar(client).status_code == 200


def test_swagger_login_berbagi_pembatas_dengan_login(client, pemilik):
    for _ in range(3):
        salah(client)
    for _ in range(2):
        r = client.post(f"{API}/auth/swagger-login", data={"username": "pemilik@example.com", "password": "salah"})
        assert r.status_code == 401
    assert salah(client).status_code == 429


def test_email_tak_terdaftar_juga_dibatasi(client):
    for _ in range(5):
        assert salah(client, "hantu@example.com").status_code == 401
    assert salah(client, "hantu@example.com").status_code == 429


# ---------- seed admin ----------

def hapus_user(email):
    with engine.begin() as conn:
        conn.execute(text('DELETE FROM "user" WHERE email = :e'), {"e": email})


def test_seed_admin_development_memakai_password_bawaan(client, monkeypatch, capsys):
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "admin_password", None)
    email, sandi = seed_admin.create_initial_pemilik()
    assert (email, sandi) == (settings.admin_email, "admin123")
    assert "admin123" in capsys.readouterr().out
    assert login(client, email, sandi)
    assert seed_admin.create_initial_pemilik() is None  # idempoten


def test_seed_admin_memakai_admin_password_dari_environment(client, monkeypatch, capsys):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "admin_password", "Kata-Sandi-Khusus-1!")
    email, sandi = seed_admin.create_initial_pemilik()
    assert sandi == "Kata-Sandi-Khusus-1!"
    assert "Kata-Sandi-Khusus-1!" not in capsys.readouterr().out  # tidak dicetak di production
    assert login(client, email, sandi)


def test_seed_admin_production_tanpa_password_membuat_acak_dan_mencetak_sekali(client, monkeypatch, capsys):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "admin_password", None)
    email, sandi = seed_admin.create_initial_pemilik()
    assert sandi != "admin123" and len(sandi) >= 12
    keluaran = capsys.readouterr().out
    assert keluaran.count(sandi) == 1
    assert login(client, email, sandi)
    # akun sudah ada: tidak membuat password acak baru dan tidak mencetaknya
    assert seed_admin.create_initial_pemilik() is None
    assert sandi not in capsys.readouterr().out


def test_seed_demo_menolak_berjalan_di_production(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    with pytest.raises(SystemExit, match="production"):
        seed_demo.main()


# ---------- hash device token ----------

def alat_di_db(alat_id):
    with Session(engine) as s:
        return s.exec(select(Alat).where(Alat.id == uuid.UUID(alat_id))).one()


def hb(client, token):
    return client.post(f"{API}/device/heartbeat", json={"status": "ONLINE"}, headers={"X-Device-Token": token})


def test_token_alat_disimpan_sebagai_hash(client, pemilik):
    k = buat_kandang(client, pemilik, buat_master(client, pemilik))
    token = k.device_token
    assert len(token) == 64 and int(token, 16) >= 0  # token mentah 256-bit dikembalikan sekali
    alat = alat_di_db(k.alat_id)
    assert alat.device_token_hash == hashlib.sha256(token.encode()).hexdigest()
    with engine.connect() as conn:
        baris = conn.execute(text("SELECT * FROM alat WHERE id = :i"), {"i": uuid.UUID(k.alat_id)}).one()
    assert token not in [str(v) for v in baris]  # token mentah tidak ada di kolom mana pun
    assert hb(client, token).status_code == 200
    assert hb(client, "token-salah").status_code == 401


def test_rotasi_token_mengganti_hash_dan_mencabut_token_lama(client, pemilik):
    k = buat_kandang(client, pemilik, buat_master(client, pemilik))
    lama = k.device_token
    baru = post(client, pemilik, f"/alat/{k.alat_id}/rotasi-token")["device_token"]
    assert baru != lama and len(baru) == 64
    assert alat_di_db(k.alat_id).device_token_hash == hashlib.sha256(baru.encode()).hexdigest()
    assert hb(client, lama).status_code == 401
    assert hb(client, baru).status_code == 200


def test_endpoint_lain_tidak_pernah_menampilkan_token_atau_hash(client, pemilik):
    k = buat_kandang(client, pemilik, buat_master(client, pemilik))
    for path in (f"/kandang/{k.id}", f"/kandang/{k.id}/alat"):
        teks = client.get(API + path, headers=pemilik).text
        assert k.device_token not in teks and "device_token" not in teks


# ---------- migrasi token pada data lama ----------

def test_migrasi_mengubah_token_lama_menjadi_hash_dan_alat_tetap_valid(client):
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    token_lama = "ab" * 32
    uid, kid, aid = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

    command.downgrade(cfg, "9d4e7a1c5b20")  # skema sebelum hash token
    try:
        kolom = {c["name"] for c in inspect(engine).get_columns("alat")}
        assert "device_token" in kolom and "device_token_hash" not in kolom
        with engine.begin() as conn:
            conn.execute(text(
                "INSERT INTO \"user\"(id, nama, email, kata_sandi_hash, role, status, dibuat_pada) "
                "VALUES (:i, 'Lama', 'lama@example.com', 'x', 'PEMILIK', 'AKTIF', now())"), {"i": uid})
            conn.execute(text(
                "INSERT INTO kandang(id, pemilik_id, nama, status) VALUES (:k, :u, 'K Lama', 'AKTIF')"), {"k": kid, "u": uid})
            conn.execute(text(
                "INSERT INTO alat(id, kandang_id, device_token, status) VALUES (:a, :k, :t, 'OFFLINE')"),
                {"a": aid, "k": kid, "t": token_lama})
    finally:
        command.upgrade(cfg, "head")

    kolom = {c["name"] for c in inspect(engine).get_columns("alat")}
    assert "device_token_hash" in kolom and "device_token" not in kolom
    with engine.connect() as conn:
        tersimpan = conn.execute(text("SELECT device_token_hash FROM alat WHERE id = :a"), {"a": aid}).scalar()
    assert tersimpan == hashlib.sha256(token_lama.encode()).hexdigest()
    assert hb(client, token_lama).status_code == 200  # alat lama tetap bisa memakai token lamanya
    assert hb(client, tersimpan).status_code == 401   # hash bukan token yang valid
