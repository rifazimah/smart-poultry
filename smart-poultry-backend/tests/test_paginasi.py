"""Paginasi ?skip&limit (default 20, maks 100) dan header X-Total-Count pada endpoint list."""
import pytest

from tests.conftest import login
from tests.helpers import API, buat_kandang, buat_master, get, post, simpan_formulasi_otomatis


def daftar(client, h, path):
    r = client.get(API + path, headers=h)
    assert r.status_code == 200, r.text
    return r.json(), int(r.headers["X-Total-Count"])


@pytest.fixture
def bahan25(client, pemilik):
    for i in range(25):
        post(client, pemilik, "/bahan-pakan", {"nama": f"Bahan {i:02d}", "harga": 100})


def test_default_limit_20_dengan_total(client, pemilik, bahan25):
    data, total = daftar(client, pemilik, "/bahan-pakan")
    assert len(data) == 20 and total == 25


def test_skip_dan_limit(client, pemilik, bahan25):
    halaman2, total = daftar(client, pemilik, "/bahan-pakan?skip=20")
    assert len(halaman2) == 5 and total == 25
    kecil, _ = daftar(client, pemilik, "/bahan-pakan?limit=5")
    assert len(kecil) == 5
    besar, _ = daftar(client, pemilik, "/bahan-pakan?limit=100")
    assert len(besar) == 25
    kosong, total = daftar(client, pemilik, "/bahan-pakan?skip=100")
    assert kosong == [] and total == 25


def test_halaman_berurutan_tanpa_tumpang_tindih(client, pemilik, bahan25):
    semua = []
    for skip in (0, 10, 20):
        data, _ = daftar(client, pemilik, f"/bahan-pakan?skip={skip}&limit=10")
        semua += [b["nama"] for b in data]
    assert semua == [f"Bahan {i:02d}" for i in range(25)]  # urut nama, tidak ada duplikat/hilang


@pytest.mark.parametrize("query", ["limit=101", "limit=0", "limit=-1", "skip=-1", "limit=abc"])
def test_parameter_tidak_valid_422(client, pemilik, query):
    assert client.get(f"{API}/bahan-pakan?{query}", headers=pemilik).status_code == 422


def test_semua_endpoint_list_mendukung_paginasi(client, pemilik):
    d = buat_master(client, pemilik)
    k = buat_kandang(client, pemilik, d)
    simpan_formulasi_otomatis(client, pemilik, k)
    post(client, pemilik, "/users", {"nama": "Budi", "email": "budi@example.com", "kata_sandi": "budi12345", "role": "PEKERJA"})
    post(client, pemilik, f"/wadah/{k.wadah['jagung']}/stok/isi-ulang", {"jumlah": 1})
    post(client, pemilik, f"/kandang/{k.id}/perintah/stop-darurat")  # alat belum online; stop darurat tetap boleh

    jalur = [
        "/jenis-ayam", f"/jenis-ayam/{d.jenis_ayam}/fase", "/nutrisi", "/bahan-pakan", "/kandang",
        f"/siklus/{k.siklus_id}/formulasi", f"/kandang/{k.id}/perintah",
        f"/wadah/{k.wadah['jagung']}/stok/transaksi", "/users", "/notifikasi",
    ]
    for path in jalur:
        data, total = daftar(client, pemilik, path + "?limit=1")
        assert len(data) <= 1 and total >= len(data), path
        assert total >= 1, path
        assert client.get(f"{API}{path}?limit=0", headers=pemilik).status_code == 422, path


def test_notifikasi_total_mengikuti_filter(client, pemilik):
    d = buat_master(client, pemilik)
    k = buat_kandang(client, pemilik, d)
    simpan_formulasi_otomatis(client, pemilik, k)
    post(client, pemilik, f"/kandang/{k.id}/perintah/stop-darurat")
    _, semua = daftar(client, pemilik, "/notifikasi")
    assert semua >= 1
    client.patch(f"{API}/notifikasi/baca-semua", headers=pemilik)
    _, belum = daftar(client, pemilik, "/notifikasi?status=BELUM_DIBACA")
    assert belum == 0


def test_riwayat_perintah_tanpa_alat_total_nol(client, pemilik):
    kid = post(client, pemilik, "/kandang", {"nama": "Tanpa alat"})["id"]
    data, total = daftar(client, pemilik, f"/kandang/{kid}/perintah")
    assert data == [] and total == 0


def test_kandang_pekerja_dipaginasi_sesuai_penugasan(client, pemilik):
    buat_master(client, pemilik)
    ids = [post(client, pemilik, "/kandang", {"nama": f"K{i}"})["id"] for i in range(3)]
    post(client, pemilik, "/users", {"nama": "Budi", "email": "budi@example.com", "kata_sandi": "budi12345", "role": "PEKERJA"})
    budi = get(client, pemilik, "/users")[0]["id"]
    for kid in ids[:2]:
        post(client, pemilik, f"/users/{budi}/penugasan", {"kandang_id": kid, "tanggal_mulai": "2026-11-01"})
    hp = login(client, "budi@example.com", "budi12345")
    data, total = daftar(client, hp, "/kandang?limit=1")
    assert len(data) == 1 and total == 2


def test_header_total_terbuka_untuk_cors(client, pemilik):
    r = client.get(f"{API}/nutrisi", headers={**pemilik, "Origin": "http://localhost:5173"})
    assert "X-Total-Count" in r.headers["access-control-expose-headers"]
