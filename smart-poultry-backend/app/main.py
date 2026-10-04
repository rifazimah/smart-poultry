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


# Router akan didaftarkan di sini seiring endpoint di API_CONTRACT.md diimplementasikan, mis.:
# from .routers import auth, kandang, formulasi, perintah, device
# app.include_router(auth.router)
# app.include_router(kandang.router)
# ...
