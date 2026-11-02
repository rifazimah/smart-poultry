import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .config import settings
from .database import engine

logger = logging.getLogger("smart_poultry")

app = FastAPI(
    title="Smart Poultry API",
    version="0.1.0-mvp",
    description="Lihat docs/spesifikasi/API_CONTRACT.md untuk daftar lengkap endpoint yang direncanakan.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],  # total data untuk paginasi di frontend
)


@app.get("/health")
def health():
    """Cek cepat: server jalan & bisa dipanggil. Belum menyentuh database."""
    return {"status": "ok"}


@app.get("/health/db")
def health_db():
    """Cek kesiapan: server dapat menjalankan query ke database. 503 bila database tidak terjangkau."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Health check database gagal")
        return JSONResponse(status_code=503, content={"status": "error", "database": "tidak terjangkau"})
    return {"status": "ok", "database": "ok"}


from .routers import auth, users, kandang, masterdata, siklus, formulasi, perintah, device, stok, notifikasi, template  # noqa: E402

app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(kandang.router, prefix="/api/v1")
app.include_router(masterdata.router, prefix="/api/v1")
app.include_router(siklus.router, prefix="/api/v1")
app.include_router(formulasi.router, prefix="/api/v1")
app.include_router(perintah.router, prefix="/api/v1")
app.include_router(device.router, prefix="/api/v1")
app.include_router(stok.router, prefix="/api/v1")
app.include_router(notifikasi.router, prefix="/api/v1")
app.include_router(template.router, prefix="/api/v1")
