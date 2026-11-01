"""
Simulator alat IoT Smart Poultry.

Meniru perilaku alat sungguhan lewat endpoint /device/* (lihat docs/spesifikasi/API_CONTRACT.md bagian 8):
heartbeat berkala -> bila ada perintah PENDING: ambil -> (jeda) -> mulai -> (jeda proses fisik) -> log.

Ini BUKAN bagian backend dan tidak mengimpor kode backend. Hanya butuh `httpx`.

Contoh:
    python simulator/run.py --device-token <token>
    python simulator/run.py --device-token <token> --proses-delay 8 --fail-rate 0.2
    python simulator/run.py --device-token <token> --once
"""
import argparse
import logging
import os
import random
import sys
import time
import uuid

import httpx

API = "/api/v1"
log = logging.getLogger("simulator")


class TokenDitolak(Exception):
    """Server menolak X-Device-Token (401)."""


class Simulator:
    def __init__(
        self,
        http,
        device_token,
        *,
        api_prefix=API,
        interval=None,
        ambil_delay=1.0,
        proses_delay=5.0,
        fail_rate=0.0,
        skip_stock_rate=0.0,
        berat_dasar=1000.0,
        offline_after=None,
        offline_for=0.0,
        retries=3,
        rng=None,
        sleep=time.sleep,
        clock=time.monotonic,
    ):
        self.http = http
        self.headers = {"X-Device-Token": device_token}
        self.prefix = api_prefix
        self.interval_override = interval
        self.interval_server = 10
        self.ambil_delay = ambil_delay
        self.proses_delay = proses_delay
        self.fail_rate = fail_rate
        self.skip_stock_rate = skip_stock_rate
        self.berat_dasar = berat_dasar
        self.offline_after = offline_after
        self.offline_for = offline_for
        self.retries = retries
        self.rng = rng or random.Random()
        self.sleep = sleep
        self.clock = clock
        self.t0 = clock()
        self._stop_pending = None  # perintah STOP_DARURAT yang terlihat saat memproses perintah lain

    # ---------- util ----------
    @property
    def interval(self):
        return self.interval_override or self.interval_server

    def _post(self, path, json=None):
        return self.http.post(self.prefix + path, json=json if json is not None else {}, headers=self.headers)

    def _post_retry(self, path, json):
        """Kirim ulang bila jaringan gagal; body (termasuk id_eksekusi_unik) sama sehingga idempoten."""
        for percobaan in range(1, self.retries + 1):
            try:
                return self._post(path, json)
            except httpx.TransportError as e:
                log.warning("Gagal kirim %s (percobaan %d/%d): %s", path, percobaan, self.retries, e)
                if percobaan == self.retries:
                    raise
                self.sleep(0.5 * percobaan)

    def offline_sekarang(self):
        if self.offline_after is None:
            return False
        t = self.clock() - self.t0
        return self.offline_after <= t < self.offline_after + self.offline_for

    # ---------- protokol ----------
    def heartbeat(self):
        r = self._post("/device/heartbeat", {"status": "ONLINE"})
        if r.status_code == 401:
            raise TokenDitolak(r.text)
        r.raise_for_status()
        data = r.json()
        self.interval_server = data["config"]["heartbeat_interval_seconds"]
        return data

    def step(self):
        """Satu putaran: heartbeat, lalu proses perintah bila ada. Mengembalikan perintah yang ditangani (atau None)."""
        if self.offline_sekarang():
            log.info("(simulasi offline) heartbeat dilewati")
            return None
        pending = self.heartbeat()["perintah_pending"]
        if pending:
            self.tangani(pending)
        return pending

    def _tunggu(self, detik):
        """Tunggu sambil tetap heartbeat. False bila ada STOP_DARURAT yang harus didahulukan."""
        sisa = detik
        while sisa > 0:
            langkah = min(sisa, self.interval)
            self.sleep(langkah)
            sisa -= langkah
            pending = self.heartbeat()["perintah_pending"]
            if pending and pending["tipe"] == "STOP_DARURAT":
                self._stop_pending = pending
                return False
        return True

    def tangani(self, perintah):
        pid, tipe = perintah["id"], perintah["tipe"]
        log.info("Perintah %s (%s) diterima", pid, tipe)

        r = self._post(f"/device/perintah/{pid}/ambil")
        if r.status_code != 200:
            log.warning("ambil ditolak (%s): %s", r.status_code, r.text)
            return

        if tipe == "STOP_DARURAT":
            self._selesaikan(pid, "SUKSES", 0.0)
            return

        if not self._tunggu(self.ambil_delay):
            return self._dahulukan_stop(pid)
        r = self._post(f"/device/perintah/{pid}/mulai")
        if r.status_code != 200:
            log.warning("mulai ditolak (%s): %s", r.status_code, r.text)
            return
        log.info("Mulai memproses %s (%.1f detik)", pid, self.proses_delay)

        if not self._tunggu(self.proses_delay):
            return self._dahulukan_stop(pid)

        status, berat = self._hasil()
        self._selesaikan(pid, status, berat)

    def _dahulukan_stop(self, pid):
        """Stop darurat datang saat memproses: hentikan, server sudah menandai perintah lama GAGAL."""
        log.warning("STOP DARURAT diterima; menghentikan perintah %s", pid)
        stop, self._stop_pending = self._stop_pending, None
        self.tangani(stop)

    def _hasil(self):
        if self.rng.random() < self.fail_rate:
            return "GAGAL", 0.0
        if self.rng.random() < self.skip_stock_rate:
            return "SKIPPED_STOCK", 0.0
        return "SUKSES", round(self.berat_dasar * self.rng.uniform(0.97, 1.03), 1)

    def _selesaikan(self, pid, status, berat):
        body = {"id_eksekusi_unik": str(uuid.uuid4()), "berat_aktual": berat, "status": status}
        r = self._post_retry(f"/device/perintah/{pid}/log", body)
        if r.status_code in (200, 201):
            log.info("Log %s terkirim (%s, %.1f g, HTTP %d)", pid, status, berat, r.status_code)
        else:
            log.warning("Log ditolak (%s): %s", r.status_code, r.text)

    # ---------- loop ----------
    def run(self, max_steps=None, once=False):
        n = 0
        while max_steps is None or n < max_steps:
            n += 1
            try:
                ditangani = self.step()
            except httpx.TransportError as e:
                log.warning("Server tidak terjangkau: %s", e)
                ditangani = None
            if once and ditangani:
                return
            self.sleep(self.interval)


def main(argv=None):
    p = argparse.ArgumentParser(description="Simulator alat IoT Smart Poultry")
    p.add_argument("--base-url", default=os.environ.get("SIMULATOR_BASE_URL", "http://localhost:8000"))
    p.add_argument("--device-token", default=os.environ.get("DEVICE_TOKEN"), help="atau env DEVICE_TOKEN")
    p.add_argument("--interval", type=float, help="paksa interval heartbeat (detik); default dari server")
    p.add_argument("--ambil-delay", type=float, default=1.0, help="jeda ambil -> mulai (detik)")
    p.add_argument("--proses-delay", type=float, default=5.0, help="durasi proses fisik (detik)")
    p.add_argument("--fail-rate", type=float, default=0.0, help="peluang log GAGAL (0-1)")
    p.add_argument("--skip-stock-rate", type=float, default=0.0, help="peluang log SKIPPED_STOCK (0-1)")
    p.add_argument("--berat-dasar", type=float, default=1000.0, help="berat aktual rata-rata (gram)")
    p.add_argument("--offline-after", type=float, help="mulai simulasi offline setelah N detik")
    p.add_argument("--offline-for", type=float, default=0.0, help="lama simulasi offline (detik)")
    p.add_argument("--once", action="store_true", help="berhenti setelah satu perintah selesai")
    p.add_argument("--seed", type=int, help="seed acak agar hasil dapat diulang")
    args = p.parse_args(argv)

    if not args.device_token:
        p.error("--device-token (atau env DEVICE_TOKEN) wajib diisi")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # satu baris per request terlalu berisik
    sim = Simulator(
        httpx.Client(base_url=args.base_url, timeout=10),
        args.device_token,
        interval=args.interval,
        ambil_delay=args.ambil_delay,
        proses_delay=args.proses_delay,
        fail_rate=args.fail_rate,
        skip_stock_rate=args.skip_stock_rate,
        berat_dasar=args.berat_dasar,
        offline_after=args.offline_after,
        offline_for=args.offline_for,
        rng=random.Random(args.seed),
    )
    log.info("Simulator berjalan -> %s (Ctrl+C untuk berhenti)", args.base_url)
    try:
        sim.run(once=args.once)
    except TokenDitolak:
        log.error("Device token ditolak server (401). Buat token baru lewat POST /alat/{id}/rotasi-token.")
        return 1
    except KeyboardInterrupt:
        log.info("Dihentikan.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
