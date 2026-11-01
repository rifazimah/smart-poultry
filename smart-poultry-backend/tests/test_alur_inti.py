"""Otomasi smoke test Swagger: master data -> formulasi -> beri makan -> alat -> stok -> notifikasi."""
import uuid

import pytest

from tests.helpers import (
    API, buat_kandang, buat_master, device_h, formulasi_manual_valid, get, heartbeat, post,
    simpan_formulasi_otomatis,
)


@pytest.fixture
def setup(client, pemilik):
    d = buat_master(client, pemilik)
    k = buat_kandang(client, pemilik, d)
    return d, k


def _stok(client, h, k):
    return {s["nama_bahan"]: s["jumlah_estimasi"] for s in get(client, h, f"/kandang/{k.id}/stok")}


def test_simpan_formulasi_aktif_dan_menggantikan_yang_lama(client, pemilik, setup):
    d, k = setup
    f1 = simpan_formulasi_otomatis(client, pemilik, k)
    preview = post(client, pemilik, f"/siklus/{k.siklus_id}/formulasi/manual", formulasi_manual_valid(d))
    f2 = post(client, pemilik, "/formulasi", preview)["id"]

    riwayat = {f["id"]: f for f in get(client, pemilik, f"/siklus/{k.siklus_id}/formulasi")}
    assert riwayat[f1]["aktif"] is False
    assert riwayat[f2]["aktif"] is True and riwayat[f2]["status"] == "VALID"
    lengkap = get(client, pemilik, f"/formulasi/{f2}")
    assert lengkap["item"] and lengkap["nutrisi_hasil"]


def test_pindah_fase_menandai_perlu_ditinjau_dan_selesai_siklus_menonaktifkan(client, pemilik, setup):
    d, k = setup
    f = simpan_formulasi_otomatis(client, pemilik, k)

    r = client.patch(f"{API}/siklus/{k.siklus_id}/fase", json={"fase_id": d.fase_grower}, headers=pemilik)
    assert r.status_code == 200, r.text
    assert get(client, pemilik, f"/formulasi/{f}")["status"] == "PERLU_DITINJAU"

    r = client.post(f"{API}/siklus/{k.siklus_id}/selesai", json={}, headers=pemilik)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "SELESAI"
    assert get(client, pemilik, f"/formulasi/{f}")["aktif"] is False


def test_alur_beri_makan_sampai_stok_berkurang(client, pemilik, setup):
    d, k = setup
    f = simpan_formulasi_otomatis(client, pemilik, k)

    # alat belum heartbeat -> OFFLINE
    r = client.post(f"{API}/kandang/{k.id}/perintah/beri-makan", json={"formulasi_id": f}, headers=pemilik)
    assert r.status_code == 409

    hb = heartbeat(client, k)
    assert hb["perintah_pending"] is None
    assert hb["config"]["heartbeat_interval_seconds"] == 10

    perintah = post(client, pemilik, f"/kandang/{k.id}/perintah/beri-makan", {"formulasi_id": f})
    assert perintah["status"] == "PENDING"
    pid = perintah["id"]

    # perintah lain ditolak selama masih aktif
    r = client.post(f"{API}/kandang/{k.id}/perintah/beri-makan", json={"formulasi_id": f}, headers=pemilik)
    assert r.status_code == 409

    assert heartbeat(client, k)["perintah_pending"]["id"] == pid
    for aksi, status in [("ambil", "DIAMBIL"), ("mulai", "BERJALAN")]:
        r = client.post(f"{API}/device/perintah/{pid}/{aksi}", json={}, headers=device_h(k))
        assert r.status_code == 200 and r.json()["status"] == status

    sebelum = _stok(client, pemilik, k)
    log = {"id_eksekusi_unik": str(uuid.uuid4()), "berat_aktual": 1250, "status": "SUKSES"}
    r = client.post(f"{API}/device/perintah/{pid}/log", json=log, headers=device_h(k))
    assert r.status_code == 201, r.text

    detail = get(client, pemilik, f"/perintah/{pid}")
    assert detail["status"] == "SUKSES" and detail["log_eksekusi"]

    sesudah = _stok(client, pemilik, k)
    berkurang = sum(sebelum[n] - sesudah[n] for n in sebelum)
    assert berkurang == pytest.approx(1250, abs=0.5)

    notif = get(client, pemilik, "/notifikasi")
    assert any(n["jenis"] == "PERINTAH_SUKSES" and n["status"] == "BELUM_DIBACA" for n in notif)
    r = client.patch(f"{API}/notifikasi/baca-semua", headers=pemilik)
    assert r.status_code == 204
    assert get(client, pemilik, "/notifikasi?status=BELUM_DIBACA") == []


def test_log_gagal_tidak_mengurangi_stok(client, pemilik, setup):
    d, k = setup
    f = simpan_formulasi_otomatis(client, pemilik, k)
    heartbeat(client, k)
    pid = post(client, pemilik, f"/kandang/{k.id}/perintah/beri-makan", {"formulasi_id": f})["id"]
    client.post(f"{API}/device/perintah/{pid}/ambil", json={}, headers=device_h(k))
    client.post(f"{API}/device/perintah/{pid}/mulai", json={}, headers=device_h(k))
    sebelum = _stok(client, pemilik, k)

    log = {"id_eksekusi_unik": str(uuid.uuid4()), "berat_aktual": 0, "status": "GAGAL"}
    r = client.post(f"{API}/device/perintah/{pid}/log", json=log, headers=device_h(k))
    assert r.status_code == 201, r.text
    assert get(client, pemilik, f"/perintah/{pid}")["status"] == "GAGAL"
    assert _stok(client, pemilik, k) == sebelum
    assert any(n["jenis"] == "PERINTAH_GAGAL" for n in get(client, pemilik, "/notifikasi"))


def test_device_token_salah_401(client, setup):
    r = client.post(f"{API}/device/heartbeat", json={"status": "ONLINE"}, headers={"X-Device-Token": "ngawur"})
    assert r.status_code == 401


def test_koreksi_stok_tanpa_alasan_422(client, pemilik, setup):
    d, k = setup
    r = client.post(f"{API}/wadah/{k.wadah['jagung']}/stok/koreksi",
                    json={"jumlah_baru": 100, "alasan": ""}, headers=pemilik)
    assert r.status_code == 422
