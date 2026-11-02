# Panduan Operasional: Container, CI, dan Production

Melengkapi [setup-backend](setup-backend.md) (lingkungan lokal). Dokumen ini untuk menjalankan backend di Docker, membaca hasil CI,
dan menyiapkan deployment. Staging online belum ada (keputusan D-10: tiap anggota memakai database lokal); isi dokumen ini siap dipakai ketika staging dibutuhkan.

## 1. Variabel lingkungan

Backend membaca environment (atau `.env` di folder `smart-poultry-backend` saat dijalankan di komputer).

| Variabel | Bawaan | Production | Keterangan |
|---|---|---|---|
| `ENVIRONMENT` | `development` | **`production`** | Pada `production` aplikasi **menolak start** bila `JWT_SECRET` lemah/bawaan, dan mematikan SQL echo |
| `DATABASE_URL` | postgres lokal | wajib | `postgresql+psycopg://USER:PASSWORD@HOST:PORT/DB`. Dalam compose host-nya `db`; dari container ke database di host gunakan `host.docker.internal` |
| `JWT_SECRET` | `ganti-ini-di-.env` | **wajib, ≥ 32 karakter acak** | Tidak boleh mengandung kata `ganti`/placeholder. Buat: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `JWT_EXPIRE_MINUTES` | 1440 | sesuaikan | Masa berlaku token login |
| `CORS_ORIGINS` | `localhost:5173`, `:3000` | domain frontend | JSON array, mis. `["https://app.contoh.id"]` |
| `LOGIN_MAX_GAGAL` / `LOGIN_JENDELA_DETIK` | 5 / 300 | sesuaikan | Percobaan login gagal per email+alamat klien sebelum 429 |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | `admin@smartpoultry.com` / kosong | isi `ADMIN_PASSWORD` atau biarkan acak | Hanya untuk `seed_admin.py` |
| `DEVICE_HEARTBEAT_INTERVAL_SECONDS` | 10 | 10 | Interval heartbeat alat |
| `PERINTAH_TIMEOUT_PENDING_SECONDS` / `_BERJALAN_SECONDS` | 60 / 300 | sesuaikan | Batas waktu perintah |
| `ALAT_OFFLINE_AFTER_SECONDS` | 0 (=3× heartbeat) | — | Batas alat dianggap offline |
| `SQL_ECHO` | `false` | diabaikan | Dipaksa `false` pada production |

Khusus container: `PORT` (default 8000), `MIGRATE_ON_START` (default `true`), `UVICORN_ARGS` (argumen tambahan uvicorn).
Khusus compose: `POSTGRES_PORT` (default 5432), `BACKEND_PORT` (default 8000).

## 2. Menjalankan backend di Docker

### Dengan docker compose (lokal/uji)
`docker compose up -d` tetap hanya menyalakan database. Backend ada di profil `app`:

```bash
docker compose --profile app up -d --build      # build image + jalankan db dan backend
docker compose ps                                # backend harus "healthy"
docker compose --profile app logs -f backend
docker compose --profile app down                # hentikan (data DB tetap); tambahkan -v untuk menghapus data
```
Backend tersedia di `http://localhost:8000` (ubah dengan `BACKEND_PORT`). Mulai-ulang tidak perlu migrasi manual: lihat bagian 3.
Di Docker-di-WSL, jaga sesi WSL tetap hidup ([setup-backend](setup-backend.md#khusus-jalur-b-docker-di-wsl-ubuntu)).

### Image mandiri
```bash
docker build -t smart-poultry-backend ./smart-poultry-backend
docker run -d --name backend -p 8000:8000 \
  -e ENVIRONMENT=production \
  -e DATABASE_URL='postgresql+psycopg://USER:PASSWORD@HOST:5432/smart_poultry' \
  -e JWT_SECRET='<string acak >= 32 karakter>' \
  -e CORS_ORIGINS='["https://app.contoh.id"]' \
  smart-poultry-backend
```
Sifat image: `python:3.12-slim`, ±630 MB, berjalan sebagai user non-root (uid 10001), `HEALTHCHECK` ke `/health`. Hanya berisi `app/`, `alembic/`, `alembic.ini`, `seed_admin.py`
(tanpa test dan `seed_demo.py`).

## 3. Migrasi database

Entrypoint menjalankan `alembic upgrade head` setiap container start (keputusan: otomatis, paling sederhana untuk satu instance). Konsekuensi:
- Migrasi baru ikut terpasang saat image baru dijalankan; **cadangkan database sebelum deploy** yang membawa migrasi.
- Dengan beberapa instance sekaligus, jalankan migrasi dari satu tempat saja: set `MIGRATE_ON_START=false` pada instance biasa dan jalankan sekali
  `docker run --rm -e DATABASE_URL=... smart-poultry-backend alembic upgrade head`.
- Migrasi `c5f8b2a41d7e` (hash token alat) mengubah token lama menjadi hash di tempat; alat yang sudah terdaftar tetap valid dengan token lamanya.
  Downgrade tidak dapat memulihkan token mentah (semua alat perlu dirotasi tokennya).

## 4. Akun admin pertama

```bash
docker compose --profile app exec backend python seed_admin.py                       # development: admin123 (hanya lokal!)
docker compose --profile app exec -e ADMIN_PASSWORD='<kata sandi kuat>' backend python seed_admin.py
```
Pada `ENVIRONMENT=production` tanpa `ADMIN_PASSWORD`, password **acak** dicetak sekali di akhir output; simpan segera lalu ganti lewat `POST /auth/ganti-kata-sandi`.
`seed_demo.py` sengaja menolak berjalan di production dan tidak ada di image.

## 5. Health check

| Endpoint | Menyentuh DB | Pakai untuk |
|---|---|---|
| `GET /health` | tidak | *Liveness*: proses hidup (dipakai `HEALTHCHECK` image) |
| `GET /health/db` | ya (`SELECT 1`) | *Readiness*/monitoring: 200 `{"status":"ok","database":"ok"}`, 503 bila database tidak terjangkau (tanpa detail internal) |

Koneksi database memakai `connect_timeout` 5 detik dan `pool_pre_ping`, sehingga database mati menghasilkan galat cepat, bukan permintaan yang menggantung.

## 6. Lint dan CI

Lokal (dari `smart-poultry-backend`, venv aktif):
```bash
ruff check .            # lint (aturan konservatif E4/E7/E9/F, konfigurasi di pyproject.toml)
pytest -q
alembic upgrade head && alembic check     # pada database kosong: pastikan model dan migrasi tidak berbeda
```
`ruff format` belum diwajibkan (akan mengubah hampir semua berkas); kode baru sebaiknya mengikuti gaya sekitarnya.

**GitHub Actions** (`.github/workflows/ci.yml`) berjalan pada setiap push dan Pull Request ke `main`: pasang dependency → `ruff check` → `alembic upgrade head`
dari database kosong + satu `head` + `alembic check` → `pytest -q`, dengan service PostgreSQL 16. Melihat hasil: tab **Actions** di GitHub, atau bagian
*Checks* pada halaman Pull Request. Disarankan mengaktifkan *branch protection* pada `main` (Settings → Branches → "Require status checks to pass": job `backend`).
Bila CI merah, jalankan tiga perintah di atas secara lokal dan bandingkan.

> Workflow ini sudah divalidasi sintaksnya dan setiap langkahnya dijalankan lokal, tetapi **belum pernah berjalan di GitHub**: periksa run pertama dan laporkan bila ada penyimpangan.

## 7. Fitur keamanan

- **Secret production**: `ENVIRONMENT=production` + `JWT_SECRET` lemah → aplikasi gagal start dengan pesan jelas (`ValidationError ... JWT_SECRET`).
- **Login**: user `NONAKTIF` ditolak (403, setelah kata sandi benar); 5 percobaan gagal per (email, alamat klien) dalam 300 detik → 429 dengan header `Retry-After`;
  login sukses mereset hitungan; `/auth/login` dan `/auth/swagger-login` berbagi pembatas.
  *Batas*: pembatas disimpan di memori per proses (hilang saat restart; bila ada beberapa worker/instance, batas berlaku per proses).
  Di balik reverse proxy, alamat klien adalah alamat proxy kecuali uvicorn dijalankan dengan `UVICORN_ARGS="--proxy-headers --forwarded-allow-ips=<IP proxy>"`
  (jangan memakai `*` bila backend dapat diakses langsung).
- **Token alat**: disimpan sebagai SHA-256; token mentah hanya ditampilkan sekali saat `POST /kandang/{id}/alat` atau `POST /alat/{id}/rotasi-token`. Token yang hilang tidak dapat dipulihkan, hanya dirotasi.
- **Kata sandi**: bcrypt (`bcrypt<4.1` ditetapkan di `requirements.txt` demi kompatibilitas passlib).

## 8. Daftar centang production

- [ ] `ENVIRONMENT=production`, `JWT_SECRET` acak ≥ 32 karakter (jangan di-commit; simpan di pengelola rahasia platform).
- [ ] `DATABASE_URL` ke database terkelola dengan password kuat (bukan `admin` / `popuri123` dari compose lokal); koneksi publik hanya lewat TLS (`?sslmode=require` bila disediakan penyedia).
- [ ] `CORS_ORIGINS` berisi domain frontend sebenarnya saja.
- [ ] Akun admin: `ADMIN_PASSWORD` kuat atau simpan password acak, lalu ganti.
- [ ] HTTPS ditangani platform/reverse proxy; atur `UVICORN_ARGS` bila perlu `--proxy-headers`.
- [ ] Cadangan terjadwal ([bagian 9](#9-cadangan-dan-pemulihan)) dan uji pemulihan sekali.
- [ ] Pantau `GET /health/db`; log dibaca dari `docker logs` / log platform.
- [ ] `branch protection` + CI hijau sebelum merge ke `main`.

## 9. Cadangan dan pemulihan

```bash
# cadangan (jalankan di mesin yang dapat menjangkau database)
pg_dump "postgresql://USER:PASSWORD@HOST:5432/smart_poultry" --no-owner --clean --if-exists > backup.sql
# pemulihan (menimpa isi database tujuan!)
psql "postgresql://USER:PASSWORD@HOST:5432/smart_poultry" -q < backup.sql
```
Untuk database di compose lokal: `docker compose exec -T db pg_dump -U admin -d smart_poultry --no-owner --clean --if-exists > backups/data.sql`
(lihat [setup-backend](setup-backend.md#12-berbagi-data-tanpa-database-bersama)). Jangan commit berkas cadangan.

## 10. Batas yang diketahui

- Pembatas login per proses (lihat bagian 7); belum ada penyimpanan bersama.
- Diuji pada Python 3.12; Python 3.13 belum diuji (`passlib` 1.7 sudah tidak dipelihara).
- `WAJIB_GANTI_SANDI` ada di enum tetapi tidak ada alur yang memakainya, sehingga belum ditegakkan.
- JWT memakai `sub=email`; mengubah email Pengguna menginvalidasi tokennya (belum ada endpoint ubah email).
- Belum ada log terstruktur / `request_id`, pemantauan, dan staging online (D-10).
- Image ±630 MB karena scipy/numpy; cukup untuk MVP.
