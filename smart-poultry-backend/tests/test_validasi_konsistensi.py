"""
Konvensi kode error:
- 422 : bentuk/nilai body tidak valid (divalidasi skema)
- 400 : nilai request tidak valid terhadap aturan (mis. total proporsi, fase bukan milik jenis ayam)
- 409 : request sah tetapi bertentangan dengan keadaan data (siklus selesai, alat sudah ada, dst.)
"""
import pytest

from tests.helpers import API, buat_kandang, buat_master, get, post


@pytest.fixture
def setup(client, pemilik):
    d = buat_master(client, pemilik)
    k = buat_kandang(client, pemilik, d)
    return d, k


# ---------- 422: nilai body ----------

def test_jumlah_ayam_siklus_harus_positif(client, pemilik):
    d = buat_master(client, pemilik)
    kid = post(client, pemilik, "/kandang", {"nama": "K"})["id"]
    for jumlah in (0, -5):
        r = client.post(f"{API}/kandang/{kid}/siklus", headers=pemilik, json={
            "jenis_ayam_id": d.jenis_ayam, "fase_id": d.fase_starter, "jumlah_ayam": jumlah, "tanggal_mulai": "2026-11-01"})
        assert r.status_code == 422, jumlah


@pytest.mark.parametrize("jumlah", [0, -1])
def test_jumlah_populasi_harus_positif(client, pemilik, setup, jumlah):
    _, k = setup
    r = client.post(f"{API}/siklus/{k.siklus_id}/populasi", headers=pemilik,
                    json={"jenis": "MORTALITAS", "jumlah": jumlah, "tanggal": "2026-11-02"})
    assert r.status_code == 422


def test_isi_ulang_dan_koreksi_stok_validasi_nilai(client, pemilik, setup):
    _, k = setup
    wid = k.wadah["jagung"]
    assert client.post(f"{API}/wadah/{wid}/stok/isi-ulang", json={"jumlah": 0}, headers=pemilik).status_code == 422
    assert client.post(f"{API}/wadah/{wid}/stok/isi-ulang", json={"jumlah": -10}, headers=pemilik).status_code == 422
    assert client.post(f"{API}/wadah/{wid}/stok/koreksi", json={"jumlah_baru": -1, "alasan": "x"}, headers=pemilik).status_code == 422
    assert client.post(f"{API}/wadah/{wid}/stok/koreksi", json={"jumlah_baru": 0, "alasan": "dikosongkan"}, headers=pemilik).status_code == 201


# ---------- 409: keadaan data ----------

def test_kandang_nonaktif_tidak_bisa_memulai_siklus(client, pemilik):
    d = buat_master(client, pemilik)
    kid = post(client, pemilik, "/kandang", {"nama": "K"})["id"]
    assert client.patch(f"{API}/kandang/{kid}", json={"status": "NONAKTIF"}, headers=pemilik).status_code == 200
    r = client.post(f"{API}/kandang/{kid}/siklus", headers=pemilik, json={
        "jenis_ayam_id": d.jenis_ayam, "fase_id": d.fase_starter, "jumlah_ayam": 10, "tanggal_mulai": "2026-11-01"})
    assert r.status_code == 409 and "NONAKTIF" in r.json()["detail"]
    client.patch(f"{API}/kandang/{kid}", json={"status": "AKTIF"}, headers=pemilik)
    r = client.post(f"{API}/kandang/{kid}/siklus", headers=pemilik, json={
        "jenis_ayam_id": d.jenis_ayam, "fase_id": d.fase_starter, "jumlah_ayam": 10, "tanggal_mulai": "2026-11-01"})
    assert r.status_code == 201


def test_populasi_tidak_boleh_membuat_jumlah_negatif_dan_tidak_berubah(client, pemilik, setup):
    _, k = setup
    r = client.post(f"{API}/siklus/{k.siklus_id}/populasi", headers=pemilik,
                    json={"jenis": "PANEN", "jumlah": 101, "tanggal": "2026-11-02"})
    assert r.status_code == 409 and "100" in r.json()["detail"]
    assert get(client, pemilik, f"/kandang/{k.id}/siklus/aktif")["jumlah_ayam"] == 100
    # catatan yang ditolak tidak tersimpan: panen 100 sah dan menghasilkan 0
    assert client.post(f"{API}/siklus/{k.siklus_id}/populasi", headers=pemilik,
                       json={"jenis": "PANEN", "jumlah": 100, "tanggal": "2026-11-02"}).status_code == 201
    assert get(client, pemilik, f"/kandang/{k.id}/siklus/aktif")["jumlah_ayam"] == 0


def test_alat_dan_wadah_ganda_409(client, pemilik, setup):
    _, k = setup
    assert client.post(f"{API}/kandang/{k.id}/alat", json={}, headers=pemilik).status_code == 409
    assert client.post(f"{API}/alat/{k.alat_id}/wadah", json={"nomor_wadah": 1}, headers=pemilik).status_code == 409


def test_perintah_tanpa_alat_409(client, pemilik):
    kid = post(client, pemilik, "/kandang", {"nama": "Tanpa alat"})["id"]
    f = "00000000-0000-0000-0000-000000000001"
    assert client.post(f"{API}/kandang/{kid}/perintah/beri-makan", json={"formulasi_id": f}, headers=pemilik).status_code == 409
    assert client.post(f"{API}/kandang/{kid}/perintah/stop-darurat", json={}, headers=pemilik).status_code == 409


def test_formulasi_tanpa_prasyarat_409(client, pemilik):
    """Alat/bahan/kebutuhan/standar belum disiapkan = keadaan data belum siap, bukan input salah."""
    d = buat_master(client, pemilik)
    kid = post(client, pemilik, "/kandang", {"nama": "K"})["id"]
    sid = post(client, pemilik, f"/kandang/{kid}/siklus", {
        "jenis_ayam_id": d.jenis_ayam, "fase_id": d.fase_starter, "jumlah_ayam": 10, "tanggal_mulai": "2026-11-01"})["id"]
    url = f"{API}/siklus/{sid}/formulasi/otomatis"
    assert client.post(url, json={}, headers=pemilik).status_code == 409      # belum ada alat
    alat = post(client, pemilik, f"/kandang/{kid}/alat")["id"]
    assert client.post(url, json={}, headers=pemilik).status_code == 409      # alat ada, wadah/bahan belum
    post(client, pemilik, f"/alat/{alat}/wadah", {"nomor_wadah": 1, "bahan_pakan_id": d.jagung})
    fase_baru = post(client, pemilik, f"/jenis-ayam/{d.jenis_ayam}/fase", {"nama": "Kosong", "umur_min_hari": 99, "umur_max_hari": 100})["id"]
    client.patch(f"{API}/siklus/{sid}/fase", json={"fase_id": fase_baru}, headers=pemilik)
    assert client.post(url, json={}, headers=pemilik).status_code == 409      # fase tanpa kebutuhan nutrisi


def test_siklus_selesai_menolak_perubahan_dengan_409(client, pemilik, setup):
    d, k = setup
    sid = k.siklus_id
    post(client, pemilik, f"/siklus/{sid}/selesai")
    assert client.post(f"{API}/siklus/{sid}/selesai", json={}, headers=pemilik).status_code == 409
    assert client.post(f"{API}/siklus/{sid}/populasi", headers=pemilik,
                       json={"jenis": "MORTALITAS", "jumlah": 1, "tanggal": "2026-11-02"}).status_code == 409
    assert client.patch(f"{API}/siklus/{sid}/fase", json={"fase_id": d.fase_grower}, headers=pemilik).status_code == 409
    assert client.patch(f"{API}/siklus/{sid}", json={"jumlah_ayam": 5}, headers=pemilik).status_code == 409


# ---------- 400: nilai tidak valid terhadap aturan ----------

def test_nilai_request_tidak_valid_tetap_400(client, pemilik, setup):
    d, k = setup
    assert client.patch(f"{API}/siklus/{k.siklus_id}", json={}, headers=pemilik).status_code == 400  # tidak ada yang diubah
    fase_lain = post(client, pemilik, "/jenis-ayam", {"nama": "Lain"})
    fid = post(client, pemilik, f"/jenis-ayam/{fase_lain['id']}/fase", {"nama": "F", "umur_min_hari": 0, "umur_max_hari": 5})["id"]
    assert client.patch(f"{API}/siklus/{k.siklus_id}/fase", json={"fase_id": fid}, headers=pemilik).status_code == 400  # fase bukan milik jenis ayam siklus
    r = client.post(f"{API}/siklus/{k.siklus_id}/formulasi/manual", headers=pemilik,
                    json={"item": [{"bahan_pakan_id": d.jagung, "proporsi": 0.5}]})
    assert r.status_code == 400  # total proporsi bukan 1
