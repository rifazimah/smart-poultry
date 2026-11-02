"""5B: endpoint baca yang dibutuhkan UI (A1-A5): kebutuhan fase, standar konsumsi, kandungan bahan, populasi, penugasan."""
import pytest

from tests.conftest import login
from tests.helpers import API, buat_kandang, buat_master, get, post

TGL = "2026-11-01"


@pytest.fixture
def setup(client, pemilik):
    d = buat_master(client, pemilik)
    k = buat_kandang(client, pemilik, d)
    return d, k


def buat_pekerja(client, h, email="budi@example.com", nama="Budi"):
    post(client, h, "/users", {"nama": nama, "email": email, "kata_sandi": "budi12345", "role": "PEKERJA"})
    return next(u["id"] for u in get(client, h, "/users") if u["email"] == email)


def header_total(client, h, path):
    r = client.get(API + path, headers=h)
    assert r.status_code == 200, r.text
    return r.json(), int(r.headers["X-Total-Count"])


# ---------- A1: kebutuhan nutrisi fase ----------

def test_kebutuhan_nutrisi_fase_memuat_nama_dan_satuan(client, pemilik, setup):
    d, _ = setup
    data = get(client, pemilik, f"/fase/{d.fase_starter}/kebutuhan-nutrisi")
    assert {x["nama_nutrisi"] for x in data} == {"Protein", "Energi Metabolis", "Kalsium"}
    protein = next(x for x in data if x["nama_nutrisi"] == "Protein")
    assert (protein["batas_min"], protein["batas_max"], protein["satuan"]) == (20, 23, "%")
    assert protein["nutrisi_id"] == d.protein and protein["fase_id"] == d.fase_starter
    energi = next(x for x in data if x["nama_nutrisi"] == "Energi Metabolis")
    assert energi["batas_max"] is None and energi["satuan"] == "kkal/kg"


def test_kebutuhan_nutrisi_fase_kosong_dan_terisolasi(client, pemilik, pemilik_lain, setup):
    d, _ = setup
    fid = post(client, pemilik, f"/jenis-ayam/{d.jenis_ayam}/fase", {"nama": "Kosong", "umur_min_hari": 50, "umur_max_hari": 60})["id"]
    assert get(client, pemilik, f"/fase/{fid}/kebutuhan-nutrisi") == []
    assert client.get(f"{API}/fase/{d.fase_starter}/kebutuhan-nutrisi", headers=pemilik_lain).status_code == 404
    assert client.get(f"{API}/fase/00000000-0000-0000-0000-000000000001/kebutuhan-nutrisi", headers=pemilik).status_code == 404


# ---------- A2: standar konsumsi ----------

def test_standar_konsumsi_fase(client, pemilik, setup):
    d, _ = setup
    s = get(client, pemilik, f"/fase/{d.fase_starter}/standar-konsumsi")
    assert (s["gram_per_ekor_per_hari"], s["frekuensi_makan"], s["durasi_aduk"], s["volume_air"]) == (50, 4, 30, 200)
    assert s["fase_id"] == d.fase_starter


def test_standar_konsumsi_null_bila_belum_diatur_dan_terisolasi(client, pemilik, pemilik_lain, setup):
    d, _ = setup
    fid = post(client, pemilik, f"/jenis-ayam/{d.jenis_ayam}/fase", {"nama": "Tanpa standar", "umur_min_hari": 50, "umur_max_hari": 60})["id"]
    r = client.get(f"{API}/fase/{fid}/standar-konsumsi", headers=pemilik)
    assert r.status_code == 200 and r.json() is None
    assert client.get(f"{API}/fase/{d.fase_starter}/standar-konsumsi", headers=pemilik_lain).status_code == 404


# ---------- A3: kandungan nutrisi bahan ----------

def test_kandungan_nutrisi_bahan(client, pemilik, setup):
    d, _ = setup
    data = get(client, pemilik, f"/bahan-pakan/{d.jagung}/nutrisi")
    nilai = {x["nama_nutrisi"]: (x["nilai_per_kg"], x["satuan"]) for x in data}
    assert nilai == {"Protein": (8.5, "%"), "Energi Metabolis": (3350, "kkal/kg"), "Kalsium": (0.02, "%")}
    assert all(x["bahan_pakan_id"] == d.jagung for x in data)


def test_kandungan_nutrisi_bahan_kosong_dan_terisolasi(client, pemilik, pemilik_lain, setup):
    d, _ = setup
    bid = post(client, pemilik, "/bahan-pakan", {"nama": "Polos", "harga": 1})["id"]
    assert get(client, pemilik, f"/bahan-pakan/{bid}/nutrisi") == []
    assert client.get(f"{API}/bahan-pakan/{d.jagung}/nutrisi", headers=pemilik_lain).status_code == 404


def test_endpoint_master_data_baca_hanya_pemilik(client, pemilik, setup):
    d, k = setup
    budi = buat_pekerja(client, pemilik)
    post(client, pemilik, f"/users/{budi}/penugasan", {"kandang_id": k.id, "tanggal_mulai": TGL})
    hp = login(client, "budi@example.com", "budi12345")
    for path in (f"/fase/{d.fase_starter}/kebutuhan-nutrisi", f"/fase/{d.fase_starter}/standar-konsumsi",
                 f"/bahan-pakan/{d.jagung}/nutrisi"):
        assert client.get(API + path, headers=hp).status_code == 403, path


# ---------- A4: daftar populasi ----------

def catat(client, h, siklus_id, jenis, jumlah, tanggal, catatan=None):
    body = {"jenis": jenis, "jumlah": jumlah, "tanggal": tanggal}
    if catatan:
        body["catatan"] = catatan
    return post(client, h, f"/siklus/{siklus_id}/populasi", body)


def test_daftar_populasi_terbaru_dulu_dengan_total(client, pemilik, setup):
    _, k = setup
    catat(client, pemilik, k.siklus_id, "MORTALITAS", 1, "2026-11-02", "pagi")
    catat(client, pemilik, k.siklus_id, "MORTALITAS", 2, "2026-11-04")
    catat(client, pemilik, k.siklus_id, "PENAMBAHAN", 5, "2026-11-03")
    data, total = header_total(client, pemilik, f"/siklus/{k.siklus_id}/populasi")
    assert total == 3
    assert [x["tanggal"] for x in data] == ["2026-11-04", "2026-11-03", "2026-11-02"]
    assert data[2]["catatan"] == "pagi" and data[1]["jenis"] == "PENAMBAHAN"
    halaman, total = header_total(client, pemilik, f"/siklus/{k.siklus_id}/populasi?limit=2&skip=2")
    assert len(halaman) == 1 and total == 3


def test_daftar_populasi_kosong(client, pemilik, setup):
    _, k = setup
    data, total = header_total(client, pemilik, f"/siklus/{k.siklus_id}/populasi")
    assert data == [] and total == 0


def test_id_dari_daftar_populasi_dapat_dihapus(client, pemilik, setup):
    _, k = setup
    catat(client, pemilik, k.siklus_id, "MORTALITAS", 3, "2026-11-02")
    item = get(client, pemilik, f"/siklus/{k.siklus_id}/populasi")[0]
    assert client.delete(f"{API}/siklus/{k.siklus_id}/populasi/{item['id']}", headers=pemilik).status_code == 204
    assert get(client, pemilik, f"/siklus/{k.siklus_id}/populasi") == []


def test_akses_daftar_populasi(client, pemilik, pemilik_lain, setup):
    _, k = setup
    assert client.get(f"{API}/siklus/{k.siklus_id}/populasi", headers=pemilik_lain).status_code in (403, 404)
    buat_pekerja(client, pemilik)
    hp = login(client, "budi@example.com", "budi12345")
    assert client.get(f"{API}/siklus/{k.siklus_id}/populasi", headers=hp).status_code == 403  # belum ditugaskan
    budi = get(client, pemilik, "/users")[0]["id"]
    post(client, pemilik, f"/users/{budi}/penugasan", {"kandang_id": k.id, "tanggal_mulai": TGL})
    assert client.get(f"{API}/siklus/{k.siklus_id}/populasi", headers=hp).status_code == 200  # Pekerja ditugaskan boleh membaca


# ---------- A5: daftar penugasan ----------

def test_penugasan_per_kandang_memuat_nama_pekerja(client, pemilik, setup):
    _, k = setup
    budi = buat_pekerja(client, pemilik)
    cici = buat_pekerja(client, pemilik, "cici@example.com", "Cici")
    p1 = post(client, pemilik, f"/users/{budi}/penugasan", {"kandang_id": k.id, "tanggal_mulai": "2026-10-01"})["id"]
    post(client, pemilik, f"/users/{cici}/penugasan", {"kandang_id": k.id, "tanggal_mulai": "2026-11-01"})
    data, total = header_total(client, pemilik, f"/kandang/{k.id}/penugasan")
    assert total == 2
    assert [x["nama_pekerja"] for x in data] == ["Cici", "Budi"]  # tanggal mulai terbaru dulu
    budi_row = next(x for x in data if x["id"] == p1)
    assert budi_row["email_pekerja"] == "budi@example.com" and budi_row["nama_kandang"] == "Kandang A"
    assert budi_row["status"] == "AKTIF" and budi_row["user_id"] == budi and budi_row["kandang_id"] == k.id


def test_penugasan_filter_status(client, pemilik, setup):
    _, k = setup
    budi = buat_pekerja(client, pemilik)
    pid = post(client, pemilik, f"/users/{budi}/penugasan", {"kandang_id": k.id, "tanggal_mulai": TGL})["id"]
    client.delete(f"{API}/penugasan/{pid}", headers=pemilik)
    assert header_total(client, pemilik, f"/kandang/{k.id}/penugasan")[1] == 1
    data, total = header_total(client, pemilik, f"/kandang/{k.id}/penugasan?status=AKTIF")
    assert data == [] and total == 0
    data, total = header_total(client, pemilik, f"/kandang/{k.id}/penugasan?status=BERAKHIR")
    assert len(data) == 1 and data[0]["status"] == "BERAKHIR"
    assert client.get(f"{API}/kandang/{k.id}/penugasan?status=NGAWUR", headers=pemilik).status_code == 422


def test_penugasan_per_pekerja_memuat_nama_kandang(client, pemilik, setup):
    d, k = setup
    k2 = post(client, pemilik, "/kandang", {"nama": "Kandang B"})["id"]
    budi = buat_pekerja(client, pemilik)
    post(client, pemilik, f"/users/{budi}/penugasan", {"kandang_id": k.id, "tanggal_mulai": "2026-10-01"})
    post(client, pemilik, f"/users/{budi}/penugasan", {"kandang_id": k2, "tanggal_mulai": "2026-11-01"})
    data, total = header_total(client, pemilik, f"/users/{budi}/penugasan")
    assert total == 2 and [x["nama_kandang"] for x in data] == ["Kandang B", "Kandang A"]
    assert all(x["nama_pekerja"] == "Budi" for x in data)


def test_penugasan_kosong(client, pemilik, setup):
    _, k = setup
    budi = buat_pekerja(client, pemilik)
    assert header_total(client, pemilik, f"/kandang/{k.id}/penugasan")[0] == []
    assert header_total(client, pemilik, f"/users/{budi}/penugasan")[0] == []


def test_akses_daftar_penugasan(client, pemilik, pemilik_lain, setup):
    _, k = setup
    budi = buat_pekerja(client, pemilik)
    post(client, pemilik, f"/users/{budi}/penugasan", {"kandang_id": k.id, "tanggal_mulai": TGL})
    # Pemilik lain tidak melihat kandang/pekerja Pemilik ini
    assert client.get(f"{API}/kandang/{k.id}/penugasan", headers=pemilik_lain).status_code in (403, 404)
    assert client.get(f"{API}/users/{budi}/penugasan", headers=pemilik_lain).status_code == 404
    # Pekerja tidak boleh melihat penugasan
    hp = login(client, "budi@example.com", "budi12345")
    assert client.get(f"{API}/kandang/{k.id}/penugasan", headers=hp).status_code == 403
    assert client.get(f"{API}/users/{budi}/penugasan", headers=hp).status_code == 403
