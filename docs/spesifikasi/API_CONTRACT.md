# Kontrak API — Smart Poultry (MVP)

Cakupan: akun & kandang dasar, master data nutrisi, siklus & populasi,
**formulasi pakan (LP)**, **beri makan manual**, stok, notifikasi, dan
endpoint untuk **simulator alat**. Tidak ada endpoint jadwal/pengajuan
(Fase 2).

## Konvensi umum

- Base URL: `/api/v1`
- Autentikasi web: **Bearer JWT** di header `Authorization`, didapat dari `POST /auth/login`.
- Autentikasi alat (simulator): header `X-Device-Token: <device_token>` (bukan JWT — perangkat tidak login sebagai user).
- Body & response: JSON. Semua `id` adalah UUID string.
- Semua angka uang: `number` (desimal), dikirim sebagai string di JSON kalau presisi jadi masalah — untuk MVP cukup `number` biasa.
- Error: `{"detail": "pesan"}` dengan status code HTTP standar (400 validasi, 401 tidak terautentikasi, 403 tidak berizin, 404 tidak ditemukan, 409 konflik state, 422 validasi body).
- Daftar (list) mendukung `?skip=0&limit=20` (default `limit=20`, maksimum `100`).
- Endpoint yang mengubah data milik Pekerja/Pemilik mengecek kepemilikan/penugasan kandang di level service, bukan hanya role — lihat kolom "Otorisasi" tiap endpoint.

## Ringkasan status code khusus

| Situasi | Status |
|---|---|
| Validasi gagal (body salah bentuk) | 422 |
| Aturan bisnis gagal (mis. formulasi tidak feasible, alat offline) | 409 |
| Berhasil membuat resource | 201 |
| Berhasil, tidak ada body balik | 204 |

---

## 1. Auth

| Method | Path | Body | Response | Catatan |
|---|---|---|---|---|
| POST | `/auth/login` | `{email, kata_sandi}` | `{access_token, token_type, user}` | Menerima JSON murni. |
| GET | `/auth/me` | — | `User` | Butuh JWT |
| POST | `/auth/ganti-kata-sandi` | `{kata_sandi_lama, kata_sandi_baru}` | 204 | Butuh JWT |

> **Catatan Endpoint Login & Swagger UI:**
> `POST /auth/login` secara ketat **hanya** menerima body **JSON** (sebagai *source of truth* untuk Frontend). 
> Terdapat satu endpoint internal tersembunyi (`POST /auth/swagger-login`) yang dikhususkan untuk menerima Form-Data `application/x-www-form-urlencoded`. Endpoint internal ini **hanya** digunakan agar fitur tombol gembok "Authorize" bawaan Swagger UI (`/docs`) dapat berfungsi untuk keperluan testing. Frontend developer **dilarang** menggunakan endpoint `swagger-login` tersebut dan harus tetap menggunakan `/auth/login` dengan payload JSON.

## 2. User & Penugasan (BR-02, BR-03)

| Method | Path | Body | Response | Otorisasi |
|---|---|---|---|---|
| POST | `/users` | `{nama, email, kata_sandi, role}` | `User` (201) | Hanya Pemilik; role yang dibuat harus `PEKERJA` |
| GET | `/users` | — | `User[]` | Hanya Pemilik (daftar Pekerja miliknya) |
| PATCH | `/users/{id}/status` | `{status}` | `User` | Hanya Pemilik, nonaktifkan Pekerja |
| POST | `/users/{id}/penugasan` | `{kandang_id, tanggal_mulai}` | `PenugasanKandang` (201) | Hanya Pemilik |
| DELETE | `/penugasan/{id}` | — | 204 | Hanya Pemilik (set status `BERAKHIR`, bukan hard delete) |

## 3. Kandang & Alat (UC-03, UC-04)

| Method | Path | Body | Response | Otorisasi |
|---|---|---|---|---|
| POST | `/kandang` | `{nama, lokasi}` | `Kandang` (201) | Pemilik |
| GET | `/kandang` | — | `Kandang[]` | Pemilik (miliknya) / Pekerja (yang ditugaskan) |
| GET | `/kandang/{id}` | — | `Kandang` (termasuk status alat & siklus aktif) | Pemilik pemilik / Pekerja ditugaskan |
| PATCH | `/kandang/{id}` | `{nama?, lokasi?, status?}` | `Kandang` | Pemilik |
| POST | `/kandang/{id}/alat` | `{}` | `Alat` (201, `device_token` di-generate & dikembalikan **sekali** di response ini) | Pemilik |
| POST | `/alat/{id}/rotasi-token` | `{}` | `{device_token}` | Pemilik |
| POST | `/alat/{id}/wadah` | `{nomor_wadah, bahan_pakan_id?}` | `Wadah` (201) | Pemilik |
| PATCH | `/wadah/{id}` | `{bahan_pakan_id}` | `Wadah` | Pemilik — memetakan ulang wadah ke bahan pakan |

## 4. Master Data (UC-05)

Pola CRUD yang sama berlaku untuk lima resource ini (disingkat jadi satu tabel):

| Resource | Path | Catatan |
|---|---|---|
| Jenis Ayam | `/jenis-ayam` | — |
| Fase | `/jenis-ayam/{id}/fase` (create/list), `/fase/{id}` (get/patch/delete) | — |
| Nutrisi | `/nutrisi` | `tipe_batas` wajib diisi |
| Bahan Pakan | `/bahan-pakan` | `harga` wajib untuk dipakai mode OTOMATIS |
| Standar Konsumsi | `/fase/{id}/standar-konsumsi` (upsert, PUT) | 1 fase = 1 standar konsumsi |

Masing-masing resource mendukung `POST` (create, 201), `GET` (list, dengan `?jenis_ayam_id=` untuk Fase), `GET /{id}`, `PATCH /{id}`, `DELETE /{id}` (hanya Pemilik). Semua otomatis di-scope ke `pemilik_id` dari JWT — Pemilik tidak bisa melihat/mengubah master data Pemilik lain.

### Kandungan nutrisi bahan & kebutuhan nutrisi fase

| Method | Path | Body | Response |
|---|---|---|---|
| PUT | `/bahan-pakan/{id}/nutrisi` | `[{nutrisi_id, nilai_per_kg}]` | `KandunganNutrisiBahan[]` — replace semua sekaligus, lebih praktis dari form di UI daripada CRUD satu-satu |
| PUT | `/fase/{id}/kebutuhan-nutrisi` | `[{nutrisi_id, batas_min?, batas_max?}]` | `KebutuhanNutrisiFase[]` |

### Template referensi (BR-13)

| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/template/jenis-ayam` | — | Daftar template bawaan (read-only, tidak terikat `pemilik_id`) |
| POST | `/template/jenis-ayam/{template_id}/salin` | `{}` | `JenisAyam` (201) — menyalin jenis ayam + fase + kebutuhan nutrisi + standar konsumsi ke akun Pemilik yang login |

## 5. Siklus & Populasi (UC-06)

| Method | Path | Body | Response | Catatan |
|---|---|---|---|---|
| POST | `/kandang/{id}/siklus` | `{jenis_ayam_id, fase_id, jumlah_ayam, tanggal_mulai}` | `SiklusKandang` (201) | Ditolak (409) jika kandang masih punya siklus `AKTIF` |
| GET | `/kandang/{id}/siklus/aktif` | — | `SiklusKandang \| null` | |
| PATCH | `/siklus/{id}/fase` | `{fase_id}` | `SiklusKandang` | Pindah fase; formulasi lama otomatis ditandai `PERLU_DITINJAU` |
| POST | `/siklus/{id}/populasi` | `{jenis, jumlah, tanggal, catatan?}` | `PerubahanPopulasi` (201) | `jenis = MORTALITAS` dan `PANEN` mengurangi `jumlah_ayam`; `PENAMBAHAN` menambah |
| POST | `/siklus/{id}/selesai` | `{}` | `SiklusKandang` | status → `SELESAI` |

## 6. Formulasi — inti MVP (UC-07, BR-08/BR-09)

| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/siklus/{id}/formulasi/otomatis` | `{}` | `FormulasiPreview` (lihat bentuk di bawah) — **belum tersimpan** |
| POST | `/siklus/{id}/formulasi/manual` | `{item: [{bahan_pakan_id, proporsi}]}` | `FormulasiPreview` — dihitung & divalidasi, **belum tersimpan** |
| POST | `/formulasi` | `FormulasiPreview` (hasil salah satu endpoint di atas) | `Formulasi` (201) — baru disimpan permanen sebagai snapshot di sini |
| GET | `/siklus/{id}/formulasi` | — | `Formulasi[]` (riwayat snapshot, terbaru dulu) |
| GET | `/formulasi/{id}` | — | `Formulasi` lengkap dengan `item[]` dan `nutrisi_hasil[]` |

**`FormulasiPreview` (bentuk response, bukan tabel):**
```json
{
  "mode": "OTOMATIS",
  "status": "VALID",
  "total_biaya_per_kg": 4250.0,
  "item": [
    {"bahan_pakan_id": "uuid", "nama_bahan": "Jagung", "proporsi": 0.55, "berat_per_sesi": 120.4}
  ],
  "nutrisi_hasil": [
    {"nutrisi_id": "uuid", "nama_nutrisi": "Protein", "nilai_hasil": 21.3, "batas_min": 20, "batas_max": 23, "status": "SESUAI"}
  ],
  "pesan": null
}
```

- Kalau LP **tidak feasible**: response tetap `200`, `status = "TIDAK_SEMPURNA"`, `item = []`, `pesan` berisi daftar nutrisi yang tidak terpenuhi (BR-11). **Bukan** error HTTP, karena ini hasil valid dari proses (bukan kegagalan request).
- `harga` kosong pada salah satu bahan yang terpasang di wadah → endpoint otomatis balas `409` dengan pesan bahan mana yang belum ada harganya.
- Endpoint `/formulasi` (simpan) menolak (`409`) kalau sejak preview dibuat ada bahan yang dilepas dari wadah — mencegah snapshot menyimpan data yang sudah tidak valid.

## 7. Beri Makan Manual & Perintah (UC-08, BR-24/BR-26)

| Method | Path | Body | Response | Catatan |
|---|---|---|---|---|
| POST | `/kandang/{id}/perintah/beri-makan` | `{formulasi_id}` | `Perintah` (201, `status=PENDING`) | 409 jika alat offline atau ada perintah lain yang masih `PENDING`/`BERJALAN` |
| POST | `/kandang/{id}/perintah/stop-darurat` | `{}` | `Perintah` (201) | `tipe=STOP_DARURAT`, selalu boleh dikirim walau ada perintah lain berjalan |
| GET | `/perintah/{id}` | — | `Perintah` (termasuk `log_eksekusi` jika sudah ada) | Dipakai frontend untuk polling status sampai `SUKSES`/`GAGAL`/`TIMEOUT` |
| GET | `/kandang/{id}/perintah` | — | `Perintah[]` | Riwayat, terbaru dulu |

Frontend melakukan **polling** `GET /perintah/{id}` tiap 1-2 detik sampai status final — tidak perlu WebSocket untuk MVP ini.

## 8. Endpoint Simulator Alat (BR-24, device-facing)

Semua endpoint di bawah pakai header `X-Device-Token`, **bukan** JWT.

| Method | Path | Body | Response | Fungsi |
|---|---|---|---|---|
| POST | `/device/heartbeat` | `{status: "ONLINE"\|"ERROR"}` | `{perintah_pending: Perintah \| null, config: {heartbeat_interval_seconds}}` | Dipanggil simulator tiap beberapa detik (lihat `DEVICE_HEARTBEAT_INTERVAL_SECONDS`). Server update `waktu_terakhir_sinkron` & `status` alat, lalu balas perintah yang menunggu (kalau ada) |
| POST | `/device/perintah/{id}/ambil` | `{}` | `Perintah` | status → `DIAMBIL` |
| POST | `/device/perintah/{id}/mulai` | `{}` | `Perintah` | status → `BERJALAN` |
| POST | `/device/perintah/{id}/log` | `{id_eksekusi_unik, berat_aktual, status: "SUKSES"\|"GAGAL"}` | `LogEksekusi` (201) | Idempoten lewat `id_eksekusi_unik` — kirim ulang dengan id sama tidak membuat log ganda (balas log yang sudah ada, 200 bukan 201). Server otomatis: update `Perintah.status`, kurangi `Stok` kalau SUKSES, catat `TransaksiStok` jenis `PENGELUARAN`, buat `Notifikasi` |

Simulator alat sendiri (skrip Python terpisah, **bukan** bagian backend ini) meniru perilaku di atas: poll `/device/heartbeat`, kalau dapat perintah → panggil `ambil` → delay beberapa detik (mensimulasikan proses fisik) → `mulai` → delay lagi → `log`.

## 9. Stok (UC-12, BR-34)

| Method | Path | Body | Response | Catatan |
|---|---|---|---|---|
| GET | `/kandang/{id}/stok` | — | `Stok[]` (per wadah, termasuk nama bahan) | |
| POST | `/wadah/{id}/stok/isi-ulang` | `{jumlah}` | `TransaksiStok` (201) | jenis otomatis `ISI_ULANG` |
| POST | `/wadah/{id}/stok/koreksi` | `{jumlah_baru, alasan}` | `TransaksiStok` (201) | **`alasan` wajib**, balas `422` kalau kosong (BR-34) |
| GET | `/wadah/{id}/stok/transaksi` | — | `TransaksiStok[]` | Riwayat |

## 10. Notifikasi

| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/notifikasi?status=BELUM_DIBACA` | — | `Notifikasi[]` |
| PATCH | `/notifikasi/{id}/baca` | `{}` | `Notifikasi` |
| PATCH | `/notifikasi/baca-semua` | `{}` | 204 |

---

## Hal yang perlu diputuskan sebelum mulai coding router

1. **Simulator alat dijalankan di mana?** Saran: skrip Python terpisah (`simulator/`) yang memanggil endpoint bagian 8 lewat `httpx`, dijalankan manual (`python simulator/run.py --device-token=...`) saat testing — tidak perlu containerized dulu untuk MVP.
2. **LP solver**: `scipy.optimize.linprog` sudah masuk `requirements.txt`. Perlu ditentukan di endpoint formulasi-otomatis: fungsi objektif minimisasi `Σ(harga_i × proporsi_i)`, dengan batasan nutrisi sebagai `A_ub`/`b_ub` (atau `A_eq` untuk total proporsi = 1).
3. **Response `User` tidak boleh mengembalikan `kata_sandi_hash`** — pastikan dipakai Pydantic response model terpisah (`UserPublic`), bukan langsung serialize tabel `User` di SQLModel.
