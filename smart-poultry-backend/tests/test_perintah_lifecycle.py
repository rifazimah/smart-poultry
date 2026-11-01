"""State machine perintah, timeout, deteksi offline, idempotensi log, stop darurat, notifikasi, audit."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlmodel import Session, select

from app.database import engine
from app.models.akses import AuditLog
from app.models.fisik import Alat, Stok
from app.models.operasional import Perintah
from tests.conftest import login
from tests.helpers import (
    API, buat_kandang, buat_master, device_h, get, heartbeat, post, simpan_formulasi_otomatis,
)


@pytest.fixture
def setup(client, pemilik):
    d = buat_master(client, pemilik)
    k = buat_kandang(client, pemilik, d)
    heartbeat(client, k)
    f = simpan_formulasi_otomatis(client, pemilik, k)
    return d, k, f


def perintah_baru(client, h, k, f):
    return post(client, h, f"/kandang/{k.id}/perintah/beri-makan", {"formulasi_id": f})["id"]


def dev(client, k, pid, aksi, json=None):
    return client.post(f"{API}/device/perintah/{pid}/{aksi}", json=json or {}, headers=device_h(k))


def log_body(status="SUKSES", uid=None):
    return {"id_eksekusi_unik": uid or str(uuid.uuid4()), "berat_aktual": 1250, "status": status}


def mundurkan_perintah(pid, detik):
    with Session(engine) as s:
        p = s.get(Perintah, uuid.UUID(pid))
        p.dibuat_pada = datetime.now(timezone.utc) - timedelta(seconds=detik)
        s.add(p)
        s.commit()


def mundurkan_sinkron(alat_id, detik):
    with Session(engine) as s:
        a = s.get(Alat, uuid.UUID(alat_id))
        a.waktu_terakhir_sinkron = datetime.now(timezone.utc) - timedelta(seconds=detik)
        s.add(a)
        s.commit()


def jenis_notif(client, h):
    return [n["jenis"] for n in get(client, h, "/notifikasi")]


# ---------- transisi ----------

def test_mulai_langsung_dari_pending_409(client, pemilik, setup):
    _, k, f = setup
    pid = perintah_baru(client, pemilik, k, f)
    assert dev(client, k, pid, "mulai").status_code == 409


def test_ambil_dan_mulai_idempoten(client, pemilik, setup):
    _, k, f = setup
    pid = perintah_baru(client, pemilik, k, f)
    assert dev(client, k, pid, "ambil").status_code == 200
    assert dev(client, k, pid, "ambil").status_code == 200
    assert dev(client, k, pid, "mulai").status_code == 200
    assert dev(client, k, pid, "mulai").status_code == 200


def test_log_dari_pending_409(client, pemilik, setup):
    _, k, f = setup
    pid = perintah_baru(client, pemilik, k, f)
    assert dev(client, k, pid, "log", log_body()).status_code == 409


# ---------- idempotensi log ----------

def test_log_duplikat_200_tanpa_pengurangan_ganda(client, pemilik, setup):
    _, k, f = setup
    pid = perintah_baru(client, pemilik, k, f)
    dev(client, k, pid, "ambil")
    dev(client, k, pid, "mulai")
    body = log_body()
    r1 = dev(client, k, pid, "log", body)
    stok1 = {s["wadah_id"]: s["jumlah_estimasi"] for s in get(client, pemilik, f"/kandang/{k.id}/stok")}
    r2 = dev(client, k, pid, "log", body)
    stok2 = {s["wadah_id"]: s["jumlah_estimasi"] for s in get(client, pemilik, f"/kandang/{k.id}/stok")}
    assert r1.status_code == 201 and r2.status_code == 200
    assert r1.json()["id"] == r2.json()["id"]
    assert stok1 == stok2


def test_log_lain_untuk_perintah_yang_sama_409(client, pemilik, setup):
    _, k, f = setup
    pid = perintah_baru(client, pemilik, k, f)
    dev(client, k, pid, "ambil")
    dev(client, k, pid, "mulai")
    assert dev(client, k, pid, "log", log_body()).status_code == 201
    assert dev(client, k, pid, "log", log_body()).status_code == 409


def test_id_eksekusi_dipakai_perintah_lain_409(client, pemilik, setup):
    _, k, f = setup
    uid = str(uuid.uuid4())
    p1 = perintah_baru(client, pemilik, k, f)
    dev(client, k, p1, "ambil")
    dev(client, k, p1, "mulai")
    assert dev(client, k, p1, "log", log_body(uid=uid)).status_code == 201
    heartbeat(client, k)
    p2 = perintah_baru(client, pemilik, k, f)
    dev(client, k, p2, "ambil")
    dev(client, k, p2, "mulai")
    assert dev(client, k, p2, "log", log_body(uid=uid)).status_code == 409


def test_skipped_stock_menjadi_gagal_tanpa_pengurangan(client, pemilik, setup):
    _, k, f = setup
    sebelum = get(client, pemilik, f"/kandang/{k.id}/stok")
    pid = perintah_baru(client, pemilik, k, f)
    dev(client, k, pid, "ambil")
    dev(client, k, pid, "mulai")
    assert dev(client, k, pid, "log", log_body("SKIPPED_STOCK")).status_code == 201
    assert get(client, pemilik, f"/perintah/{pid}")["status"] == "GAGAL"
    assert get(client, pemilik, f"/kandang/{k.id}/stok") == sebelum


# ---------- timeout & offline ----------

def test_pending_kedaluwarsa_menjadi_timeout_dan_alat_bebas_lagi(client, pemilik, setup):
    _, k, f = setup
    pid = perintah_baru(client, pemilik, k, f)
    mundurkan_perintah(pid, 120)
    assert get(client, pemilik, f"/perintah/{pid}")["status"] == "TIMEOUT"
    assert "PERINTAH_GAGAL" in jenis_notif(client, pemilik)
    # alat tidak lagi terblokir
    assert perintah_baru(client, pemilik, k, f)


def test_berjalan_lebih_lama_dari_batas_timeout(client, pemilik, setup):
    _, k, f = setup
    pid = perintah_baru(client, pemilik, k, f)
    dev(client, k, pid, "ambil")
    dev(client, k, pid, "mulai")
    mundurkan_perintah(pid, 120)  # belum melewati 300 dtk
    assert get(client, pemilik, f"/perintah/{pid}")["status"] == "BERJALAN"
    mundurkan_perintah(pid, 400)
    assert get(client, pemilik, f"/perintah/{pid}")["status"] == "TIMEOUT"
    assert dev(client, k, pid, "log", log_body()).status_code == 409


def test_alat_offline_bila_heartbeat_kedaluwarsa(client, pemilik, setup):
    _, k, f = setup
    assert get(client, pemilik, f"/kandang/{k.id}")["status_alat"] == "ONLINE"
    mundurkan_sinkron(k.alat_id, 300)
    assert get(client, pemilik, f"/kandang/{k.id}")["status_alat"] == "OFFLINE"
    get(client, pemilik, f"/kandang/{k.id}")  # panggilan kedua tidak menambah notifikasi
    assert jenis_notif(client, pemilik).count("ALAT_OFFLINE") == 1
    r = client.post(f"{API}/kandang/{k.id}/perintah/beri-makan", json={"formulasi_id": f}, headers=pemilik)
    assert r.status_code == 409
    heartbeat(client, k)
    assert get(client, pemilik, f"/kandang/{k.id}")["status_alat"] == "ONLINE"


def test_heartbeat_error_membuat_notifikasi(client, pemilik, setup):
    _, k, _ = setup
    heartbeat(client, k, "ERROR")
    assert "ALAT_ERROR" in jenis_notif(client, pemilik)


# ---------- stop darurat ----------

def test_stop_darurat_membatalkan_perintah_aktif_dan_boleh_saat_offline(client, pemilik, setup):
    _, k, f = setup
    pid = perintah_baru(client, pemilik, k, f)
    dev(client, k, pid, "ambil")
    dev(client, k, pid, "mulai")
    mundurkan_sinkron(k.alat_id, 300)  # offline

    r = client.post(f"{API}/kandang/{k.id}/perintah/stop-darurat", json={}, headers=pemilik)
    assert r.status_code == 201, r.text
    assert r.json()["tipe"] == "STOP_DARURAT" and r.json()["status"] == "PENDING"
    assert get(client, pemilik, f"/perintah/{pid}")["status"] == "GAGAL"

    # alat mengambil & menuntaskan stop darurat
    hb = heartbeat(client, k)
    sid = hb["perintah_pending"]["id"]
    assert sid == r.json()["id"]
    dev(client, k, sid, "ambil")
    dev(client, k, sid, "mulai")
    assert dev(client, k, sid, "log", log_body()).status_code == 201
    assert get(client, pemilik, f"/perintah/{sid}")["status"] == "SUKSES"


# ---------- notifikasi ----------

def test_notifikasi_ke_pemilik_dan_pekerja_ditugaskan(client, pemilik, setup):
    _, k, f = setup
    post(client, pemilik, "/users", {"nama": "Budi", "email": "budi@example.com",
                                      "kata_sandi": "budi12345", "role": "PEKERJA"})
    pekerja_id = get(client, pemilik, "/users")[0]["id"]
    post(client, pemilik, f"/users/{pekerja_id}/penugasan", {"kandang_id": k.id, "tanggal_mulai": "2026-11-01"})
    hp = login(client, "budi@example.com", "budi12345")

    pid = post(client, hp, f"/kandang/{k.id}/perintah/beri-makan", {"formulasi_id": f})["id"]  # Pekerja boleh
    dev(client, k, pid, "ambil")
    dev(client, k, pid, "mulai")
    dev(client, k, pid, "log", log_body())
    assert "PERINTAH_SUKSES" in jenis_notif(client, pemilik)
    assert "PERINTAH_SUKSES" in jenis_notif(client, hp)


def test_stok_kosong_dan_menipis(client, pemilik, setup):
    d, k, f = setup
    item = {i["bahan_pakan_id"]: i["berat_per_sesi"] for i in get(client, pemilik, f"/formulasi/{f}")["item"]}
    # jagung: tepat habis setelah satu sesi
    post(client, pemilik, f"/wadah/{k.wadah['jagung']}/stok/koreksi",
         {"jumlah_baru": item[d.jagung], "alasan": "uji"})
    # kedelai: di bawah ambang setelah satu sesi
    with Session(engine) as s:
        st = s.exec(select(Stok).where(Stok.wadah_id == uuid.UUID(k.wadah["kedelai"]))).first()
        st.ambang_menipis = 100000.0
        s.add(st)
        s.commit()

    pid = perintah_baru(client, pemilik, k, f)
    dev(client, k, pid, "ambil")
    dev(client, k, pid, "mulai")
    dev(client, k, pid, "log", log_body())
    jenis = jenis_notif(client, pemilik)
    assert "STOK_KOSONG" in jenis
    assert "STOK_MENIPIS" in jenis


def test_pindah_fase_membuat_notifikasi_perlu_ditinjau(client, pemilik, setup):
    d, k, _ = setup
    client.patch(f"{API}/siklus/{k.siklus_id}/fase", json={"fase_id": d.fase_grower}, headers=pemilik)
    assert "PERLU_DITINJAU" in jenis_notif(client, pemilik)


# ---------- audit ----------

def test_koreksi_stok_menulis_audit_log(client, pemilik, setup):
    _, k, _ = setup
    post(client, pemilik, f"/wadah/{k.wadah['jagung']}/stok/koreksi", {"jumlah_baru": 500, "alasan": "salah timbang"})
    with Session(engine) as s:
        log = s.exec(select(AuditLog).where(AuditLog.aksi == "KOREKSI_STOK")).first()
        assert log and log.catatan == "salah timbang" and log.nilai_baru == "500.0"
