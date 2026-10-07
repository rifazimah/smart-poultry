from fastapi import FastAPI

app = FastAPI(
    title="Smart Poultry API",
    version="0.1.0-mvp",
    description="Lihat API_CONTRACT.md untuk daftar lengkap endpoint yang direncanakan.",
)


@app.get("/health")
def health():
    """Cek cepat: server jalan & bisa dipanggil. Belum menyentuh database."""
    return {"status": "ok"}


from .routers import auth, users, kandang, masterdata, siklus

app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(kandang.router, prefix="/api/v1")
app.include_router(masterdata.router, prefix="/api/v1")
app.include_router(siklus.router, prefix="/api/v1")
