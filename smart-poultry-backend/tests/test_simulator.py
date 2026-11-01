"""Simulator alat (../simulator/run.py) dijalankan terhadap API sungguhan lewat TestClient."""
import random
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "simulator"))
from run import Simulator, TokenDitolak  # noqa: E402

from tests.helpers import API, buat_kandang, buat_master, get, post, simpan_formulasi_otomatis  # noqa: E402


@pytest.fixture
def setup(client, pemilik):
    d = buat_master(client, pemilik)
    k = buat_kandang(client, pemilik, d)
    f = simpan_formulasi_otomatis(client, pemilik, k)
    return d, k, f


def buat_sim(client, k, **kw):
    kw.setdefault("sleep", lambda s: None)
    kw.setdefault("rng", random.Random(1))
    return Simulator(client, k.device_token, **kw)


def total_stok(client, h, k):
    return sum(s["jumlah_estimasi"] for s in get(client, h, f"/kandang/{k.id}/stok"))


def beri_makan(client, h, k, f):
    return post(client, h, f"/kandang/{k.id}/perintah/beri-makan", {"formulasi_id": f})["id"]


def status_perintah(client, h, pid):
    return get(client, h, f"/perintah/{pid}")["status"]


def test_heartbeat_tanpa_perintah_membuat_alat_online(client, pemilik, setup):
    _, k, _ = setup
    assert buat_sim(client, k).step() is None
    assert get(client, pemilik, f"/kandang/{k.id}")["status_alat"] == "ONLINE"


def test_token_salah_ditolak(client, setup):
    _, k, _ = setup
    sim = Simulator(client, "ngawur", sleep=lambda s: None)
    with pytest.raises(TokenDitolak):
        sim.step()


def test_perintah_beri_makan_selesai_sukses_dan_stok_berkurang(client, pemilik, setup):
    _, k, f = setup
    sim = buat_sim(client, k)
    sim.step()  # alat online
    sebelum = total_stok(client, pemilik, k)
    pid = beri_makan(client, pemilik, k, f)

    assert sim.step()["id"] == pid
    detail = get(client, pemilik, f"/perintah/{pid}")
    assert detail["status"] == "SUKSES" and detail["log_eksekusi"]["status"] == "SUKSES"
    assert detail["log_eksekusi"]["berat_aktual"] == pytest.approx(1000, rel=0.05)
    assert sebelum - total_stok(client, pemilik, k) == pytest.approx(1250, abs=0.5)  # stok memakai berat_per_sesi formulasi
    assert "PERINTAH_SUKSES" in [n["jenis"] for n in get(client, pemilik, "/notifikasi")]


def test_fail_rate_menghasilkan_gagal_tanpa_pengurangan_stok(client, pemilik, setup):
    _, k, f = setup
    sim = buat_sim(client, k, fail_rate=1.0)
    sim.step()
    sebelum = total_stok(client, pemilik, k)
    pid = beri_makan(client, pemilik, k, f)
    sim.step()
    assert status_perintah(client, pemilik, pid) == "GAGAL"
    assert total_stok(client, pemilik, k) == sebelum


def test_skip_stock_menghasilkan_gagal_dengan_log_skipped(client, pemilik, setup):
    _, k, f = setup
    sim = buat_sim(client, k, skip_stock_rate=1.0)
    sim.step()
    pid = beri_makan(client, pemilik, k, f)
    sim.step()
    detail = get(client, pemilik, f"/perintah/{pid}")
    assert detail["status"] == "GAGAL" and detail["log_eksekusi"]["status"] == "SKIPPED_STOCK"


def test_stop_darurat_langsung_diselesaikan(client, pemilik, setup):
    _, k, _ = setup
    sim = buat_sim(client, k)
    sim.step()
    sid = post(client, pemilik, f"/kandang/{k.id}/perintah/stop-darurat")["id"]
    assert sim.step()["id"] == sid
    assert status_perintah(client, pemilik, sid) == "SUKSES"


def test_kirim_ulang_log_setelah_jaringan_putus_tidak_menggandakan(client, pemilik, setup):
    """Server memproses log, tetapi respons hilang; simulator mengirim ulang dengan id yang sama."""
    _, k, f = setup

    class JaringanPutusSekali:
        def __init__(self, inner):
            self.inner, self.putus = inner, True
            self.status_log = []

        def post(self, url, **kw):
            r = self.inner.post(url, **kw)
            if url.endswith("/log"):
                self.status_log.append(r.status_code)
                if self.putus:
                    self.putus = False
                    raise httpx.ConnectError("respons hilang")
            return r

    http = JaringanPutusSekali(client)
    sim = Simulator(http, k.device_token, sleep=lambda s: None, rng=random.Random(1))
    sim.step()
    sebelum = total_stok(client, pemilik, k)
    pid = beri_makan(client, pemilik, k, f)
    sim.step()

    assert http.status_log == [201, 200]  # kirim ulang dibalas log yang sama
    assert status_perintah(client, pemilik, pid) == "SUKSES"
    assert sebelum - total_stok(client, pemilik, k) == pytest.approx(1250, abs=0.5)  # hanya sekali


def test_stop_darurat_saat_memproses_menghentikan_perintah_berjalan(client, pemilik, setup):
    _, k, f = setup
    stop = {}

    def tidur(detik):
        if not stop:  # pada jeda pertama (setelah perintah berjalan) pengguna menekan stop darurat
            stop["id"] = post(client, pemilik, f"/kandang/{k.id}/perintah/stop-darurat")["id"]

    sim = Simulator(client, k.device_token, sleep=tidur, rng=random.Random(1), ambil_delay=0, proses_delay=25, interval=10)
    sim.step()
    sebelum = total_stok(client, pemilik, k)
    pid = beri_makan(client, pemilik, k, f)
    sim.step()

    assert status_perintah(client, pemilik, pid) == "GAGAL"          # dibatalkan server
    assert status_perintah(client, pemilik, stop["id"]) == "SUKSES"  # dituntaskan simulator
    assert total_stok(client, pemilik, k) == sebelum


def test_simulasi_offline_melewati_heartbeat(client, pemilik, setup):
    _, k, _ = setup
    jam = {"t": 0.0}
    sim = Simulator(client, k.device_token, sleep=lambda s: jam.__setitem__("t", jam["t"] + s),
                    clock=lambda: jam["t"], interval=10, offline_after=15, offline_for=30)
    dipanggil = []
    asli = sim.heartbeat
    sim.heartbeat = lambda: dipanggil.append(jam["t"]) or asli()
    sim.run(max_steps=7)
    # t = 0, 10 (online) | 20, 30, 40 (offline: 15 <= t < 45) | 50, 60 (online)
    assert dipanggil == [0.0, 10.0, 50.0, 60.0]
