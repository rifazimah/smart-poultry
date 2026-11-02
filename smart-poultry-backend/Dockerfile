# Image backend Smart Poultry (FastAPI). Konteks build: folder ini (smart-poultry-backend/).
#   docker build -t smart-poultry-backend .
# Lihat docs/panduan/operasional.md untuk variabel lingkungan dan cara menjalankan.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependency dulu agar layer ini ter-cache selama requirements.txt tidak berubah.
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY alembic.ini seed_admin.py docker-entrypoint.sh ./
COPY alembic ./alembic
COPY app ./app

# Skrip bisa berakhiran baris CRLF bila di-clone di Windows; samakan lalu jalankan sebagai user non-root.
RUN sed -i 's/\r$//' docker-entrypoint.sh \
    && chmod +x docker-entrypoint.sh \
    && useradd --create-home --uid 10001 appuser \
    && chown -R appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=3 \
    CMD ["python", "-c", "import os,urllib.request as u; u.urlopen('http://127.0.0.1:%s/health' % os.environ.get('PORT', '8000'), timeout=4)"]

ENTRYPOINT ["./docker-entrypoint.sh"]
