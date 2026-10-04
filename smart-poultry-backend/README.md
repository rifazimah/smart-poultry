# Smart Poultry — Backend (MVP)

Cakupan: formulasi pakan (LP otomatis + manual) dan kontrol pakan manual
lewat simulator alat. **Tidak termasuk** penjadwalan otomatis, alur
persetujuan Pekerja, dan Role/Permission dinamis (ditunda ke Fase 2).

Lihat `API_CONTRACT.md` di root repo untuk daftar lengkap endpoint.

## 1. Persiapan

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # lalu sesuaikan DATABASE_URL ke container Postgres Anda
```

## 2. Buat database (sekali saja)

Container Postgres Alpine Anda sudah jalan tapi database `smart_poultry`
belum ada. Buat dulu:

```bash
docker exec -it <nama_container_postgres> psql -U postgres -c "CREATE DATABASE smart_poultry;"
```

## 3. Jalankan migrasi pertama

```bash
alembic revision --autogenerate -m "init schema mvp"
alembic upgrade head
```

Setiap kali model di `app/models/` diubah, ulangi dua baris di atas untuk
membuat & menjalankan migrasi baru — jangan edit tabel manual lewat SQL.

## 4. Jalankan server

```bash
uvicorn app.main:app --reload
```

Cek di `http://localhost:8000/health` → harus mengembalikan `{"status": "ok"}`.
Dokumentasi interaktif otomatis tersedia di `http://localhost:8000/docs`
(FastAPI generate dari kode, akan terisi seiring router ditambahkan).

## Struktur folder

```
app/
  models/
    enums.py        -> semua enum (status, tipe, dsb.)
    akses.py        -> User, PenugasanKandang, AuditLog
    fisik.py        -> Kandang, Alat, Wadah, Stok, TransaksiStok
    masterdata.py    -> Nutrisi, BahanPakan, JenisAyam, Fase, dst.
    operasional.py   -> SiklusKandang, Formulasi, Perintah, LogEksekusi, Notifikasi
  database.py        -> engine & session
  config.py          -> baca .env
  main.py            -> entrypoint FastAPI
alembic/              -> migrasi skema
API_CONTRACT.md        -> acuan endpoint (baca sebelum menambah router baru)
```
