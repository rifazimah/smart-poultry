"""T-4: POST /formulasi tidak mempercayai angka dari klien; semua dihitung ulang di server."""
import copy

import pytest

from tests.helpers import API, buat_kandang, buat_master, formulasi_manual_valid, get, post


@pytest.fixture
def setup(client, pemilik):
    d = buat_master(client, pemilik)
    k = buat_kandang(client, pemilik, d)
    return d, k


def simpan(client, h, preview):
    return client.post(f"{API}/formulasi", json=preview, headers=h)


def test_angka_palsu_diabaikan_pada_mode_otomatis(client, pemilik, setup):
    _, k = setup
    asli = post(client, pemilik, f"/siklus/{k.siklus_id}/formulasi/otomatis")
    palsu = copy.deepcopy(asli)
    palsu["total_biaya_per_kg"] = 1.0
    for i in palsu["item"]:
        i["berat_per_sesi"] = 99999
    for n in palsu["nutrisi_hasil"]:
        n["nilai_hasil"] = 123456.0
        n["status"] = "SESUAI"

    r = simpan(client, pemilik, palsu)
    assert r.status_code == 201, r.text
    assert r.json()["total_biaya_per_kg"] == pytest.approx(asli["total_biaya_per_kg"], rel=1e-6)

    lengkap = get(client, pemilik, f"/formulasi/{r.json()['id']}")
    assert sum(i["berat_per_sesi"] for i in lengkap["item"]) == pytest.approx(1250, abs=0.5)
    asli_nutrisi = {n["nutrisi_id"]: n["nilai_hasil"] for n in asli["nutrisi_hasil"]}
    for n in lengkap["nutrisi_hasil"]:
        assert n["nilai_hasil"] == pytest.approx(asli_nutrisi[n["nutrisi_id"]], rel=1e-6)


def test_status_valid_palsu_pada_komposisi_yang_tidak_memenuhi_nutrisi(client, pemilik, setup):
    d, k = setup
    buruk = {"item": [
        {"bahan_pakan_id": d.jagung, "proporsi": 0.5},
        {"bahan_pakan_id": d.kedelai, "proporsi": 0.2},
        {"bahan_pakan_id": d.dedak, "proporsi": 0.28},
        {"bahan_pakan_id": d.kapur, "proporsi": 0.02},
    ]}
    preview = post(client, pemilik, f"/siklus/{k.siklus_id}/formulasi/manual", buruk)
    assert preview["status"] == "TIDAK_SEMPURNA"
    preview["status"] = "VALID"
    for n in preview["nutrisi_hasil"]:
        n["status"] = "SESUAI"

    r = simpan(client, pemilik, preview)
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "TIDAK_SEMPURNA"
    assert r.json()["aktif"] is False
    lengkap = get(client, pemilik, f"/formulasi/{r.json()['id']}")
    assert any(n["status"] == "KURANG" for n in lengkap["nutrisi_hasil"])


def test_mode_otomatis_dengan_komposisi_lain_ditolak(client, pemilik, setup):
    d, k = setup
    preview = post(client, pemilik, f"/siklus/{k.siklus_id}/formulasi/manual", formulasi_manual_valid(d))
    preview["mode"] = "OTOMATIS"  # komposisi manual bukan optimum LP
    r = simpan(client, pemilik, preview)
    assert r.status_code == 409, r.text


def test_mode_otomatis_melebihi_batas_maksimum_bahan_ditolak(client, pemilik, setup):
    d, k = setup
    preview = post(client, pemilik, f"/siklus/{k.siklus_id}/formulasi/otomatis")
    # kapur dibatasi 0.05; geser 0.1 dari jagung ke kapur
    for i in preview["item"]:
        if i["bahan_pakan_id"] == d.kapur:
            i["proporsi"] += 0.1
        elif i["bahan_pakan_id"] == d.jagung:
            i["proporsi"] -= 0.1
    r = simpan(client, pemilik, preview)
    assert r.status_code == 409, r.text


def test_proporsi_tidak_berjumlah_satu_ditolak(client, pemilik, setup):
    _, k = setup
    preview = post(client, pemilik, f"/siklus/{k.siklus_id}/formulasi/otomatis")
    preview["item"][0]["proporsi"] += 0.2
    assert simpan(client, pemilik, preview).status_code == 400


def test_item_kosong_ditolak(client, pemilik, setup):
    _, k = setup
    preview = post(client, pemilik, f"/siklus/{k.siklus_id}/formulasi/otomatis")
    preview["item"] = []
    assert simpan(client, pemilik, preview).status_code == 400


def test_bahan_di_luar_wadah_ditolak(client, pemilik, setup):
    d, k = setup
    asing = post(client, pemilik, "/bahan-pakan", {"nama": "Asing", "harga": 1})["id"]
    preview = post(client, pemilik, f"/siklus/{k.siklus_id}/formulasi/otomatis")
    preview["item"][0]["bahan_pakan_id"] = asing
    assert simpan(client, pemilik, preview).status_code == 409


def test_siklus_selesai_ditolak(client, pemilik, setup):
    _, k = setup
    preview = post(client, pemilik, f"/siklus/{k.siklus_id}/formulasi/otomatis")
    post(client, pemilik, f"/siklus/{k.siklus_id}/selesai")
    assert simpan(client, pemilik, preview).status_code == 409


def test_siklus_milik_pemilik_lain_ditolak(client, pemilik, pemilik_lain, setup):
    _, k = setup
    preview = post(client, pemilik, f"/siklus/{k.siklus_id}/formulasi/otomatis")
    r = simpan(client, pemilik_lain, preview)
    assert r.status_code in (403, 404)


def test_alur_normal_tetap_berjalan(client, pemilik, setup):
    d, k = setup
    for body in [None, formulasi_manual_valid(d)]:
        if body is None:
            preview = post(client, pemilik, f"/siklus/{k.siklus_id}/formulasi/otomatis")
        else:
            preview = post(client, pemilik, f"/siklus/{k.siklus_id}/formulasi/manual", body)
        r = simpan(client, pemilik, preview)
        assert r.status_code == 201, r.text
        assert r.json()["status"] == "VALID" and r.json()["aktif"] is True
