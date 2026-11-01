"""Stok otomatis (T-6) dan validasi perintah beri makan (T-5, D-4)."""
import uuid

import pytest

from tests.helpers import (
    API, buat_kandang, buat_master, formulasi_manual_valid, get, heartbeat, post, simpan_formulasi_otomatis,
)


@pytest.fixture
def setup(client, pemilik):
    d = buat_master(client, pemilik)
    k = buat_kandang(client, pemilik, d)
    heartbeat(client, k)
    return d, k


def beri_makan(client, h, k, formulasi_id):
    return client.post(f"{API}/kandang/{k.id}/perintah/beri-makan", json={"formulasi_id": formulasi_id}, headers=h)


def test_stok_dibuat_otomatis_saat_wadah_dibuat(client, pemilik):
    d = buat_master(client, pemilik)
    k = buat_kandang(client, pemilik, d, isi_stok=False)
    stok = get(client, pemilik, f"/kandang/{k.id}/stok")
    assert len(stok) == 4
    assert all(s["jumlah_estimasi"] == 0 for s in stok)
    assert {s["nama_bahan"] for s in stok} == {"Jagung", "Bungkil Kedelai", "Dedak", "Tepung Batu"}


def test_formulasi_tidak_ada_404(client, pemilik, setup):
    _, k = setup
    assert beri_makan(client, pemilik, k, str(uuid.uuid4())).status_code == 404


def test_formulasi_kandang_lain_409(client, pemilik, setup):
    d, k = setup
    k2 = buat_kandang(client, pemilik, d, nama="Kandang B")
    f2 = simpan_formulasi_otomatis(client, pemilik, k2)
    r = beri_makan(client, pemilik, k, f2)
    assert r.status_code == 409


def test_formulasi_digantikan_409(client, pemilik, setup):
    d, k = setup
    lama = simpan_formulasi_otomatis(client, pemilik, k)
    preview = post(client, pemilik, f"/siklus/{k.siklus_id}/formulasi/manual", formulasi_manual_valid(d))
    post(client, pemilik, "/formulasi", preview)
    assert beri_makan(client, pemilik, k, lama).status_code == 409


def test_formulasi_perlu_ditinjau_409(client, pemilik, setup):
    d, k = setup
    f = simpan_formulasi_otomatis(client, pemilik, k)
    client.patch(f"{API}/siklus/{k.siklus_id}/fase", json={"fase_id": d.fase_grower}, headers=pemilik)
    assert beri_makan(client, pemilik, k, f).status_code == 409


def test_stok_kurang_409_menyebut_bahan(client, pemilik, setup):
    d, k = setup
    f = simpan_formulasi_otomatis(client, pemilik, k)
    # kosongkan stok jagung lewat koreksi
    post(client, pemilik, f"/wadah/{k.wadah['jagung']}/stok/koreksi", {"jumlah_baru": 1, "alasan": "uji"})
    # formulasi otomatis hampir pasti memakai jagung; pastikan lewat detail
    nama_jagung = next(i for i in get(client, pemilik, f"/formulasi/{f}")["item"] if i["bahan_pakan_id"] == d.jagung)
    assert nama_jagung["berat_per_sesi"] > 1
    r = beri_makan(client, pemilik, k, f)
    assert r.status_code == 409
    assert "Jagung" in r.json()["detail"]


def test_tanpa_isi_ulang_ditolak(client, pemilik):
    d = buat_master(client, pemilik)
    k = buat_kandang(client, pemilik, d, isi_stok=False)
    heartbeat(client, k)
    f = simpan_formulasi_otomatis(client, pemilik, k)
    assert beri_makan(client, pemilik, k, f).status_code == 409


def test_formulasi_valid_dan_stok_cukup_201(client, pemilik, setup):
    _, k = setup
    f = simpan_formulasi_otomatis(client, pemilik, k)
    r = beri_makan(client, pemilik, k, f)
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "PENDING"
