"""DELETE master data yang aman, DELETE perubahan populasi, dan PATCH koreksi siklus."""
import uuid

import pytest
from sqlmodel import Session, select

from app.database import engine
from app.models.akses import AuditLog
from tests.conftest import login
from tests.helpers import API, buat_kandang, buat_master, get, post, simpan_formulasi_otomatis


@pytest.fixture
def setup(client, pemilik):
    d = buat_master(client, pemilik)
    k = buat_kandang(client, pemilik, d)
    return d, k


def hapus(client, h, path):
    return client.delete(API + path, headers=h)


def aksi_audit(aksi):
    with Session(engine) as s:
        return s.exec(select(AuditLog).where(AuditLog.aksi == aksi)).all()


# ---------- master data ----------

def test_bahan_di_wadah_ditolak_dan_wadah_tetap_utuh(client, pemilik, setup):
    d, k = setup
    r = hapus(client, pemilik, f"/bahan-pakan/{d.jagung}")
    assert r.status_code == 409
    assert "wadah" in r.json()["detail"]
    nama = {s["nama_bahan"] for s in get(client, pemilik, f"/kandang/{k.id}/stok")}
    assert "Jagung" in nama


def test_bahan_dipakai_formulasi_ditolak(client, pemilik, setup):
    d, k = setup
    simpan_formulasi_otomatis(client, pemilik, k)
    # lepas dari wadah supaya hanya referensi formulasi yang tersisa
    client.patch(f"{API}/wadah/{k.wadah['jagung']}", json={"bahan_pakan_id": None}, headers=pemilik)
    r = hapus(client, pemilik, f"/bahan-pakan/{d.jagung}")
    assert r.status_code == 409 and "item formulasi" in r.json()["detail"]


def test_bahan_bebas_boleh_dihapus_beserta_kandungannya(client, pemilik, setup):
    bid = post(client, pemilik, "/bahan-pakan", {"nama": "Salah input", "harga": 1})["id"]
    assert hapus(client, pemilik, f"/bahan-pakan/{bid}").status_code == 204
    assert client.get(f"{API}/bahan-pakan/{bid}", headers=pemilik).status_code == 404
    assert len(aksi_audit("HAPUS_BAHAN_PAKAN")) == 1


def test_nutrisi_dipakai_ditolak_lalu_boleh_setelah_dilepas(client, pemilik):
    d = buat_master(client, pemilik)
    r = hapus(client, pemilik, f"/nutrisi/{d.kalsium}")
    assert r.status_code == 409
    assert "kandungan bahan pakan" in r.json()["detail"] and "kebutuhan fase" in r.json()["detail"]

    nid = post(client, pemilik, "/nutrisi", {"nama": "Salah", "satuan": "%", "tipe_batas": "MINIMUM"})["id"]
    assert hapus(client, pemilik, f"/nutrisi/{nid}").status_code == 204


def test_fase_dan_jenis_ayam_dipakai_siklus_ditolak(client, pemilik, setup):
    d, _ = setup
    r = hapus(client, pemilik, f"/fase/{d.fase_starter}")
    assert r.status_code == 409 and "siklus" in r.json()["detail"]
    r = hapus(client, pemilik, f"/jenis-ayam/{d.jenis_ayam}")
    assert r.status_code == 409 and "siklus" in r.json()["detail"]


def test_fase_dan_jenis_ayam_bebas_boleh_dihapus(client, pemilik):
    jid = post(client, pemilik, "/jenis-ayam", {"nama": "Salah"})["id"]
    fid = post(client, pemilik, f"/jenis-ayam/{jid}/fase", {"nama": "F", "umur_min_hari": 0, "umur_max_hari": 7})["id"]
    assert hapus(client, pemilik, f"/fase/{fid}").status_code == 204
    assert hapus(client, pemilik, f"/jenis-ayam/{jid}").status_code == 204
    assert {a.aksi for a in aksi_audit("HAPUS_FASE") + aksi_audit("HAPUS_JENIS_AYAM")} == {"HAPUS_FASE", "HAPUS_JENIS_AYAM"}


def test_hapus_master_data_milik_pemilik_lain_404(client, pemilik, pemilik_lain):
    bid = post(client, pemilik, "/bahan-pakan", {"nama": "Milik A", "harga": 1})["id"]
    assert hapus(client, pemilik_lain, f"/bahan-pakan/{bid}").status_code == 404


# ---------- populasi ----------

def catat(client, h, siklus_id, jenis, jumlah):
    return post(client, h, f"/siklus/{siklus_id}/populasi", {"jenis": jenis, "jumlah": jumlah, "tanggal": "2026-11-02"})


def jumlah_ayam(client, h, k):
    return get(client, h, f"/kandang/{k.id}/siklus/aktif")["jumlah_ayam"]


def test_hapus_mortalitas_mengembalikan_populasi(client, pemilik, setup):
    _, k = setup
    p = catat(client, pemilik, k.siklus_id, "MORTALITAS", 5)
    assert jumlah_ayam(client, pemilik, k) == 95
    assert hapus(client, pemilik, f"/siklus/{k.siklus_id}/populasi/{p['id']}").status_code == 204
    assert jumlah_ayam(client, pemilik, k) == 100
    assert len(aksi_audit("HAPUS_PERUBAHAN_POPULASI")) == 1


def test_hapus_panen_mengembalikan_populasi_dan_penambahan_mengurangi(client, pemilik, setup):
    _, k = setup
    panen = catat(client, pemilik, k.siklus_id, "PANEN", 30)
    tambah = catat(client, pemilik, k.siklus_id, "PENAMBAHAN", 10)
    assert jumlah_ayam(client, pemilik, k) == 80
    hapus(client, pemilik, f"/siklus/{k.siklus_id}/populasi/{panen['id']}")
    assert jumlah_ayam(client, pemilik, k) == 110
    hapus(client, pemilik, f"/siklus/{k.siklus_id}/populasi/{tambah['id']}")
    assert jumlah_ayam(client, pemilik, k) == 100


def test_hapus_penambahan_yang_membuat_negatif_ditolak(client, pemilik, setup):
    _, k = setup
    tambah = catat(client, pemilik, k.siklus_id, "PENAMBAHAN", 50)
    catat(client, pemilik, k.siklus_id, "PANEN", 140)  # sisa 10
    r = hapus(client, pemilik, f"/siklus/{k.siklus_id}/populasi/{tambah['id']}")
    assert r.status_code == 409
    assert jumlah_ayam(client, pemilik, k) == 10


def test_hapus_populasi_siklus_selesai_atau_tidak_ada(client, pemilik, setup):
    _, k = setup
    p = catat(client, pemilik, k.siklus_id, "MORTALITAS", 1)
    assert hapus(client, pemilik, f"/siklus/{k.siklus_id}/populasi/{uuid.uuid4()}").status_code == 404
    post(client, pemilik, f"/siklus/{k.siklus_id}/selesai")
    assert hapus(client, pemilik, f"/siklus/{k.siklus_id}/populasi/{p['id']}").status_code == 409


def test_hapus_populasi_hanya_pemilik_yang_berhak(client, pemilik, pemilik_lain, setup):
    _, k = setup
    p = catat(client, pemilik, k.siklus_id, "MORTALITAS", 1)
    assert hapus(client, pemilik_lain, f"/siklus/{k.siklus_id}/populasi/{p['id']}").status_code in (403, 404)

    post(client, pemilik, "/users", {"nama": "Budi", "email": "budi@example.com", "kata_sandi": "budi12345", "role": "PEKERJA"})
    budi = get(client, pemilik, "/users")[0]["id"]
    post(client, pemilik, f"/users/{budi}/penugasan", {"kandang_id": k.id, "tanggal_mulai": "2026-11-01"})
    hp = login(client, "budi@example.com", "budi12345")
    assert hapus(client, hp, f"/siklus/{k.siklus_id}/populasi/{p['id']}").status_code == 403


# ---------- PATCH siklus ----------

def test_koreksi_jumlah_ayam_menandai_formulasi_perlu_ditinjau(client, pemilik, setup):
    _, k = setup
    f = simpan_formulasi_otomatis(client, pemilik, k)
    r = client.patch(f"{API}/siklus/{k.siklus_id}", json={"jumlah_ayam": 120, "tanggal_mulai": "2026-10-30"}, headers=pemilik)
    assert r.status_code == 200, r.text
    assert r.json()["jumlah_ayam"] == 120 and r.json()["tanggal_mulai"] == "2026-10-30"
    assert get(client, pemilik, f"/formulasi/{f}")["status"] == "PERLU_DITINJAU"
    assert "PERLU_DITINJAU" in [n["jenis"] for n in get(client, pemilik, "/notifikasi")]
    assert len(aksi_audit("KOREKSI_SIKLUS")) == 1


def test_koreksi_tanggal_saja_tidak_menandai_formulasi(client, pemilik, setup):
    _, k = setup
    f = simpan_formulasi_otomatis(client, pemilik, k)
    r = client.patch(f"{API}/siklus/{k.siklus_id}", json={"tanggal_mulai": "2026-10-28"}, headers=pemilik)
    assert r.status_code == 200
    assert get(client, pemilik, f"/formulasi/{f}")["status"] == "VALID"


def test_koreksi_siklus_validasi(client, pemilik, setup):
    _, k = setup
    url = f"{API}/siklus/{k.siklus_id}"
    assert client.patch(url, json={}, headers=pemilik).status_code == 400
    assert client.patch(url, json={"jumlah_ayam": -1}, headers=pemilik).status_code == 422
    post(client, pemilik, f"/siklus/{k.siklus_id}/selesai")
    assert client.patch(url, json={"jumlah_ayam": 5}, headers=pemilik).status_code == 409


def test_koreksi_siklus_hanya_pemilik_sendiri(client, pemilik, pemilik_lain, setup):
    _, k = setup
    r = client.patch(f"{API}/siklus/{k.siklus_id}", json={"jumlah_ayam": 5}, headers=pemilik_lain)
    assert r.status_code in (403, 404)
