"""Skema OpenAPI di frontend/openapi.json harus sama dengan skema aplikasi saat ini (menjaga tipe frontend tetap sinkron)."""
import json
import sys

from tests.conftest import BACKEND_DIR

sys.path.insert(0, str(BACKEND_DIR))
from scripts.export_openapi import TUJUAN, skema_saat_ini  # noqa: E402


def test_openapi_frontend_sinkron_dengan_backend():
    assert TUJUAN.exists(), "frontend/openapi.json belum ada. Jalankan: python scripts/export_openapi.py"
    tersimpan = json.loads(TUJUAN.read_text(encoding="utf-8"))
    assert tersimpan == skema_saat_ini(), (
        "frontend/openapi.json tertinggal dari API. Jalankan di smart-poultry-backend: "
        "python scripts/export_openapi.py, lalu di frontend: npm run gen:api, dan commit hasilnya."
    )
