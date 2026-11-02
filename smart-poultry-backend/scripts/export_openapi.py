"""
Ekspor skema OpenAPI backend ke ../frontend/openapi.json (sumber tipe TypeScript frontend).

Jalankan dari folder smart-poultry-backend setiap kali endpoint/skema berubah, lalu di frontend:
    npm run gen:api
Test `tests/test_openapi_snapshot.py` (dan CI) gagal bila berkas ini tertinggal.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402

TUJUAN = Path(__file__).resolve().parents[2] / "frontend" / "openapi.json"


def skema_saat_ini() -> dict:
    # round-trip JSON agar tipe sama dengan hasil baca berkas (tuple -> list, dst.)
    return json.loads(json.dumps(app.openapi()))


if __name__ == "__main__":
    TUJUAN.write_text(json.dumps(skema_saat_ini(), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Ditulis: {TUJUAN}")
