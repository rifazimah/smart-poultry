import pytest

from tests.helpers import API, buat_kandang, buat_master, formulasi_manual_valid, post, put


@pytest.fixture
def setup(client, pemilik):
    d = buat_master(client, pemilik)
    k = buat_kandang(client, pemilik, d)
    return d, k


def test_otomatis_valid_memenuhi_nutrisi_dan_total_sesuai_standar(client, pemilik, setup):
    d, k = setup
    p = post(client, pemilik, f"/siklus/{k.siklus_id}/formulasi/otomatis")
    assert p["status"] == "VALID"
    assert p["total_biaya_per_kg"] > 0
    assert sum(i["proporsi"] for i in p["item"]) == pytest.approx(1.0, abs=1e-4)
    assert all(n["status"] == "SESUAI" for n in p["nutrisi_hasil"])
    # 50 g/ekor/hari x 100 ekor / 4 sesi
    assert sum(i["berat_per_sesi"] for i in p["item"]) == pytest.approx(1250, abs=0.5)
    kapur = next((i for i in p["item"] if i["bahan_pakan_id"] == d.kapur), None)
    assert kapur is None or kapur["proporsi"] <= 0.05 + 1e-6


def test_manual_valid(client, pemilik, setup):
    d, k = setup
    p = post(client, pemilik, f"/siklus/{k.siklus_id}/formulasi/manual", formulasi_manual_valid(d))
    assert p["status"] == "VALID"
    jagung = next(i for i in p["item"] if i["bahan_pakan_id"] == d.jagung)
    assert jagung["berat_per_sesi"] == pytest.approx(800, abs=0.5)


def test_manual_protein_kurang(client, pemilik, setup):
    d, k = setup
    body = {"item": [
        {"bahan_pakan_id": d.jagung, "proporsi": 0.5},
        {"bahan_pakan_id": d.kedelai, "proporsi": 0.2},
        {"bahan_pakan_id": d.dedak, "proporsi": 0.28},
        {"bahan_pakan_id": d.kapur, "proporsi": 0.02},
    ]}
    p = post(client, pemilik, f"/siklus/{k.siklus_id}/formulasi/manual", body)
    assert p["status"] == "TIDAK_SEMPURNA"
    protein = next(n for n in p["nutrisi_hasil"] if n["nutrisi_id"] == d.protein)
    assert protein["status"] == "KURANG"
    assert "Protein" in p["pesan"]


def test_manual_total_proporsi_salah(client, pemilik, setup):
    d, k = setup
    r = client.post(f"{API}/siklus/{k.siklus_id}/formulasi/manual",
                    json={"item": [{"bahan_pakan_id": d.jagung, "proporsi": 0.5}]}, headers=pemilik)
    assert r.status_code == 400


def test_infeasible_tetap_200_tidak_sempurna(client, pemilik, setup):
    d, k = setup
    put(client, pemilik, f"/fase/{d.fase_starter}/kebutuhan-nutrisi",
        [{"nutrisi_id": d.protein, "batas_min": 60}])
    p = post(client, pemilik, f"/siklus/{k.siklus_id}/formulasi/otomatis")
    assert p["status"] == "TIDAK_SEMPURNA"
    assert p["item"] == []


def test_harga_kosong_409(client, pemilik, setup):
    d, k = setup
    r = client.patch(f"{API}/bahan-pakan/{d.dedak}", json={"harga": None}, headers=pemilik)
    assert r.status_code == 200
    r = client.post(f"{API}/siklus/{k.siklus_id}/formulasi/otomatis", json={}, headers=pemilik)
    assert r.status_code == 409
    assert "Dedak" in r.json()["detail"]
