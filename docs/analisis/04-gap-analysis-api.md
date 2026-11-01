# 04 — Gap Analysis: Kontrak API vs Implementasi

Sumber kontrak: [`../spesifikasi/API_CONTRACT.md`](../spesifikasi/API_CONTRACT.md). Implementasi: `smart-poultry-backend/app/routers/`.
> **Pembaruan 1 Nov 2026:** baris yang merujuk T-1, T-2, T-3, T-5..T-12, K-1..K-3 dan S-5/S-9/S-14 sudah diperbaiki
> (lihat [03](03-review-kode.md)); baris tersebut kini berstatus ✅ kecuali dicatat lain. Masih ❌/⚠️: template (BR-13), paginasi,
> S-1, S-4, S-6, S-7, S-15, T-4.

Legenda: ✅ sesuai · ⚠️ ada tapi menyimpang/berisiko (rujuk ID temuan di [03](03-review-kode.md)) · ❌ belum ada.

| # | Bagian kontrak | Endpoint | Status | Catatan |
|---|---|---|---|---|
| 1 | Auth | `POST /auth/login` | ⚠️ | S-11 (NONAKTIF, rate-limit) |
| | | `GET /auth/me` | ✅ | |
| | | `POST /auth/ganti-kata-sandi` | ✅ | Tidak menghapus status `WAJIB_GANTI_SANDI` setelah ganti (S-11) |
| 2 | User | `POST /users` | ✅ | |
| | | `GET /users` | ⚠️ | T-3: mengembalikan semua Pekerja sistem |
| | | `PATCH /users/{id}/status` | ⚠️ | T-3 |
| | | `POST /users/{id}/penugasan` | ⚠️ | T-1 |
| | | `DELETE /penugasan/{id}` | ⚠️ | T-2 |
| 3 | Kandang & Alat | `POST/GET /kandang`, `GET/PATCH /kandang/{id}` | ✅ | Detail memuat `status_alat`, `siklus_aktif_*`; belum memuat alat/wadah lengkap (S) |
| | | `POST /kandang/{id}/alat` | ✅ | Token tampil sekali; disimpan plaintext (diterima untuk MVP) |
| | | `POST /alat/{id}/rotasi-token` | ✅ | |
| | | `POST /alat/{id}/wadah` | ⚠️ | T-6 (Stok tak dibuat), T-12 |
| | | `PATCH /wadah/{id}` | ⚠️ | T-12 (tak bisa melepas bahan) |
| | | (tidak di kontrak) `GET alat/wadah` | ❌ | UI butuh daftar wadah per kandang → usulkan tambah `GET /kandang/{id}/alat` (perlu persetujuan karena di luar kontrak) |
| 4 | Master data | CRUD jenis-ayam, fase, nutrisi, bahan-pakan | ✅/⚠️ | Tanpa paginasi (S-8); DELETE → 500 saat direferensikan (S-15); filter `?jenis_ayam_id=` untuk Fase berbentuk path `/jenis-ayam/{id}/fase` |
| | | `PUT /fase/{id}/standar-konsumsi` | ✅ | |
| | | `PUT /bahan-pakan/{id}/nutrisi` | ✅ | |
| | | `PUT /fase/{id}/kebutuhan-nutrisi` | ✅ | |
| | | `GET /template/jenis-ayam` | ❌ | BR-13 |
| | | `POST /template/jenis-ayam/{id}/salin` | ❌ | BR-13; butuh sumber template (seed data/JSON statis, bukan tabel baru) |
| 5 | Siklus & populasi | `POST /kandang/{id}/siklus` | ⚠️ | S-7 |
| | | `GET /kandang/{id}/siklus/aktif` | ✅ | |
| | | `PATCH /siklus/{id}/fase` | ⚠️ | Logika ada tetapi crash (K-2); tidak membuat notifikasi `PERLU_DITINJAU` (T-11) |
| | | `POST /siklus/{id}/populasi` | ⚠️ | S-6 |
| | | `POST /siklus/{id}/selesai` | ⚠️ | K-2 |
| 6 | Formulasi | `POST /siklus/{id}/formulasi/otomatis` | ⚠️ | K-1, S-1, S-5; harga kosong → 409 ✅ |
| | | `POST /siklus/{id}/formulasi/manual` | ⚠️ | K-1; salah validasi total proporsi → 400 (kontrak: 400 validasi ✅) |
| | | `POST /formulasi` | ⚠️ | K-2, T-4; cek bahan dilepas → 409 ✅ |
| | | `GET /siklus/{id}/formulasi`, `GET /formulasi/{id}` | ✅ | `FormulasiLengkapPublic` belum memuat `nama_bahan`/`nama_nutrisi` (kontrak menyebut item lengkap) |
| 7 | Perintah | `POST /kandang/{id}/perintah/beri-makan` | ⚠️ | T-5, T-7, T-8; 409 offline/aktif ✅ |
| | | `POST /kandang/{id}/perintah/stop-darurat` | ⚠️ | T-9 |
| | | `GET /perintah/{id}`, `GET /kandang/{id}/perintah` | ✅ | |
| 8 | Device | `POST /device/heartbeat` | ⚠️ | S-9, T-7; token tidak valid → 401 ✅ |
| | | `POST /device/perintah/{id}/ambil` / `mulai` | ⚠️ | T-9 |
| | | `POST /device/perintah/{id}/log` | ⚠️ | K-3, T-10 |
| 9 | Stok | `GET /kandang/{id}/stok` | ⚠️ | T-6 |
| | | `POST isi-ulang`, `POST koreksi`, `GET transaksi` | ✅ | Koreksi mewajibkan `alasan` (422) ✅; tidak menulis `AuditLog` (S-14); Pekerja boleh koreksi (kontrak tidak membatasi) |
| 10 | Notifikasi | `GET /notifikasi`, `PATCH baca`, `PATCH baca-semua` | ✅ | Fungsi ada; **pemicu** notifikasi minim (T-11) |
| — | Umum | Paginasi `skip/limit` | ❌ | S-8 |
| — | Umum | Format error `{"detail"}` + 409 untuk aturan bisnis | ⚠️ | Beberapa aturan bisnis memakai 400 (mis. alat belum ada) – pilih konsisten |

## Ringkasan angka (berdasarkan baris di atas)
- Endpoint kontrak total ±55; **sesuai penuh ≈ 60%**, **ada tetapi bermasalah ≈ 35%**, **belum ada ≈ 5%** (2 endpoint template + paginasi).
- Semua masalah ⚠️ berpusat di 3 area: formulasi/enum (K-1..K-3), otorisasi lintas-pemilik (T-1..T-3, T-12), dan siklus hidup perintah/alat (T-5..T-11).
