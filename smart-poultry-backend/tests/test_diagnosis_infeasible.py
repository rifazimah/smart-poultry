"""S-1 / BR-11: formulasi otomatis yang infeasible harus menyebut nutrisi yang tidak terpenuhi."""
import pytest

from tests.helpers import API, buat_kandang, buat_master, put


@pytest.fixture
def setup(client, pemilik):
    d = buat_master(client, pemilik)
    k = buat_kandang(client, pemilik, d)
    return d, k


def otomatis(client, h, k):
    r = client.post(f"{API}/siklus/{k.siklus_id}/formulasi/otomatis", json={}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def kebutuhan(client, h, d, protein=(20, 23), energi=2900, kalsium=(0.9, 1.2)):
    put(client, h, f"/fase/{d.fase_starter}/kebutuhan-nutrisi", [
        {"nutrisi_id": d.protein, "batas_min": protein[0], "batas_max": protein[1]},
        {"nutrisi_id": d.energi, "batas_min": energi},
        {"nutrisi_id": d.kalsium, "batas_min": kalsium[0], "batas_max": kalsium[1]},
    ])


def per_nutrisi(preview):
    return {n["nama_nutrisi"]: n for n in preview["nutrisi_hasil"]}


def test_bentuk_respons_sesuai_kontrak(client, pemilik, setup):
    d, k = setup
    kebutuhan(client, pemilik, d, protein=(60, 70))
    p = otomatis(client, pemilik, k)
    assert p["status"] == "TIDAK_SEMPURNA" and p["item"] == [] and p["total_biaya_per_kg"] is None
    assert p["pesan"] and p["nutrisi_hasil"]


def test_nutrisi_yang_tak_bisa_mencapai_minimum(client, pemilik, setup):
    d, k = setup
    kebutuhan(client, pemilik, d, protein=(60, 70))  # protein tertinggi yang mungkin = kedelai 44%
    p = otomatis(client, pemilik, k)
    protein = per_nutrisi(p)["Protein"]
    assert protein["status"] == "KURANG"
    assert protein["nilai_hasil"] == pytest.approx(44.0, abs=0.01)  # nilai terbaik yang mungkin
    assert protein["batas_min"] == 60
    assert "tidak tercapai" in protein["keterangan"] and "44" in protein["keterangan"]
    assert "Protein" in p["pesan"] and "60" in p["pesan"] and "44" in p["pesan"]
    # nutrisi lain tetap dilaporkan dan tidak disalahkan
    assert set(per_nutrisi(p)) == {"Protein", "Energi Metabolis", "Kalsium"}


def test_nutrisi_yang_tak_bisa_turun_di_bawah_maksimum(client, pemilik, setup):
    d, k = setup
    kebutuhan(client, pemilik, d, protein=(1, 5))  # protein terendah yang mungkin ~8,075 (jagung 95% + kapur 5%)
    p = otomatis(client, pemilik, k)
    protein = per_nutrisi(p)["Protein"]
    assert protein["status"] == "BERLEBIH"
    assert protein["nilai_hasil"] == pytest.approx(8.075, abs=0.01)
    assert "maks" in p["pesan"] and "Protein" in p["pesan"]


def test_batas_yang_saling_bertentangan_dilaporkan_sebagai_kompromi(client, pemilik, setup):
    """Protein min 40 (butuh kedelai >= ~72%) dan energi min 3300 (butuh jagung >= ~95%): masing-masing mungkin, bersama tidak."""
    d, k = setup
    kebutuhan(client, pemilik, d, protein=(40, 50), energi=3300)
    p = otomatis(client, pemilik, k)
    assert p["status"] == "TIDAK_SEMPURNA"
    assert "saling bertentangan" in p["pesan"]
    hasil = per_nutrisi(p)
    langgar = [n for n in hasil.values() if n["status"] != "SESUAI"]
    assert langgar, "minimal satu nutrisi harus dilaporkan melanggar pada komposisi kompromi"
    for n in langgar:
        assert n["nama_nutrisi"] in p["pesan"] and n["keterangan"]
    # tak satu pun diklaim mustahil secara individual
    assert all("tidak tercapai" not in (n["keterangan"] or "") for n in hasil.values())


def test_total_batas_maksimum_bahan_kurang_dari_100_persen(client, pemilik, setup):
    d, k = setup
    for bid in (d.jagung, d.kedelai, d.dedak, d.kapur):
        r = client.patch(f"{API}/bahan-pakan/{bid}", json={"batas_maksimum": 0.2}, headers=pemilik)
        assert r.status_code == 200
    p = otomatis(client, pemilik, k)
    assert p["status"] == "TIDAK_SEMPURNA" and p["item"] == [] and p["nutrisi_hasil"] == []
    assert "batas maksimum" in p["pesan"].lower() and "80%" in p["pesan"]


def test_formulasi_yang_feasible_tidak_berubah(client, pemilik, setup):
    _, k = setup
    p = otomatis(client, pemilik, k)
    assert p["status"] == "VALID" and p["pesan"] is None and p["item"]
    assert all(n["status"] == "SESUAI" and n["keterangan"] is None for n in p["nutrisi_hasil"])


def test_hasil_infeasible_tidak_bisa_disimpan(client, pemilik, setup):
    d, k = setup
    kebutuhan(client, pemilik, d, protein=(60, 70))
    p = otomatis(client, pemilik, k)
    r = client.post(f"{API}/formulasi", json=p, headers=pemilik)
    assert r.status_code == 400  # komposisi kosong tidak dapat disimpan


def test_pesan_menyebut_semua_nutrisi_yang_mustahil(client, pemilik, setup):
    d, k = setup
    kebutuhan(client, pemilik, d, protein=(60, 70), energi=9000)  # energi tertinggi yang mungkin 3350
    p = otomatis(client, pemilik, k)
    hasil = per_nutrisi(p)
    assert hasil["Protein"]["status"] == "KURANG" and hasil["Energi Metabolis"]["status"] == "KURANG"
    assert hasil["Energi Metabolis"]["nilai_hasil"] == pytest.approx(3350, abs=0.5)
    assert "Protein" in p["pesan"] and "Energi Metabolis" in p["pesan"]
