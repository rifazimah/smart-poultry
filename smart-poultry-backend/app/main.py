from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings

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
