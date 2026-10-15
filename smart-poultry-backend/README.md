# Smart Poultry — Backend (MVP)

Scope: automated feed formulation (LP-based + manual) and manual feeding
control via a device simulator. **Not included:** automated scheduling,
worker-approval flow, and dynamic Role/Permission (deferred to Phase 2).

See `API_CONTRACT.md` in the repo root for the full list of endpoints.

## 1. Prerequisites

| Tool | Version |
|---|---|
| Python | ≥ 3.11 |
| Docker + Docker Compose | any recent version (Docker Desktop or Docker Engine) |

## 2. Start the Database

The database runs in Docker via **docker-compose**. From the **monorepo root**:

```bash
# Start the PostgreSQL container in the background (creates it on first run)
docker compose up -d

# Verify it is healthy
docker compose ps
```

This starts the `db` service (PostgreSQL 16 Alpine, port **5432** mapped to
`localhost:5432`). Data is stored in the `smart_poultry_pgdata` named volume
and **survives** `docker compose down`. To wipe data completely, use
`docker compose down -v` (caution!).

> **Replaces the old manual workflow:** Previously the container was started
> with a bare `docker run` command and connected via its WSL IP (e.g.
> `172.23.x.x:5432`). The compose setup is identical in terms of image,
> credentials, and database name — no data migration is needed if you reuse
> the same named volume.

## 3. Set Up the Python Environment

```bash
cd smart-poultry-backend

python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

pip install -r requirements.txt

# Copy the example env file and review it
cp .env.example .env
```

The default `DATABASE_URL` in `.env.example` already points to `localhost:5432`
(Option A — app on host, DB in compose). You should not need to change it.

## 4. Run Database Migrations (first time only)

```bash
alembic upgrade head
```

On subsequent model changes, generate and apply a new migration:

```bash
alembic revision --autogenerate -m "describe your change"
alembic upgrade head
```

**Never edit tables directly via SQL** — always go through Alembic.

## 5. Run the Development Server

```bash
uvicorn app.main:app --reload
```

- Health check: `http://localhost:8000/health` → `{"status": "ok"}`
- Interactive API docs: `http://localhost:8000/docs`

## Folder Structure

```
smart-poultry/               ← monorepo root (git is here)
  docker-compose.yml         ← one-command local DB setup
  smart-poultry-backend/     ← this folder
    app/
      models/
        enums.py             → all enums (status, type, etc.)
        akses.py             → User, PenugasanKandang, AuditLog
        fisik.py             → Kandang, Alat, Wadah, Stok, TransaksiStok
        masterdata.py        → Nutrisi, BahanPakan, JenisAyam, Fase, etc.
        operasional.py       → SiklusKandang, Formulasi, Perintah, LogEksekusi, Notifikasi
      routers/               → one file per API section
      schemas/               → Pydantic request/response models
      services/              → business logic (formulasi LP, device handler)
      database.py            → engine & session
      config.py              → reads .env
      main.py                → FastAPI entrypoint
    alembic/                 → schema migrations
    API_CONTRACT.md          → endpoint reference (read before adding a router)
    CONVENTIONS.md           → coding rules (password hashing, LP solver, etc.)
    ARCHITECTURE.md          → system design & auth flow
    AGENTS.md                → rules for AI coding agents
```
