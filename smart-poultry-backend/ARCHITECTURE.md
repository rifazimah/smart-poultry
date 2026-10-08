# Architecture — Smart Poultry (MVP)

Dokumen ini menjelaskan **bentuk sistem**, bukan aturan penulisan kode
(itu ada di CONVENTIONS.md) dan bukan daftar endpoint (itu di
API_CONTRACT.md).

## Komponen sistem

```
┌─────────────┐      HTTP + JWT       ┌──────────────────┐
│  React App   │ ───────────────────▶ │   FastAPI Backend │
│  (frontend)  │ ◀─────────────────── │   (repo ini)       │
└─────────────┘                       └─────────┬─────────┘
                                                 │
                                       SQLModel  │  (Alembic migrasi)
                                                 ▼
                                       ┌───────────────────┐
                                       │  PostgreSQL         │
                                       │  (container Alpine, │
                                       │   sudah jalan lokal)│
                                       └───────────────────┘
                                                 ▲
                                       HTTP + X-Device-Token
                                                 │
                                       ┌───────────────────┐
                                       │ Simulator Alat IoT  │
                                       │ (skrip Python       │
                                       │  terpisah, polling)│
                                       └───────────────────┘
```

**4 komponen berjalan terpisah**, tidak saling import kode:
1. **React App** — belum dibangun di fase ini (menyusul).
2. **FastAPI Backend** — repo ini. Satu-satunya yang bicara ke database.
3. **PostgreSQL** — sudah jalan di container Alpine lokal (bukan tanggung
   jawab repo ini untuk menjalankannya, cuma konek lewat `DATABASE_URL`).
4. **Simulator Alat** — repo/folder **terpisah** di luar
   `smart-poultry-backend/`, dijalankan manual (`python run.py`) saat
   testing. Ini BUKAN bagian dari backend FastAPI, dan tidak boleh
   di-import sebagai modul backend.

## Dua jalur autentikasi — jangan dicampur

| Jalur | Dipakai oleh | Mekanisme | Endpoint |
|---|---|---|---|
| **JWT** | React App (manusia: Pemilik/Pekerja) | `Authorization: Bearer <token>`, didapat dari `/auth/login` | Semua endpoint di API_CONTRACT.md kecuali bagian 8 |
| **Device Token** | Simulator Alat | `X-Device-Token: <token>`, didapat sekali saat `POST /kandang/{id}/alat` | Hanya endpoint `/device/*` (bagian 8 di API_CONTRACT.md) |

Kedua jalur ini **tidak saling bisa dipakai gantian**. Endpoint `/device/*`
tidak boleh menerima JWT, endpoint manusia tidak boleh menerima device
token. Ini dicek lewat dependency FastAPI berbeda
(`get_current_user` vs `get_current_device`).

## Alur data: dari formulasi sampai pakan keluar

1. React (sebagai Pemilik) panggil `POST /siklus/{id}/formulasi/otomatis`
   → backend hitung LP → balas preview (belum tersimpan).
2. React panggil `POST /formulasi` dengan hasil preview → backend simpan
   snapshot ke tabel `formulasi` + `formulasi_item` + `formulasi_nutrisi_hasil`.
3. React panggil `POST /kandang/{id}/perintah/beri-makan` → backend buat
   baris `perintah` status `PENDING`.
4. Simulator Alat polling `POST /device/heartbeat` tiap beberapa detik →
   dapat balasan berisi perintah `PENDING` tadi.
5. Simulator panggil `/device/perintah/{id}/ambil` →`/mulai` → (simulasi
   delay proses fisik) → `/log` dengan hasil akhir.
6. Backend, saat menerima `/log`: update status `perintah`, kurangi
   `stok`, catat `transaksi_stok`, buat `notifikasi`.
7. React, yang sejak langkah 3 melakukan polling `GET /perintah/{id}`
   tiap 1-2 detik, melihat status berubah jadi `SUKSES`/`GAGAL` dan
   update tampilan.

Tidak ada WebSocket/real-time push di MVP ini — semuanya polling biasa.
Jangan menambahkan WebSocket kecuali diminta eksplisit (lihat prinsip
KISS di AGENTS.md).

## Lingkungan (environment)

| Lingkungan | Tujuan | Database |
|---|---|---|
| **Lokal** | Development sehari-hari | Container PostgreSQL Alpine yang sudah jalan, lewat `.env` |
| **Demo** | Presentasi/testing bersama teman, akhir bulan | Satu deployment sederhana (Railway/Render/Fly.io — belum dipilih final), PostgreSQL managed dari platform yang sama |

Tidak ada staging/CI-CD bertingkat untuk MVP ini — ini keputusan sadar
karena waktu 1 bulan (lihat diskusi tim), bukan sesuatu yang "belum
sempat dikerjakan". Jangan membangun pipeline CI/CD kecuali diminta.

## Keputusan teknis yang sudah final (jangan diganti tanpa konfirmasi)

- **ORM**: SQLModel (bukan SQLAlchemy mentah, bukan Django ORM)
- **Migrasi**: Alembic, selalu lewat `--autogenerate`, tidak pernah SQL manual
- **LP solver**: `scipy.optimize.linprog` (lihat detail constraint di CONVENTIONS.md)
- **Auth manusia**: JWT (python-jose) + password hashing bcrypt (passlib)
- **Auth alat**: token string statis per alat, dikirim lewat header kustom
- **Tidak ada caching layer** (Redis, dsb.) — skala data MVP ini kecil, tidak perlu
- **Tidak ada background job queue** (Celery, dsb.) — semua operasi MVP cukup cepat untuk dijalankan langsung di request/response

## Yang BELUM diputuskan (jangan agent putuskan sendiri)

- Platform hosting demo final (Railway vs Render vs Fly.io)
- Struktur state management di React (akan ditentukan saat frontend mulai)
- Apakah simulator alat juga di-deploy online saat demo, atau cukup
  dijalankan lokal saat presentasi langsung
