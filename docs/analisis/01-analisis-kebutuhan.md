# 01 — Analisis Kebutuhan (perspektif System Analyst)

Sumber: [PRD-MVP](../spesifikasi/PRD-MVP.md), [ARCHITECTURE](../spesifikasi/ARCHITECTURE.md), [API_CONTRACT](../spesifikasi/API_CONTRACT.md), kode backend.

## 1. Latar belakang & tujuan
Peternak menghitung komposisi pakan secara manual: lambat, rawan salah, tidak efisien biaya. Smart Poultry mengotomasi
(1) perhitungan formulasi pakan berbasis kebutuhan nutrisi per fase pertumbuhan dengan biaya minimum (Linear Programming) dan
(2) pengeluaran pakan lewat alat IoT (di MVP: simulator).

**Definisi selesai MVP (PRD):** Pemilik login → buat kandang & alat → isi master data → mulai siklus → formulasi otomatis
(memenuhi nutrisi, biaya tampil) → beri makan → simulator melapor → stok berkurang, riwayat & notifikasi tercatat.

## 2. Aktor & pemangku kepentingan
| Aktor | Peran | Hak utama |
|---|---|---|
| Pemilik | Peternak pemilik kandang | Master data, kandang/alat/wadah, akun & penugasan Pekerja, formulasi, perintah, stok |
| Pekerja | Petugas harian | Hanya kandang yang ditugaskan: lihat, siklus/populasi, beri makan, stok |
| Simulator Alat | Sistem eksternal | Heartbeat, ambil/mulai perintah, kirim log (token perangkat) |
| Tim pengembang | Internal | Mengelola migrasi, seed, deployment demo |
Di luar cakupan MVP: Super Admin, role dinamis, penjadwalan, notifikasi eksternal (Fase 2).

## 3. Use case (rujukan UC dari kontrak)
| UC | Nama | Aktor | Prasyarat | Hasil |
|---|---|---|---|---|
| UC-01 | Login/ganti sandi | Pemilik, Pekerja | Akun aktif | JWT |
| UC-02 | Kelola akun & penugasan Pekerja | Pemilik | Login | Pekerja punya akses kandang |
| UC-03 | Kelola kandang | Pemilik | — | Kandang terdaftar |
| UC-04 | Daftarkan alat & wadah | Pemilik | Kandang | `device_token`, wadah ↔ bahan |
| UC-05 | Kelola master data nutrisi | Pemilik | — | Nutrisi, bahan, jenis ayam, fase, kebutuhan, standar |
| UC-06 | Siklus & populasi | Pemilik, Pekerja | Master data + kandang | Siklus aktif, riwayat populasi |
| UC-07 | Formulasi pakan (otomatis/manual) | Pemilik (±Pekerja) | Alat+wadah+bahan berharga+kebutuhan fase | Preview → snapshot tersimpan |
| UC-08 | Beri makan manual | Pemilik, Pekerja | Formulasi valid, alat online, stok cukup | Perintah → log → stok turun |
| UC-12 | Kelola stok | Pemilik, Pekerja | Wadah | Isi ulang / koreksi / riwayat |
| UC-xx | Notifikasi dalam aplikasi | Semua | — | Daftar & status baca |
| UC-09 | Penjadwalan | — | — | **Ditunda Fase 2** |

## 4. Kebutuhan fungsional → status implementasi
| ID | Kebutuhan | Prioritas | Endpoint/modul | Status |
|---|---|---|---|---|
| FR-01 | Autentikasi JWT dua peran | Must | `routers/auth.py` | ✅ |
| FR-02 | CRUD master data (5 resource) terscope per Pemilik | Must | `routers/masterdata.py` | ✅ (paginasi ❌) |
| FR-03 | Template jenis ayam bawaan + salin (BR-13) | Should | — | ❌ |
| FR-04 | Kandang, alat (token sekali), wadah↔bahan | Must | `routers/kandang.py` | ⚠️ |
| FR-05 | Siklus & perubahan populasi | Must | `routers/siklus.py` | ⚠️ (crash saat akhiri/pindah fase) |
| FR-06 | Formulasi otomatis LP (min biaya) | **Must (inti)** | `services/formulasi.py` | ⚠️ (crash enum) |
| FR-07 | Formulasi manual + validasi nutrisi | Must | idem | ⚠️ (crash enum) |
| FR-08 | Simpan snapshot formulasi | Must | `POST /formulasi` | ⚠️ |
| FR-09 | Beri makan manual + status perintah | **Must** | `routers/perintah.py`, `device.py` | ⚠️ |
| FR-10 | Stop darurat | Should | `perintah.py` | ⚠️ (tanpa efek) |
| FR-11 | Stok: estimasi dari log, isi ulang, koreksi beralasan | Must | `routers/stok.py`, `services/device.py` | ⚠️ |
| FR-12 | Notifikasi dasar (sukses/gagal, stok menipis, alat offline, perlu ditinjau) | Must | `routers/notifikasi.py` | ⚠️ (pemicu minim) |
| FR-13 | Audit perubahan penting | Could | `AuditLog` | ❌ tak terisi |
| FR-14 | Simulator alat | **Must (untuk demo)** | — | ❌ belum dibuat |
| FR-15 | Antarmuka React | Must (untuk demo) | — | ❌ belum dibangun |

## 5. Kebutuhan non-fungsional
| ID | Kategori | Kebutuhan | Kondisi saat ini |
|---|---|---|---|
| NFR-01 | Keamanan | Hash bcrypt, tak ada hash di response, isolasi data antar Pemilik | Hash ✅; isolasi ⚠️ (T-1..T-3, T-12) |
| NFR-02 | Keamanan | Token alat terpisah dari JWT | ✅ |
| NFR-03 | Keandalan | Idempotensi log alat; TIMEOUT; deteksi offline | ⚠️ |
| NFR-04 | Kinerja | Polling 1–2 dtk UI, heartbeat 10 dtk; LP < 1 dtk (≤ ±10 bahan) | Memadai untuk skala MVP; belum diukur |
| NFR-05 | Maintainability | Layering, migrasi Alembic, konvensi | ✅; test ❌ |
| NFR-06 | Operabilitas | Setup 1 perintah (compose) , env jelas | DB ✅; backend/CI ❌ |
| NFR-07 | Portabilitas | Berjalan di Windows/WSL/Linux, Python ≥3.11 | ✅ |
| NFR-08 | Kegunaan | UI bahasa Indonesia, pesan error jelas | Pesan API ID ✅ |

## 6. Aturan bisnis yang terlacak di kode
| BR | Aturan | Lokasi | Status |
|---|---|---|---|
| BR-02/03 | Pemilik membuat Pekerja; penugasan ke kandang | `users.py` | ⚠️ (T-1..T-3) |
| BR-08 | Harga wajib untuk mode otomatis | `formulasi.py` (409) | ✅ |
| BR-09 | Total proporsi = 1, hanya bahan terpasang di wadah | `formulasi.py` | ✅ |
| BR-11 | Infeasible → 200 `TIDAK_SEMPURNA` + daftar nutrisi gagal | `formulasi.py` | ⚠️ (S-1) |
| BR-13 | Template referensi | — | ❌ |
| BR-14 | `berat_per_sesi = proporsi × gram/ekor/hari × populasi ÷ frekuensi` | `formulasi.py` | ✅ |
| BR-24/26 | Satu perintah aktif per alat, alat online | `perintah.py` | ⚠️ (T-7, T-8) |
| BR-34 | Koreksi stok wajib alasan + teraudit | `stok.py` | ⚠️ (audit ❌) |

## 7. Asumsi, batasan, dan keputusan terbuka
- Alat fisik di luar cakupan; simulator dianggap selalu terhubung (PRD) — namun backend tetap perlu logika offline/timeout agar demo tidak "macet".
- Tidak ada WebSocket, Redis, Celery (keputusan final). Konsekuensi: deteksi offline/timeout dilakukan *lazy* (saat request).
- Satuan nutrisi tidak dinormalisasi: pengguna bertanggung jawab konsisten (disarankan validasi/penjelasan di UI).
- Terbuka: platform hosting demo; apakah simulator dideploy online; state management React (lihat [05](05-risiko-dan-technical-debt.md)).

## 8. Matriks keterlacakan ringkas (PRD → hasil)
| Item cakupan MVP (PRD) | Kebutuhan | Selesai? |
|---|---|---|
| 1 Akun & autentikasi | FR-01 | Ya (perbaikan T-3 pending) |
| 2 Kandang, alat, wadah | FR-04 | Sebagian |
| 3 Master data | FR-02, FR-03 | Sebagian (template ❌) |
| 4 Siklus & populasi | FR-05 | Sebagian |
| 5 Formulasi | FR-06..08 | Tidak berfungsi sampai K-1/K-2 diperbaiki |
| 6 Beri makan manual | FR-09, FR-10, FR-14 | Tidak (simulator ❌, K-3) |
| 7 Stok | FR-11 | Sebagian |
| 8 Notifikasi | FR-12 | Sebagian |
