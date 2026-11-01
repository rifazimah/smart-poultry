"""Isolasi data antar-Pemilik dan batasan peran Pekerja (T-1, T-2, T-3, T-12, D-3)."""
import pytest

from tests.conftest import login
from tests.helpers import API, buat_kandang, buat_master, get, post, simpan_formulasi_otomatis

TGL = "2026-11-01"


def buat_pekerja(client, h, email):
    r = post(client, h, "/users", {"nama": "Pekerja", "email": email, "kata_sandi": "pekerja123", "role": "PEKERJA"})
    return r["id"]


@pytest.fixture
def dunia(client, pemilik, pemilik_lain):
    """Pemilik A: master + kandang + pekerja. Pemilik B: kosong."""
    d = buat_master(client, pemilik)
    k = buat_kandang(client, pemilik, d)
    pekerja_id = buat_pekerja(client, pemilik, "pekerja.a@example.com")
    return d, k, pekerja_id


def test_daftar_pekerja_hanya_milik_sendiri(client, pemilik, pemilik_lain, dunia):
    _, _, pekerja_id = dunia
    assert [u["id"] for u in get(client, pemilik, "/users")] == [pekerja_id]
    assert get(client, pemilik_lain, "/users") == []


def test_ubah_status_pekerja_milik_lain_404(client, pemilik_lain, dunia):
    _, _, pekerja_id = dunia
    r = client.patch(f"{API}/users/{pekerja_id}/status", json={"status": "NONAKTIF"}, headers=pemilik_lain)
    assert r.status_code == 404


def test_penugasan_ke_kandang_milik_lain_ditolak(client, pemilik_lain, dunia):
    _, k, _ = dunia
    pekerja_b = buat_pekerja(client, pemilik_lain, "pekerja.b@example.com")
    r = client.post(f"{API}/users/{pekerja_b}/penugasan",
                    json={"kandang_id": k.id, "tanggal_mulai": TGL}, headers=pemilik_lain)
    assert r.status_code in (403, 404)


def test_penugasan_pekerja_milik_lain_404(client, pemilik, pemilik_lain, dunia):
    _, _, pekerja_a = dunia
    kandang_b = post(client, pemilik_lain, "/kandang", {"nama": "Kandang B"})["id"]
    r = client.post(f"{API}/users/{pekerja_a}/penugasan",
                    json={"kandang_id": kandang_b, "tanggal_mulai": TGL}, headers=pemilik_lain)
    assert r.status_code == 404


def test_penugasan_ganda_409(client, pemilik, dunia):
    _, k, pekerja_id = dunia
    body = {"kandang_id": k.id, "tanggal_mulai": TGL}
    post(client, pemilik, f"/users/{pekerja_id}/penugasan", body)
    r = client.post(f"{API}/users/{pekerja_id}/penugasan", json=body, headers=pemilik)
    assert r.status_code == 409


def test_akhiri_penugasan_milik_lain_ditolak(client, pemilik, pemilik_lain, dunia):
    _, k, pekerja_id = dunia
    pid = post(client, pemilik, f"/users/{pekerja_id}/penugasan", {"kandang_id": k.id, "tanggal_mulai": TGL})["id"]
    r = client.delete(f"{API}/penugasan/{pid}", headers=pemilik_lain)
    assert r.status_code in (403, 404)
    # pemilik sebenarnya boleh
    r = client.delete(f"{API}/penugasan/{pid}", headers=pemilik)
    assert r.status_code == 204


def test_wadah_dengan_bahan_milik_lain_404(client, pemilik, pemilik_lain, dunia):
    d, _, _ = dunia
    kandang_b = post(client, pemilik_lain, "/kandang", {"nama": "Kandang B"})["id"]
    alat_b = post(client, pemilik_lain, f"/kandang/{kandang_b}/alat")["id"]
    r = client.post(f"{API}/alat/{alat_b}/wadah",
                    json={"nomor_wadah": 1, "bahan_pakan_id": d.jagung}, headers=pemilik_lain)
    assert r.status_code == 404

    wadah_b = post(client, pemilik_lain, f"/alat/{alat_b}/wadah", {"nomor_wadah": 1})["id"]
    r = client.patch(f"{API}/wadah/{wadah_b}", json={"bahan_pakan_id": d.jagung}, headers=pemilik_lain)
    assert r.status_code == 404


def test_patch_wadah_null_melepas_bahan(client, pemilik, dunia):
    _, k, _ = dunia
    wid = k.wadah["jagung"]
    r = client.patch(f"{API}/wadah/{wid}", json={"bahan_pakan_id": None}, headers=pemilik)
    assert r.status_code == 200
    assert r.json()["bahan_pakan_id"] is None


def test_pekerja_tidak_boleh_menjalankan_atau_menyimpan_formulasi(client, pemilik, dunia):
    d, k, pekerja_id = dunia
    post(client, pemilik, f"/users/{pekerja_id}/penugasan", {"kandang_id": k.id, "tanggal_mulai": TGL})
    f = simpan_formulasi_otomatis(client, pemilik, k)
    preview = post(client, pemilik, f"/siklus/{k.siklus_id}/formulasi/otomatis")
    hp = login(client, "pekerja.a@example.com", "pekerja123")

    assert client.post(f"{API}/siklus/{k.siklus_id}/formulasi/otomatis", json={}, headers=hp).status_code == 403
    assert client.post(f"{API}/formulasi", json=preview, headers=hp).status_code == 403
    # membaca tetap boleh
    assert get(client, hp, f"/formulasi/{f}")["id"] == f
    assert len(get(client, hp, f"/siklus/{k.siklus_id}/formulasi")) == 1


def test_pekerja_tanpa_penugasan_403(client, pemilik, dunia):
    _, k, _ = dunia
    hp = login(client, "pekerja.a@example.com", "pekerja123")
    assert client.get(f"{API}/kandang/{k.id}", headers=hp).status_code == 403
