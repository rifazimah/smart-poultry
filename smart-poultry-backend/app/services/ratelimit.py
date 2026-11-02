import math
import threading
import time
from collections import deque
from typing import Callable, Deque, Dict

from fastapi import HTTPException

from app.config import settings

_BATAS_KUNCI = 10_000  # di atas ini, bersihkan entri yang sudah kedaluwarsa agar memori tidak membengkak


class PembatasPercobaan:
    """
    Pembatas percobaan gagal (sliding window) in-memory.

    Catatan: penyimpanan per proses. Dengan beberapa worker/instance, batasnya berlaku per proses
    (cukup untuk MVP satu instance; gunakan penyimpanan bersama bila diskalakan).
    """

    def __init__(self, maks: int, jendela_detik: float, clock: Callable[[], float] = time.monotonic):
        self.maks = maks
        self.jendela = jendela_detik
        self.clock = clock
        self._gagal: Dict[str, Deque[float]] = {}
        self._kunci = threading.Lock()

    def _pangkas(self, antrean: Deque[float], sekarang: float) -> None:
        while antrean and sekarang - antrean[0] >= self.jendela:
            antrean.popleft()

    def periksa(self, kunci: str) -> None:
        """Lempar 429 (+ Retry-After) bila percobaan gagal pada `kunci` sudah mencapai batas."""
        with self._kunci:
            sekarang = self.clock()
            antrean = self._gagal.get(kunci)
            if not antrean:
                return
            self._pangkas(antrean, sekarang)
            if not antrean:
                del self._gagal[kunci]
                return
            if len(antrean) >= self.maks:
                tunggu = max(1, math.ceil(self.jendela - (sekarang - antrean[0])))
                raise HTTPException(
                    status_code=429,
                    detail=f"Terlalu banyak percobaan login yang gagal. Coba lagi dalam {tunggu} detik.",
                    headers={"Retry-After": str(tunggu)},
                )

    def catat_gagal(self, kunci: str) -> None:
        with self._kunci:
            sekarang = self.clock()
            if len(self._gagal) >= _BATAS_KUNCI:
                for k in list(self._gagal):
                    self._pangkas(self._gagal[k], sekarang)
                    if not self._gagal[k]:
                        del self._gagal[k]
            self._gagal.setdefault(kunci, deque()).append(sekarang)

    def reset(self, kunci: str) -> None:
        with self._kunci:
            self._gagal.pop(kunci, None)

    def bersihkan(self) -> None:
        """Hapus semua catatan (dipakai test)."""
        with self._kunci:
            self._gagal.clear()


pembatas_login = PembatasPercobaan(settings.login_max_gagal, settings.login_jendela_detik)
