"""GET /kandang/{id}/alat dan nama bahan/nutrisi pada GET /formulasi/{id}."""
import pytest

from tests.conftest import login
from tests.helpers import API, buat_kandang, buat_master, get, heartbeat, post, simpan_formulasi_otomatis


@pytest.fixture
def setup(client, pemilik):
    d = buat_master(client, pemilik)
    k = buat_kandang(client, pemilik, d)
    return d, k


def test_alat_kandang_lengkap_dengan_wadah_bahan_dan_stok(client, pemilik, setup):
    d, k = setup
    heartbeat(client, k)
    alat = get(client, pemilik, f"/kandang/{k.id}/alat")
    assert alat["id"] == k.alat_id and alat["kandang_id"] == k.id
    assert alat["status"] == "ONLINE" and alat["waktu_terakhir_sinkron"]
    assert "device_token" not in alat

    wadah = alat["wadah"]
    assert [w["nomor_wadah"] for w in wadah] == [1, 2, 3, 4]
    assert [w["nama_bahan"] for w in wadah] == ["Jagung", "Bungkil Kedelai", "Dedak", "Tepung Batu"]
    assert [w["jumlah_stok"] for w in wadah] == [20000, 10000, 10000, 2000]
    assert wadah[0]["id"] == k.wadah["jagung"] and wadah[0]["bahan_pakan_id"] == d.jagung


def test_alat_null_bila_kandang_belum_punya_alat(client, pemilik):
    kid = post(client, pemilik, "/kandang", {"nama": "Tanpa alat"})["id"]
    assert get(client, pemilik, f"/kandang/{kid}/alat") is None


def test_wadah_kosong_dan_stok_nol_ditampilkan(client, pemilik):
    kid = post(client, pemilik, "/kandang", {"nama": "K"})["id"]
    alat = post(client, pemilik, f"/kandang/{kid}/alat")["id"]
    post(client, pemilik, f"/alat/{alat}/wadah", {"nomor_wadah": 1})
    w = get(client, pemilik, f"/kandang/{kid}/alat")["wadah"][0]
    assert w["bahan_pakan_id"] is None and w["nama_bahan"] is None and w["jumlah_stok"] == 0


def test_status_alat_memperhitungkan_heartbeat_kedaluwarsa(client, pemilik, setup):
    _, k = setup
    assert get(client, pemilik, f"/kandang/{k.id}/alat")["status"] == "OFFLINE"  # belum pernah heartbeat


def test_akses_alat_kandang(client, pemilik, pemilik_lain, setup):
    _, k = setup
    assert client.get(f"{API}/kandang/{k.id}/alat", headers=pemilik_lain).status_code in (403, 404)

    post(client, pemilik, "/users", {"nama": "Budi", "email": "budi@example.com", "kata_sandi": "budi12345", "role": "PEKERJA"})
    hp = login(client, "budi@example.com", "budi12345")
    assert client.get(f"{API}/kandang/{k.id}/alat", headers=hp).status_code == 403  # belum ditugaskan

    budi = get(client, pemilik, "/users")[0]["id"]
    post(client, pemilik, f"/users/{budi}/penugasan", {"kandang_id": k.id, "tanggal_mulai": "2026-11-01"})
    assert client.get(f"{API}/kandang/{k.id}/alat", headers=hp).status_code == 200


def test_formulasi_lengkap_memuat_nama_bahan_dan_nutrisi(client, pemilik, setup):
    d, k = setup
    f = simpan_formulasi_otomatis(client, pemilik, k)
    lengkap = get(client, pemilik, f"/formulasi/{f}")
    assert lengkap["item"] and lengkap["nutrisi_hasil"]
    nama_bahan = {i["bahan_pakan_id"]: i["nama_bahan"] for i in lengkap["item"]}
    assert all(nama_bahan.values()) and set(nama_bahan.values()) <= {"Jagung", "Bungkil Kedelai", "Dedak", "Tepung Batu"}
    nutrisi = {h["nama_nutrisi"]: h["satuan"] for h in lengkap["nutrisi_hasil"]}
    assert nutrisi == {"Protein": "%", "Energi Metabolis": "kkal/kg", "Kalsium": "%"}
