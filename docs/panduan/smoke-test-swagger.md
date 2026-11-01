# Skenario Smoke Test via Swagger UI

Tujuan: membuktikan alur inti MVP berjalan tanpa error 500 setelah perbaikan Fase 0 (K-1, K-2, K-3), dan
mengonfirmasi temuan yang belum diperbaiki (mis. T-6). Waktu: ±30–45 menit. Acuan temuan: [03-review-kode](../analisis/03-review-kode.md).

## 0. Persiapan

```bash
# dari root repo
docker compose up -d
docker compose ps                       # db harus "healthy"

cd smart-poultry-backend
.venv\Scripts\activate                  # Windows
alembic upgrade head                    # harus sukses sampai revisi b7c1a2d93e5f
alembic revision --autogenerate -m "cek drift"   # HARUS menghasilkan migrasi kosong; hapus file hasilnya
python seed_admin.py                    # membuat admin@smartpoultry.com / admin123
uvicorn app.main:app --reload
```
Buka `http://localhost:8000/docs`. Cek `GET /health` → `{"status":"ok"}`.

**Tips kerja**
- Siapkan Notepad untuk mencatat ID: `nutrisi_protein`, `nutrisi_energi`, `nutrisi_kalsium`, `jagung`, `kedelai`, `dedak`, `kapur`, `jenis_ayam`, `fase_starter`, `fase_grower`, `kandang`, `alat`, `device_token`, `wadah1..4`, `siklus`, `formulasi`, `perintah`.
- Di Swagger: klik endpoint → **Try it out** → isi → **Execute**. Lihat *Server response* (kode + body).
- Path `{id}` diisi ID dari catatan. Bila body ada UUID, ganti `<...>` dengan ID asli.
- Semua path di bawah diawali `/api/v1`, Swagger sudah menambahkannya otomatis.

## 1. Login (UC-01)

| # | Aksi | Input | Harapan |
|---|---|---|---|
| 1.1 | Klik **Authorize** (gembok kanan atas) | `username`: `admin@smartpoultry.com`, `password`: `admin123` → Authorize → Close | Gembok tertutup |
| 1.2 | `GET /auth/me` | — | 200, `role: PEMILIK`, **tidak ada** `kata_sandi_hash` |
| 1.3 | `POST /auth/login` | `{"email":"admin@smartpoultry.com","kata_sandi":"salah"}` | 401 `Email atau kata sandi salah` |

## 2. Master data nutrisi (UC-05)

Satuan: protein & kalsium dalam **%**, energi dalam **kkal/kg**. Nilai bahan harus memakai satuan yang sama dengan batas kebutuhan.

| # | Endpoint | Body | Catat |
|---|---|---|---|
| 2.1 | `POST /nutrisi` | `{"nama":"Protein","satuan":"%","tipe_batas":"MIN_MAKS"}` | 201 → `nutrisi_protein` |
| 2.2 | `POST /nutrisi` | `{"nama":"Energi Metabolis","satuan":"kkal/kg","tipe_batas":"MINIMUM"}` | `nutrisi_energi` |
| 2.3 | `POST /nutrisi` | `{"nama":"Kalsium","satuan":"%","tipe_batas":"MIN_MAKS"}` | `nutrisi_kalsium` |
| 2.4 | `POST /bahan-pakan` | `{"nama":"Jagung","harga":5000}` | `jagung` |
| 2.5 | `POST /bahan-pakan` | `{"nama":"Bungkil Kedelai","harga":9000}` | `kedelai` |
| 2.6 | `POST /bahan-pakan` | `{"nama":"Dedak","harga":3000}` | `dedak` |
| 2.7 | `POST /bahan-pakan` | `{"nama":"Tepung Batu","harga":1000,"batas_maksimum":0.05}` | `kapur` |

Kandungan nutrisi per bahan — `PUT /bahan-pakan/{id}/nutrisi` (200, array hasil):

| Bahan | Body |
|---|---|
| Jagung | `[{"nutrisi_id":"<protein>","nilai_per_kg":8.5},{"nutrisi_id":"<energi>","nilai_per_kg":3350},{"nutrisi_id":"<kalsium>","nilai_per_kg":0.02}]` |
| Kedelai | `[{"nutrisi_id":"<protein>","nilai_per_kg":44},{"nutrisi_id":"<energi>","nilai_per_kg":2400},{"nutrisi_id":"<kalsium>","nilai_per_kg":0.3}]` |
| Dedak | `[{"nutrisi_id":"<protein>","nilai_per_kg":12},{"nutrisi_id":"<energi>","nilai_per_kg":1800},{"nutrisi_id":"<kalsium>","nilai_per_kg":0.1}]` |
| Tepung Batu | `[{"nutrisi_id":"<protein>","nilai_per_kg":0},{"nutrisi_id":"<energi>","nilai_per_kg":0},{"nutrisi_id":"<kalsium>","nilai_per_kg":38}]` |

## 3. Jenis ayam, fase, kebutuhan, standar konsumsi

| # | Endpoint | Body | Catat |
|---|---|---|---|
| 3.1 | `POST /jenis-ayam` | `{"nama":"Broiler"}` | `jenis_ayam` |
| 3.2 | `POST /jenis-ayam/{jenis_ayam}/fase` | `{"nama":"Starter","umur_min_hari":0,"umur_max_hari":14}` | `fase_starter` |
| 3.3 | `POST /jenis-ayam/{jenis_ayam}/fase` | `{"nama":"Grower","umur_min_hari":15,"umur_max_hari":28}` | `fase_grower` |
| 3.4 | `PUT /fase/{fase_starter}/kebutuhan-nutrisi` | `[{"nutrisi_id":"<protein>","batas_min":20,"batas_max":23},{"nutrisi_id":"<energi>","batas_min":2900},{"nutrisi_id":"<kalsium>","batas_min":0.9,"batas_max":1.2}]` | 200 |
| 3.5 | `PUT /fase/{fase_starter}/standar-konsumsi` | `{"gram_per_ekor_per_hari":50,"frekuensi_makan":4,"durasi_aduk":30,"volume_air":200}` | 200 |
| 3.6 | `PUT /fase/{fase_grower}/kebutuhan-nutrisi` | `[{"nutrisi_id":"<protein>","batas_min":18,"batas_max":21}]` | 200 (dipakai di langkah 7) |
| 3.7 | `PUT /fase/{fase_grower}/standar-konsumsi` | `{"gram_per_ekor_per_hari":90,"frekuensi_makan":3,"durasi_aduk":30,"volume_air":300}` | 200 |

## 4. Kandang, alat, wadah, stok (UC-03/04/12)

| # | Endpoint | Body | Harapan / Catat |
|---|---|---|---|
| 4.1 | `POST /kandang` | `{"nama":"Kandang A","lokasi":"Blok 1"}` | 201 → `kandang` |
| 4.2 | `POST /kandang/{kandang}/alat` | `{}` | 201, `device_token` muncul → **salin sekarang** (hanya tampil sekali), `alat` |
| 4.3 | `POST /kandang/{kandang}/alat` (ulang) | `{}` | 400 `sudah memiliki Alat IoT` |
| 4.4–4.7 | `POST /alat/{alat}/wadah` ×4 | `{"nomor_wadah":1,"bahan_pakan_id":"<jagung>"}`, lalu nomor 2 `<kedelai>`, 3 `<dedak>`, 4 `<kapur>` | 201 → `wadah1..4` |
| 4.8 | `POST /alat/{alat}/wadah` | `{"nomor_wadah":1}` | 400 `Wadah nomor 1 sudah ada` |
| 4.9 | `POST /wadah/{wadah1}/stok/isi-ulang` | `{"jumlah":20000}` | 201, jenis `ISI_ULANG` |
| 4.10 | isi ulang wadah2 | `{"jumlah":10000}` | 201 |
| 4.11 | isi ulang wadah3 | `{"jumlah":10000}` | 201 |
| 4.12 | isi ulang wadah4 | `{"jumlah":2000}` | 201 |
| 4.13 | `POST /wadah/{wadah1}/stok/koreksi` | `{"jumlah_baru":20000,"alasan":""}` | **422** `Alasan koreksi wajib diisi` (BR-34) |
| 4.14 | `GET /kandang/{kandang}/stok` | — | 4 baris dengan nama bahan |

> Langkah 4.9–4.12 sengaja dilakukan **sebelum** beri makan: baris `Stok` baru dibuat saat endpoint stok dipanggil (temuan T-6). Untuk mengonfirmasi T-6, ulangi skenario dengan wadah baru yang **tidak** diisi ulang dan lihat stoknya tidak berubah setelah langkah 9.

## 5. Siklus (UC-06)

| # | Endpoint | Body | Harapan |
|---|---|---|---|
| 5.1 | `POST /kandang/{kandang}/siklus` | `{"jenis_ayam_id":"<jenis_ayam>","fase_id":"<fase_starter>","jumlah_ayam":100,"tanggal_mulai":"2026-11-01"}` | 201 → `siklus` |
| 5.2 | ulangi 5.1 | sama | 409 `masih memiliki siklus aktif` |
| 5.3 | `GET /kandang/{kandang}/siklus/aktif` | — | 200 siklus tadi |
| 5.4 | `POST /siklus/{siklus}/populasi` | `{"jenis":"MORTALITAS","jumlah":2,"tanggal":"2026-11-02","catatan":"uji"}` | 201 |
| 5.5 | `POST /siklus/{siklus}/populasi` | `{"jenis":"PENAMBAHAN","jumlah":2,"tanggal":"2026-11-02"}` | 201 (populasi kembali 100) |
| 5.6 | `GET /kandang/{kandang}` | — | `siklus_aktif_id` terisi, `status_alat: OFFLINE` |

Total pakan per sesi untuk 100 ekor: 50 g × 100 ÷ 4 = **1250 g**.

## 6. Formulasi — inti MVP (UC-07)

| # | Endpoint | Body | Harapan (kunci: tidak 500) |
|---|---|---|---|
| 6.1 | `POST /siklus/{siklus}/formulasi/otomatis` | `{}` | 200, `status: VALID`, `total_biaya_per_kg` terisi, semua `nutrisi_hasil.status: SESUAI`, Σ `proporsi` ≈ 1, `berat_per_sesi` total ≈ 1250. **Simpan seluruh JSON-nya** |
| 6.2 | `POST /siklus/{siklus}/formulasi/manual` | `{"item":[{"bahan_pakan_id":"<jagung>","proporsi":0.64},{"bahan_pakan_id":"<kedelai>","proporsi":0.33},{"bahan_pakan_id":"<kapur>","proporsi":0.025},{"bahan_pakan_id":"<dedak>","proporsi":0.005}]}` | 200, `status: VALID`; jagung `berat_per_sesi` ≈ 800 |
| 6.3 | manual (nutrisi kurang) | `{"item":[{"bahan_pakan_id":"<jagung>","proporsi":0.5},{"bahan_pakan_id":"<kedelai>","proporsi":0.2},{"bahan_pakan_id":"<dedak>","proporsi":0.28},{"bahan_pakan_id":"<kapur>","proporsi":0.02}]}` | 200, `status: TIDAK_SEMPURNA`, Protein `KURANG`, `pesan: Nutrisi tidak sesuai batas: Protein` |
| 6.4 | manual (total ≠ 1) | `{"item":[{"bahan_pakan_id":"<jagung>","proporsi":0.5}]}` | 400 `Total proporsi harus 1.0` |
| 6.5 | `POST /formulasi` | tempel JSON hasil **6.1** | 201, `aktif: true`, `status: VALID` → `formulasi` |
| 6.6 | `GET /siklus/{siklus}/formulasi` | — | 1 item |
| 6.7 | `GET /formulasi/{formulasi}` | — | `item[]` dan `nutrisi_hasil[]` terisi |
| 6.8 | `POST /formulasi` | tempel JSON hasil 6.2 | 201; formulasi 6.5 kini `aktif: false` (cek via 6.6), yang baru `aktif: true` |

Opsional – infeasible: ubah kebutuhan Protein fase starter ke `batas_min: 60` (`PUT .../kebutuhan-nutrisi`), jalankan 6.1 → 200 `TIDAK_SEMPURNA`, `item: []`. Kembalikan ke 20–23 setelahnya. (Catatan: `nutrisi_hasil` kosong & pesan generik adalah temuan S-1, belum diperbaiki.)

## 7. Pindah fase → PERLU_DITINJAU (K-2)

| # | Endpoint | Body | Harapan |
|---|---|---|---|
| 7.1 | `PATCH /siklus/{siklus}/fase` | `{"fase_id":"<fase_grower>"}` | 200 (sebelumnya crash) |
| 7.2 | `GET /siklus/{siklus}/formulasi` | — | formulasi `aktif: true` kini `status: PERLU_DITINJAU` |
| 7.3 | `PATCH /siklus/{siklus}/fase` | `{"fase_id":"<fase_starter>"}` | 200 (kembali ke starter untuk tes berikutnya) |
| 7.4 | Ulangi 6.1 lalu 6.5 | — | Buat formulasi VALID baru yang `aktif: true` → `formulasi` (pakai ID baru ini di langkah 9) |

## 8. Alat & perintah beri makan (UC-08)

Endpoint `/device/*` memakai header, bukan JWT. Di Swagger, isi kolom **x-device-token** pada tiap endpoint device dengan `device_token` dari 4.2.

| # | Endpoint | Body | Harapan |
|---|---|---|---|
| 8.1 | `POST /kandang/{kandang}/perintah/beri-makan` | `{"formulasi_id":"<formulasi>"}` | **409 `Alat sedang OFFLINE`** (belum heartbeat) |
| 8.2 | `POST /device/heartbeat` (x-device-token benar) | `{"status":"ONLINE"}` | 200, `perintah_pending: null`, `config.heartbeat_interval_seconds: 10` |
| 8.3 | `POST /device/heartbeat` (token ngawur) | `{"status":"ONLINE"}` | 401 `Invalid Device Token` |
| 8.4 | `GET /kandang/{kandang}` | — | `status_alat: ONLINE` |
| 8.5 | `POST /kandang/{kandang}/perintah/beri-makan` | `{"formulasi_id":"<formulasi>"}` | 201, `status: PENDING` → `perintah` |
| 8.6 | ulangi 8.5 | sama | 409 `Alat sedang memproses perintah lain` |
| 8.7 | `POST /device/heartbeat` | `{"status":"ONLINE"}` | `perintah_pending.id` = `perintah` |
| 8.8 | `POST /device/perintah/{perintah}/ambil` | `{}` | 200, `status: DIAMBIL` |
| 8.9 | `GET /perintah/{perintah}` (JWT) | — | `status: DIAMBIL` |
| 8.10 | `POST /device/perintah/{perintah}/mulai` | `{}` | 200, `status: BERJALAN` |
| 8.11 | `POST /device/perintah/{perintah}/log` | `{"id_eksekusi_unik":"<uuid-baru>","berat_aktual":1250,"status":"SUKSES"}` | **201** (K-3: sebelumnya crash). Buat UUID bebas, mis. `3f1c2b7e-8a44-4d1e-9a31-5b6c0d9e7a10`; catat |
| 8.12 | `GET /perintah/{perintah}` | — | `status: SUKSES`, `log_eksekusi` terisi |
| 8.13 | ulangi 8.11 persis (UUID sama) | sama | Tidak membuat log ganda. Kontrak minta **200**; implementasi saat ini 201 (T-10) — catat sebagai temuan, bukan kegagalan |

## 9. Efek ke stok, notifikasi, riwayat

| # | Endpoint | Harapan |
|---|---|---|
| 9.1 | `GET /kandang/{kandang}/stok` | Jagung 20000 − 800 = ±19200; kedelai 10000 − ±412,5; kapur 2000 − ±31,25; dedak sedikit berkurang (sesuai `berat_per_sesi`) |
| 9.2 | `GET /wadah/{wadah1}/stok/transaksi` | Ada transaksi `PENGELUARAN` dan `ISI_ULANG` |
| 9.3 | `GET /notifikasi` | Ada notifikasi `PERINTAH_SUKSES` (`BELUM_DIBACA`) |
| 9.4 | `PATCH /notifikasi/{id}/baca` | `SUDAH_DIBACA` |
| 9.5 | `PATCH /notifikasi/baca-semua` | 204 |
| 9.6 | `GET /kandang/{kandang}/perintah` | 1 perintah, terbaru dulu |

Skenario gagal: ulangi 8.5 → 8.7 → 8.8 → 8.10, lalu 8.11 dengan UUID baru dan `"status":"GAGAL"` → `GET /perintah/{id}` = `GAGAL`, stok **tidak** berkurang, notifikasi `PERINTAH_GAGAL`.

## 10. Selesai siklus (K-2)

| # | Endpoint | Harapan |
|---|---|---|
| 10.1 | `POST /siklus/{siklus}/selesai` body `{}` | 200, `status: SELESAI` (sebelumnya crash) |
| 10.2 | `GET /siklus/{siklus}/formulasi` | semua formulasi `aktif: false` |
| 10.3 | `POST /siklus/{siklus}/populasi` | 400 `Siklus sudah selesai` |

## 11. Otorisasi (opsional, 5 menit)

| # | Aksi | Harapan |
|---|---|---|
| 11.1 | `POST /users` `{"nama":"Budi","email":"budi@example.com","kata_sandi":"budi12345","role":"PEKERJA"}` | 201, tanpa hash di respons |
| 11.2 | `POST /users` dengan `"role":"PEMILIK"` | 400 |
| 11.3 | Authorize ulang sebagai Budi → `GET /kandang/{kandang}` | **403** `Anda tidak ditugaskan` |
| 11.4 | Kembali sebagai admin → `POST /users/{budi}/penugasan` `{"kandang_id":"<kandang>","tanggal_mulai":"2026-11-01"}` → sebagai Budi `GET /kandang` | 201; Budi melihat Kandang A |
| 11.5 | Sebagai Budi `POST /kandang` | 403 (hanya Pemilik) |

## 12. Lembar hasil

Salin tabel ini, isi PASS/FAIL, dan lampirkan JSON error bila ada 500:

| Bagian | Hasil | Catatan |
|---|---|---|
| 0 Migrasi & drift | | |
| 1 Login | | |
| 2–3 Master data | | |
| 4 Kandang/alat/wadah/stok | | |
| 5 Siklus | | |
| 6 Formulasi (K-1) | | |
| 7 Pindah fase (K-2) | | |
| 8 Perintah & alat (K-3) | | |
| 9 Stok & notifikasi | | |
| 10 Selesai siklus (K-2) | | |
| 11 Otorisasi | | |

**Kriteria lulus Fase 0:** bagian 0–10 tanpa 500, dan hasil formulasi 6.1/6.2 `VALID`. Penyimpangan yang *diperkirakan* (bukan kegagalan): 8.13 mengembalikan 201 (T-10), infeasible tanpa rincian nutrisi (S-1), stok tak berubah bila wadah belum pernah disentuh endpoint stok (T-6).

**Bila menemukan 500:** lihat terminal uvicorn (traceback), catat endpoint + body + pesan, lalu kirim ke saya untuk diperbaiki.
