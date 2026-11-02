# Panduan Setup Lokal untuk Anggota Tim

Panduan ini membuat Anda dari nol sampai bisa menjalankan backend, data demo, simulator alat, dan test di komputer sendiri.
**Setiap anggota punya database sendiri** (PostgreSQL di Docker, lokal). Tidak ada database bersama.

Estimasi: 20–30 menit (sebagian besar mengunduh paket). Bagian 14 adalah daftar centang "setup berhasil".

## Daftar isi
1. [Prinsip kerja tim](#1-prinsip-kerja-tim)
2. [Prasyarat](#2-prasyarat)
3. [Mengambil kode](#3-mengambil-kode)
4. [Menjalankan database (Docker)](#4-menjalankan-database-docker)
5. [Lingkungan Python](#5-lingkungan-python)
6. [File `.env`](#6-file-env)
7. [Migrasi database](#7-migrasi-database)
8. [Data awal dan data demo](#data-demo)
9. [Menjalankan server](#9-menjalankan-server)
10. [Simulator alat](#10-simulator-alat)
11. [Menjalankan test](#11-menjalankan-test)
12. [Berbagi data tanpa database bersama](#12-berbagi-data-tanpa-database-bersama)
13. [Alur kerja tim](#13-alur-kerja-tim)
14. [Daftar centang setup berhasil](#14-daftar-centang-setup-berhasil)
15. [Troubleshooting](#15-troubleshooting)
16. [Cheat sheet harian](#16-cheat-sheet-harian)
17. [Status pengujian panduan](#17-status-pengujian-panduan)

---

## 1. Prinsip kerja tim

- **Database per anggota.** Data uji Anda tidak memengaruhi anggota lain, dan sebaliknya. Dataset yang sama didapat lewat `seed_demo.py` atau berkas dump ([bagian 12](#12-berbagi-data-tanpa-database-bersama)).
- **Kredensial di repo hanya untuk lokal.** `admin` / `popuri123` (database) dan `admin123` (akun admin) hanya pantas untuk komputer Anda sendiri.
- **`.env` tidak pernah di-commit** (sudah di-`.gitignore`). `.env.example` yang di-commit; salin lalu sesuaikan.
- **Skema database hanya berubah lewat Alembic**, tidak lewat SQL manual ([bagian 13](#13-alur-kerja-tim)).
- **Test memakai database terpisah** (`*_test`) yang dihapus isinya setiap kali test berjalan. Jangan pernah menunjuknya ke database kerja.

Struktur repo:

```
smart-poultry/
  docker-compose.yml          # PostgreSQL lokal
  smart-poultry-backend/      # FastAPI + Alembic + test (+ seed_admin.py, seed_demo.py)
  simulator/                  # simulator alat IoT
  docs/                       # semua dokumentasi
```

## 2. Prasyarat

| Alat | Versi | Cek |
|---|---|---|
| Git | bebas | `git --version` |
| Python | **3.11 atau lebih baru** (diuji 3.12) | `python --version` |
| Docker + Compose v2 | Compose v2 (perintah `docker compose`, bukan `docker-compose`) | `docker --version` dan `docker compose version` |

Pilih satu jalur Docker sesuai komputer Anda:

| Jalur | Untuk | Pemasangan |
|---|---|---|
| **A. Docker Desktop** | Windows 10/11 dan macOS | Pasang Docker Desktop (di Windows, aktifkan backend WSL 2), jalankan aplikasinya |
| **B. Docker Engine di WSL Ubuntu** (tanpa Docker Desktop) | Windows dengan Docker dipasang di dalam Ubuntu/WSL | Pasang Docker Engine di Ubuntu mengikuti dokumentasi resmi Docker, pastikan layanan `docker` aktif |
| **C. Docker Engine native** | Linux | Pasang Docker Engine + plugin Compose dari dokumentasi resmi Docker |

> **Windows: letakkan folder proyek pada path yang pendek** (mis. `C:\dev\smart-poultry`). Pada path yang dalam,
> `pip install` bisa gagal dengan `[WinError 206] The filename or extension is too long` (paket seperti numpy punya path internal panjang).
> Alternatif: aktifkan *long paths* Windows.

## 3. Mengambil kode

```bash
git clone https://github.com/rifazimah/smart-poultry.git
cd smart-poultry
git checkout -b nama-fitur-anda      # jangan bekerja langsung di main
```

## 4. Menjalankan database (Docker)

Perintah Docker dijalankan dari **root repo** (folder yang berisi `docker-compose.yml`).

```bash
docker compose up -d        # membuat dan menyalakan PostgreSQL 16
docker compose ps           # tunggu STATUS menjadi "healthy" (±10 detik)
```

Hasil: PostgreSQL berjalan di `localhost:5432` dengan user `admin`, password `popuri123`, database `smart_poultry`.
Data disimpan di *named volume* `smart_poultry_pgdata`, sehingga tetap ada setelah `docker compose down`.

**Port 5432 sudah dipakai** (mis. Postgres lain di komputer Anda)? Pilih port lain, lalu samakan di `.env` (bagian 6):

```bash
# Git Bash / macOS / Linux / WSL
POSTGRES_PORT=5433 docker compose up -d
# PowerShell
$env:POSTGRES_PORT = 5433; docker compose up -d
```
Atau buat berkas `.env` di **root repo** (terpisah dari `.env` backend) berisi `POSTGRES_PORT=5433`.

Masuk ke psql bila perlu: `docker compose exec db psql -U admin -d smart_poultry`.

### Khusus jalur B (Docker di WSL Ubuntu)

Bagian ini penting; hampir semua masalah jalur B ada di sini.

1. **WSL mati sendiri saat idle, dan container ikut mati.** Bila tidak ada sesi WSL yang terbuka, Windows menghentikan distro setelah beberapa saat
   (`wsl -l -v` menampilkan `Stopped`). Gejalanya: Alembic, `seed_*`, atau `pytest` **menggantung** karena database tidak menjawab.
   Penangkalnya, **jaga satu sesi WSL tetap terbuka** selama bekerja, salah satunya:
   - biarkan jendela terminal Ubuntu terbuka, atau
   - di PowerShell terpisah: `wsl -e sleep infinity` (biarkan berjalan; tutup bila selesai bekerja).

   Setelah WSL menyala lagi, container berpolicy `restart: unless-stopped` ikut hidup sendiri; cek dengan `docker compose ps`.
2. **Jalankan `docker compose` di dalam WSL**, pada folder repo. Folder Windows terlihat di WSL sebagai `/mnt/<huruf-drive>/...`
   (mis. `cd /mnt/d/kuliah/sem7/web/program/smart-poultry`). Python/venv boleh tetap di Windows.
3. **Sambungkan dari Windows lewat `localhost`**, bukan IP WSL. Selama WSL menyala, `localhost:5432` (juga `127.0.0.1`) dari Windows diteruskan ke container.
   **Jangan** memakai IP WSL (`172.x.x.x` dari `hostname -I`): IP itu berubah setiap WSL dinyalakan sehingga `.env` Anda tiba-tiba salah.
4. Bila menjalankan perintah WSL dari PowerShell dengan `wsl -e bash -c "..."` dan tanda kutip bertumpuk membingungkan, lebih mudah buka terminal Ubuntu dan jalankan perintah di sana.
5. **Container lama `postgres-light` / `docker run`.** Jika dulu Anda memulai database dengan `docker run` (mis. container bernama `postgres-light`), itu **berbeda** dari container compose (`smart-poultry-db`).
   Jangan menyalakan keduanya bersamaan pada port 5432. Dua pilihan:
   - **Tetap memakai container lama**: jangan jalankan `docker compose up`; pastikan container lama menyala (`docker start postgres-light`) dan `DATABASE_URL` menunjuk ke `localhost:5432`.
   - **Pindah ke compose**: `docker stop postgres-light`, jalankan compose, lalu pindahkan data
     (user/password container lama ada di `docker inspect postgres-light`, bagian `Env`):
     ```bash
     docker exec postgres-light pg_dump -U <user-lama> -d smart_poultry --no-owner --clean --if-exists > lama.sql
     docker compose exec -T db psql -U admin -d smart_poultry -q < lama.sql
     ```
     Container dan volume lama tidak dihapus oleh langkah ini; hapus sendiri bila sudah yakin.
6. Port 8000 (server API) bisa terpakai proses/container lain di WSL; bila `uvicorn` gagal mengikat port, pakai `--port 8001` ([bagian 9](#9-menjalankan-server)).

## 5. Lingkungan Python

Dari folder `smart-poultry-backend`:

```bash
cd smart-poultry-backend
python -m venv .venv
```

Aktifkan venv sesuai shell Anda:

| Shell | Perintah |
|---|---|
| PowerShell | `.venv\Scripts\Activate.ps1` (bila diblokir: `Set-ExecutionPolicy -Scope Process Bypass`) |
| cmd | `.venv\Scripts\activate.bat` |
| Git Bash | `source .venv/Scripts/activate` |
| macOS / Linux / WSL | `source .venv/bin/activate` |

Lalu pasang paket (termasuk pytest dan httpx):

```bash
pip install -r requirements-dev.txt
```
Prompt shell akan berawalan `(.venv)` bila venv aktif. Dependency produksi saja: `requirements.txt`.

> Versi `bcrypt` sengaja dibatasi `<4.1` di `requirements.txt` (kompatibilitas dengan `passlib`). Jangan menaikkannya tanpa menguji login dan `seed_admin.py`.

## 6. File `.env`

Masih di `smart-poultry-backend`:

```bash
cp .env.example .env          # PowerShell: Copy-Item .env.example .env
```

Hampir semua nilai bawaan sudah benar untuk lokal. Yang perlu dicek:

| Variabel | Arti | Catatan |
|---|---|---|
| `DATABASE_URL` | Alamat database kerja | Bawaan `...@localhost:5432/smart_poultry`. Ubah port bila memakai `POSTGRES_PORT` lain. **Host harus `localhost`**, bukan IP WSL |
| `TEST_DATABASE_URL` | Database untuk `pytest` (opsional) | Kosong = otomatis `smart_poultry_test` di server yang sama; **nama wajib berakhiran `_test`** |
| `JWT_SECRET` | Penanda token login | Ganti dengan string acak: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `DEVICE_HEARTBEAT_INTERVAL_SECONDS` | Interval heartbeat alat | 10 |
| `PERINTAH_TIMEOUT_*`, `ALAT_OFFLINE_AFTER_SECONDS` | Batas waktu perintah dan alat offline | Bawaan 60 / 300 / 0 (=3× heartbeat) |
| `SQL_ECHO` | Cetak SQL ke terminal | `true` hanya saat debugging |
| `CORS_ORIGINS` | Origin frontend yang diizinkan (JSON array) | Bawaan `localhost:5173` dan `:3000` |

## 7. Migrasi database

Membuat semua tabel:

```bash
alembic upgrade head
alembic current           # harus menampilkan revisi terbaru dengan tulisan (head)
```

Bila database baru/kosong, semua migrasi dijalankan berurutan. Setelah `git pull`, jalankan `alembic upgrade head` lagi bila ada migrasi baru.

<a id="data-demo"></a>
## 8. Data awal dan data demo

```bash
python seed_admin.py      # membuat Pemilik: admin@smartpoultry.com / admin123
python seed_demo.py       # master data, Kandang A + alat + 4 wadah berstok, siklus 100 ekor, Pekerja Budi
```

`seed_demo.py` aman dijalankan berulang: bila data demo sudah ada, ia dilewati.

Data demo yang dibuat: Pemilik `admin@smartpoultry.com` / `admin123`; Pekerja `budi@example.com` / `budi12345` (belum ditugaskan);
3 nutrisi, 4 bahan pakan beserta kandungannya, jenis ayam Broiler (fase Starter dan Grower dengan kebutuhan nutrisi dan standar konsumsi),
Kandang A dengan alat dan 4 wadah berstok, serta siklus aktif 100 ekor.

**`X-Device-Token`** alat hanya tampil sekali di output `seed_demo.py`. Bila terlewat, buat ulang lewat Swagger:
`POST /alat/{id}/rotasi-token` (ID alat tercetak di output seed).

Mulai dari data kosong lagi? Lihat [reset total](#reset-total).

## 9. Menjalankan server

```bash
uvicorn app.main:app --reload            # port 8000
uvicorn app.main:app --reload --port 8001   # bila 8000 terpakai
```

- Cek hidup: buka `http://localhost:8000/health` → `{"status":"ok"}`.
- Dokumentasi interaktif: `http://localhost:8000/docs` (Swagger). Klik **Authorize**, isi `username` = `admin@smartpoultry.com`, `password` = `admin123`.
- Alur uji manual lengkap: [smoke-test-swagger.md](smoke-test-swagger.md) dan [smoke-test-fase-1.md](smoke-test-fase-1.md).

## 10. Simulator alat

Dari root repo, di terminal lain (server harus menyala):

```bash
pip install -r simulator/requirements.txt       # cukup httpx; sudah ada bila memakai requirements-dev.txt
python simulator/run.py --device-token <TOKEN> --interval 3
```
Opsi dan skenario demo: [simulator.md](simulator.md). Bila server di port lain, tambahkan `--base-url http://localhost:8001`.

## 11. Menjalankan test

```bash
pytest -q
```

- Database test (`smart_poultry_test`) **dibuat otomatis** pada server yang sama; tidak ada langkah manual.
- Setiap sesi test menghapus seluruh schema database test lalu menjalankan semua migrasi dari nol, dan mengosongkan tabel antar test.
  Karena itu `tests/conftest.py` **menolak berjalan** bila nama database tidak berakhiran `_test` dan memeriksa bahwa koneksi benar-benar ke database `_test`.
  Data kerja Anda di `smart_poultry` tidak tersentuh.
- Jangan menimpa `TEST_DATABASE_URL` dengan database berisi data penting.
- Bila server database tidak terjangkau, `pytest` berhenti dalam ±5 detik dengan pesan `Tidak bisa tersambung ke Postgres ...` (di jalur B: cek [sesi WSL](#khusus-jalur-b-docker-di-wsl-ubuntu)).
- Satu file: `pytest tests/test_alur_inti.py -q`; satu test: `pytest -k nama_test -q`.

## 12. Berbagi data tanpa database bersama

Perlu memberi anggota lain dataset yang sama dengan Anda? Kirim berkas dump (jangan di-commit ke Git; berisi data dan hash kata sandi).
Letakkan di folder `backups/` (sudah di-`.gitignore`). Jalankan dari root repo (di jalur B: dalam WSL):

```bash
mkdir -p backups

# Membuat dump (pengirim)
docker compose exec -T db pg_dump -U admin -d smart_poultry --no-owner --clean --if-exists > backups/data.sql

# Memuat dump (penerima; menimpa isi database kerja!)
docker compose exec -T db psql -U admin -d smart_poultry -q < backups/data.sql
alembic current          # pastikan revisi migrasi cocok dengan kode Anda; bila perlu: alembic upgrade head
```
- Dump membawa tabel `alembic_version`; penerima sebaiknya `git pull` ke commit yang sama (atau lebih baru, lalu `alembic upgrade head`) sebelum memuat.
- Memuat dump ke database lain (aman untuk mencoba): `docker compose exec -T db psql -U admin -d postgres -c "CREATE DATABASE coba"`, lalu muat dengan `-d coba`.

<a id="reset-total"></a>
**Reset total** (mulai dari nol, menghapus semua data lokal):

```bash
docker compose down -v          # -v menghapus volume berisi data
docker compose up -d            # tunggu healthy
cd smart-poultry-backend
alembic upgrade head
python seed_admin.py && python seed_demo.py
```

## 13. Alur kerja tim

- **Branch**: satu fitur/perbaikan = satu branch (`fitur/...`, `fix/...`, `docs/...`) dari `main` terbaru, lalu Pull Request. Jangan push langsung ke `main`.
- **Sebelum mulai**: `git pull` di `main`, lalu `alembic upgrade head` (mungkin ada migrasi baru dari anggota lain).
- **Mengubah model/tabel** (hanya bila memang diminta; lihat aturan di [AGENTS.md](AGENTS.md)):
  1. Ubah file di `app/models/`.
  2. `alembic revision --autogenerate -m "deskripsi"`, **baca hasilnya** (nama constraint kosong, enum, dan data lama sering perlu disesuaikan).
  3. `alembic upgrade head`, lalu `alembic revision --autogenerate -m cek` harus menghasilkan migrasi kosong (hapus file hasil cek itu).
  4. Jalankan `pytest -q`.
- **Jangan mengedit migrasi yang sudah di-merge ke `main`**; buat migrasi baru.
- **Dua orang membuat migrasi bersamaan** → `alembic heads` menampilkan lebih dari satu head. Setelah `git pull`, selesaikan dengan `alembic merge -m "gabung head" <head1> <head2>`.
- **Jangan commit**: `.env`, `.venv/`, `backups/`, berkas dump, token alat.
- **Sebelum PR**: `pytest -q` hijau; dokumen yang terdampak (`docs/spesifikasi/API_CONTRACT.md`, dll.) ikut diperbarui.
- Peringatan Git `LF will be replaced by CRLF` di Windows tidak berbahaya.

## 14. Daftar centang setup berhasil

- [ ] `docker compose ps` menampilkan `smart-poultry-db` berstatus **healthy**.
- [ ] `alembic current` menampilkan `... (head)`.
- [ ] `python seed_admin.py` dan `python seed_demo.py` selesai tanpa galat.
- [ ] `http://localhost:8000/health` menjawab `{"status":"ok"}`.
- [ ] Login di `/docs` dengan `admin@smartpoultry.com` / `admin123` berhasil (`GET /auth/me` → 200).
- [ ] `pytest -q` lulus semua (jumlah test tertera di akhir; tidak ada yang merah).
- [ ] (Opsional) `python simulator/run.py --device-token <TOKEN> --once` terhubung (log "Simulator berjalan").

## 15. Troubleshooting

| Gejala | Penyebab | Solusi |
|---|---|---|
| `alembic`, `seed_*`, atau `pytest` **menggantung** lama tanpa keluaran (jalur B) | WSL berhenti karena idle sehingga database mati | Nyalakan lagi WSL dan jaga satu sesi tetap terbuka ([jalur B](#khusus-jalur-b-docker-di-wsl-ubuntu)); `docker compose ps` |
| `connection refused` / `Tidak bisa tersambung ke Postgres` | Database belum menyala, port salah, atau Docker/WSL mati | `docker compose ps`; cek port di `DATABASE_URL` sama dengan `POSTGRES_PORT`; nyalakan Docker |
| Dulu bisa, sekarang tidak bisa tersambung (jalur B) | `.env` memakai IP WSL (`172.x`) yang berubah | Ganti host menjadi `localhost` |
| `password authentication failed for user "admin"` | Volume lama dibuat dengan password berbeda | Bila data boleh hilang: `docker compose down -v` lalu `up -d` (hapus data!). Bila tidak: samakan password di `.env` dengan volume lama |
| `port is already allocated` / `address already in use` (5432) | Postgres/container lain memakai port itu | Pakai `POSTGRES_PORT` lain ([bagian 4](#4-menjalankan-database-docker)) atau hentikan yang lain |
| `uvicorn` gagal mengikat port 8000 | Port dipakai proses lain | `uvicorn app.main:app --port 8001` |
| `[WinError 206] The filename or extension is too long` saat `pip install` | Path folder proyek terlalu dalam (Windows) | Pindahkan/clone proyek ke path pendek (mis. `C:\dev\...`), buat ulang venv |
| `ValueError: password cannot be longer than 72 bytes` saat seed/login | `bcrypt` versi terlalu baru dengan `passlib` | `pip install -r requirements.txt` ulang (bcrypt dibatasi `<4.1`) |
| `'alembic' is not recognized` / `command not found` | venv belum aktif atau paket belum terpasang | Aktifkan venv ([bagian 5](#5-lingkungan-python)); `pip install -r requirements-dev.txt` |
| `ModuleNotFoundError: No module named 'app'` | Perintah dijalankan bukan dari `smart-poultry-backend` | `cd smart-poultry-backend` |
| `Target database is not up to date` | Database belum di revisi terbaru saat membuat migrasi | `alembic upgrade head` dulu |
| `alembic heads` menampilkan lebih dari satu | Dua branch membuat migrasi sendiri-sendiri | `alembic merge -m "gabung head" <head1> <head2>` |
| `relation "..." does not exist` | Migrasi belum dijalankan | `alembic upgrade head` |
| `RuntimeError: Nama database test harus berakhiran '_test'` | `TEST_DATABASE_URL` menunjuk ke database yang bukan `*_test` | Perbaiki nama, atau kosongkan variabel itu |
| Login `/docs` gagal 401 | `seed_admin.py` belum dijalankan atau database di-reset | `python seed_admin.py` |
| `POST /kandang/{id}/perintah/beri-makan` → 409 "Alat sedang OFFLINE" | Belum ada heartbeat dari alat | Jalankan simulator atau panggil `/device/heartbeat` |
| Peringatan `LF will be replaced by CRLF` | Normal di Windows | Abaikan |

Bila masih macet, kumpulkan keluaran `docker compose ps`, `alembic current`, dan pesan galat lengkap, lalu tanyakan ke tim.

## 16. Cheat sheet harian

```bash
# mulai bekerja
docker compose up -d                 # root repo
cd smart-poultry-backend && source .venv/bin/activate   # Windows: .venv\Scripts\activate
git pull && alembic upgrade head
uvicorn app.main:app --reload

# selesai bekerja
docker compose stop                  # data tetap; `down` juga aman, `down -v` MENGHAPUS data

# berguna
pytest -q                            # semua test
alembic current                      # revisi database saat ini
docker compose exec db psql -U admin -d smart_poultry    # masuk psql
docker compose logs -f db            # log database
```

## 17. Status pengujian panduan

Panduan ini diuji 2 November 2026 dengan simulasi "anggota baru": clone bersih, venv baru, `pip install -r requirements-dev.txt`,
Docker Engine di WSL Ubuntu 24.04 (jalur B) dengan proyek compose terpisah, `alembic upgrade head` dari database kosong, `seed_admin.py`, `seed_demo.py` (dua kali),
`uvicorn` + `/health` + login, `pytest -q` (99 test lulus, database test dibuat otomatis, data database kerja tetap utuh), serta `pg_dump` dan restore ke database lain maupun di atas data yang sama.
Simulasi itu menemukan dan memperbaiki: pembatasan `bcrypt`, pembuatan database test otomatis, dan penyebab menggantungnya perintah (WSL idle).

**Belum diuji**: jalur A (Docker Desktop) dan jalur C (Linux native), serta macOS; langkahnya mengikuti perilaku standar Docker dan Python.
Bila ada langkah yang tidak cocok di komputer Anda, perbaiki panduan ini lewat Pull Request.
