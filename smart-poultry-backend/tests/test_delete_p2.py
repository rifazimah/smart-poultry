"""DELETE P2: siklus, formulasi, wadah, alat, kandang."""
import uuid

import pytest
from sqlalchemy import func
from sqlmodel import Session, select

from app.database import engine
from app.models.akses import AuditLog, PenugasanKandang
from app.models.fisik import Alat, Kandang, Stok, TransaksiStok, Wadah
from app.models.operasional import Formulasi, FormulasiItem, PerubahanPopulasi
from tests.conftest import login
from tests.helpers import (
    API, buat_kandang, buat_master, device_h, get, heartbeat, post, simpan_formulasi_otomatis,
)


@pytest.fixture
def setup(client, pemilik):
    d = buat_master(client, pemilik)
    k = buat_kandang(client, pemilik, d)
    return d, k


def hapus(client, h, path):
    return client.delete(API + path, headers=h)


def hitung(model, *kondisi):
    with Session(engine) as s:
        return s.exec(select(func.count()).select_from(model).where(*kondisi)).one()


def audit(aksi):
    with Session(engine) as s:
        return s.exec(select(AuditLog).where(AuditLog.aksi == aksi)).all()


def jalankan_perintah(client, h, k, formulasi_id):
    """Satu siklus beri makan penuh sampai SUKSES (meninggalkan riwayat perintah + pengeluaran stok)."""
    heartbeat(client, k)
    pid = post(client, h, f"/kandang/{k.id}/perintah/beri-makan", {"formulasi_id": formulasi_id})["id"]
    for aksi in ("ambil", "mulai"):
        assert client.post(f"{API}/device/perintah/{pid}/{aksi}", json={}, headers=device_h(k)).status_code == 200
    log = {"id_eksekusi_unik": str(uuid.uuid4()), "berat_aktual": 1250, "status": "SUKSES"}
    assert client.post(f"{API}/device/perintah/{pid}/log", json=log, headers=device_h(k)).status_code == 201
    return pid


def nolkan_stok(client, h, k):
    for wid in k.wadah.values():
        stok = next(s for s in get(client, h, f"/kandang/{k.id}/stok") if s["wadah_id"] == wid)
        if stok["jumlah_estimasi"] > 0:
            post(client, h, f"/wadah/{wid}/stok/koreksi", {"jumlah_baru": 0, "alasan": "dikosongkan sebelum hapus"})


def pekerja_login(client, h, k):
    post(client, h, "/users", {"nama": "Budi", "email": "budi@example.com", "kata_sandi": "budi12345", "role": "PEKERJA"})
    budi = get(client, h, "/users")[0]["id"]
    post(client, h, f"/users/{budi}/penugasan", {"kandang_id": k.id, "tanggal_mulai": "2026-11-01"})
    return login(client, "budi@example.com", "budi12345")


# ---------- siklus ----------

def test_hapus_siklus_bebas_beserta_populasi_dan_formulasi(client, pemilik, setup):
    _, k = setup
    simpan_formulasi_otomatis(client, pemilik, k)
    post(client, pemilik, f"/siklus/{k.siklus_id}/populasi", {"jenis": "MORTALITAS", "jumlah": 2, "tanggal": "2026-11-02"})
    sid = uuid.UUID(k.siklus_id)

    assert hapus(client, pemilik, f"/siklus/{k.siklus_id}").status_code == 204
    assert get(client, pemilik, f"/kandang/{k.id}/siklus/aktif") is None
    assert hitung(Formulasi, Formulasi.siklus_id == sid) == 0
    assert hitung(PerubahanPopulasi, PerubahanPopulasi.siklus_id == sid) == 0
    assert hitung(FormulasiItem) == 0
    assert len(audit("HAPUS_SIKLUS")) == 1
    # kandang tetap ada dan bisa mulai siklus baru
    assert get(client, pemilik, f"/kandang/{k.id}")["id"] == k.id


def test_hapus_siklus_yang_formulasinya_dipakai_perintah_ditolak(client, pemilik, setup):
    _, k = setup
    jalankan_perintah(client, pemilik, k, simpan_formulasi_otomatis(client, pemilik, k))
    r = hapus(client, pemilik, f"/siklus/{k.siklus_id}")
    assert r.status_code == 409 and "perintah" in r.json()["detail"]
    assert get(client, pemilik, f"/kandang/{k.id}/siklus/aktif")["id"] == k.siklus_id


# ---------- formulasi ----------

def test_hapus_formulasi_bebas(client, pemilik, setup):
    _, k = setup
    f = simpan_formulasi_otomatis(client, pemilik, k)
    assert hapus(client, pemilik, f"/formulasi/{f}").status_code == 204
    assert client.get(f"{API}/formulasi/{f}", headers=pemilik).status_code == 404
    assert hitung(FormulasiItem) == 0
    assert len(audit("HAPUS_FORMULASI")) == 1


def test_hapus_formulasi_yang_dipakai_perintah_ditolak(client, pemilik, setup):
    _, k = setup
    f = simpan_formulasi_otomatis(client, pemilik, k)
    jalankan_perintah(client, pemilik, k, f)
    assert hapus(client, pemilik, f"/formulasi/{f}").status_code == 409


# ---------- wadah ----------

def test_hapus_wadah_dengan_stok_ditolak_lalu_boleh_setelah_dikoreksi_nol(client, pemilik, setup):
    d, k = setup
    wid = k.wadah["dedak"]
    r = hapus(client, pemilik, f"/wadah/{wid}")
    assert r.status_code == 409 and "Koreksi stok" in r.json()["detail"]

    post(client, pemilik, f"/wadah/{wid}/stok/koreksi", {"jumlah_baru": 0, "alasan": "salah wadah"})
    assert hapus(client, pemilik, f"/wadah/{wid}").status_code == 204
    assert "Dedak" not in {s["nama_bahan"] for s in get(client, pemilik, f"/kandang/{k.id}/stok")}
    assert hitung(TransaksiStok, TransaksiStok.wadah_id == uuid.UUID(wid)) == 0
    assert hitung(Stok, Stok.wadah_id == uuid.UUID(wid)) == 0
    assert len(audit("HAPUS_WADAH")) == 1


def test_hapus_wadah_menandai_formulasi_perlu_ditinjau_bila_bahan_hilang(client, pemilik, setup):
    d, k = setup
    f = simpan_formulasi_otomatis(client, pemilik, k)
    wid = k.wadah["jagung"]
    post(client, pemilik, f"/wadah/{wid}/stok/koreksi", {"jumlah_baru": 0, "alasan": "uji"})
    assert hapus(client, pemilik, f"/wadah/{wid}").status_code == 204
    assert get(client, pemilik, f"/formulasi/{f}")["status"] == "PERLU_DITINJAU"
    assert "PERLU_DITINJAU" in [n["jenis"] for n in get(client, pemilik, "/notifikasi")]


def test_hapus_wadah_yang_pernah_mengeluarkan_pakan_ditolak(client, pemilik, setup):
    d, k = setup
    jalankan_perintah(client, pemilik, k, simpan_formulasi_otomatis(client, pemilik, k))
    wid = k.wadah["jagung"]
    post(client, pemilik, f"/wadah/{wid}/stok/koreksi", {"jumlah_baru": 0, "alasan": "uji"})
    r = hapus(client, pemilik, f"/wadah/{wid}")
    assert r.status_code == 409 and "riwayat pengeluaran" in r.json()["detail"]


# ---------- alat ----------

def test_hapus_alat_dengan_perintah_ditolak(client, pemilik, setup):
    _, k = setup
    jalankan_perintah(client, pemilik, k, simpan_formulasi_otomatis(client, pemilik, k))
    nolkan_stok(client, pemilik, k)
    r = hapus(client, pemilik, f"/alat/{k.alat_id}")
    assert r.status_code == 409 and "perintah" in r.json()["detail"]


def test_hapus_alat_dengan_stok_ditolak_lalu_boleh(client, pemilik, setup):
    _, k = setup
    r = hapus(client, pemilik, f"/alat/{k.alat_id}")
    assert r.status_code == 409 and "Stok belum 0" in r.json()["detail"]

    nolkan_stok(client, pemilik, k)
    assert hapus(client, pemilik, f"/alat/{k.alat_id}").status_code == 204
    assert hitung(Alat) == 0 and hitung(Wadah) == 0 and hitung(Stok) == 0 and hitung(TransaksiStok) == 0
    assert get(client, pemilik, f"/kandang/{k.id}/stok") == []
    assert get(client, pemilik, f"/kandang/{k.id}")["status_alat"] is None
    assert len(audit("HAPUS_ALAT")) == 1
    # alat baru bisa didaftarkan lagi
    post(client, pemilik, f"/kandang/{k.id}/alat")


# ---------- kandang ----------

def test_hapus_kandang_dengan_siklus_ditolak(client, pemilik, setup):
    _, k = setup
    nolkan_stok(client, pemilik, k)
    r = hapus(client, pemilik, f"/kandang/{k.id}")
    assert r.status_code == 409 and "siklus" in r.json()["detail"]


def test_hapus_kandang_bersih_beserta_alat_wadah_dan_penugasan(client, pemilik, setup):
    d, _ = setup
    kid = post(client, pemilik, "/kandang", {"nama": "Salah input"})["id"]
    alat = post(client, pemilik, f"/kandang/{kid}/alat")["id"]
    post(client, pemilik, f"/alat/{alat}/wadah", {"nomor_wadah": 1, "bahan_pakan_id": d.jagung})
    post(client, pemilik, "/users", {"nama": "Budi", "email": "budi@example.com", "kata_sandi": "budi12345", "role": "PEKERJA"})
    budi = get(client, pemilik, "/users")[0]["id"]
    post(client, pemilik, f"/users/{budi}/penugasan", {"kandang_id": kid, "tanggal_mulai": "2026-11-01"})

    assert hapus(client, pemilik, f"/kandang/{kid}").status_code == 204
    kid_uuid = uuid.UUID(kid)
    assert hitung(Kandang, Kandang.id == kid_uuid) == 0
    assert hitung(PenugasanKandang, PenugasanKandang.kandang_id == kid_uuid) == 0
    assert hitung(Alat, Alat.kandang_id == kid_uuid) == 0
    assert client.get(f"{API}/kandang/{kid}", headers=pemilik).status_code == 404
    assert len(audit("HAPUS_KANDANG")) == 1


def test_hapus_kandang_dengan_riwayat_perintah_tanpa_siklus_ditolak(client, pemilik, setup):
    _, k = setup
    heartbeat(client, k)
    post(client, pemilik, f"/kandang/{k.id}/perintah/stop-darurat")  # perintah tanpa formulasi/siklus
    post(client, pemilik, f"/siklus/{k.siklus_id}/selesai")
    assert hapus(client, pemilik, f"/siklus/{k.siklus_id}").status_code == 204
    nolkan_stok(client, pemilik, k)
    r = hapus(client, pemilik, f"/kandang/{k.id}")
    assert r.status_code == 409 and "perintah" in r.json()["detail"]


def test_hapus_kandang_dengan_stok_ditolak(client, pemilik):
    d = buat_master(client, pemilik)
    kid = post(client, pemilik, "/kandang", {"nama": "K"})["id"]
    alat = post(client, pemilik, f"/kandang/{kid}/alat")["id"]
    wid = post(client, pemilik, f"/alat/{alat}/wadah", {"nomor_wadah": 1, "bahan_pakan_id": d.jagung})["id"]
    post(client, pemilik, f"/wadah/{wid}/stok/isi-ulang", {"jumlah": 100})
    assert hapus(client, pemilik, f"/kandang/{kid}").status_code == 409


# ---------- otorisasi ----------

@pytest.mark.parametrize("path", ["siklus", "formulasi", "wadah", "alat", "kandang"])
def test_pekerja_dan_pemilik_lain_tidak_bisa_menghapus(client, pemilik, pemilik_lain, setup, path):
    d, k = setup
    f = simpan_formulasi_otomatis(client, pemilik, k)
    target = {"siklus": k.siklus_id, "formulasi": f, "wadah": k.wadah["jagung"], "alat": k.alat_id, "kandang": k.id}[path]
    hp = pekerja_login(client, pemilik, k)
    assert hapus(client, hp, f"/{path}/{target}").status_code == 403
    assert hapus(client, pemilik_lain, f"/{path}/{target}").status_code in (403, 404)
    assert hapus(client, pemilik, f"/{path}/{uuid.uuid4()}").status_code == 404
