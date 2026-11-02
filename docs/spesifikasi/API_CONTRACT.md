# Kontrak API — Smart Poultry (MVP)

Cakupan: akun & kandang dasar, master data nutrisi, siklus & populasi,
**formulasi pakan (LP)**, **beri makan manual**, stok, notifikasi, dan
endpoint untuk **simulator alat**. Tidak ada endpoint jadwal/pengajuan
(Fase 2).

## Konvensi umum

- Base URL: `/api/v1`
- Autentikasi web: **Bearer JWT** di header `Authorization`, didapat dari `POST /auth/login`.
- Autentikasi alat (simulator): header `X-Device-Token: <device_token>` (bukan JWT — perangkat tidak login sebagai user). Server menyimpan hanya hash SHA-256 token; token mentah hanya muncul di respons pembuatan/rotasi.
- Health check: `GET /health` (proses hidup, tanpa DB) dan `GET /health/db` (`200 {"status":"ok","database":"ok"}` atau `503` bila database tidak terjangkau). Keduanya tanpa autentikasi, di luar `/api/v1`.
- Body & response: JSON. Semua `id` adalah UUID string.
- Semua angka uang: `number` (desimal), dikirim sebagai string di JSON kalau presisi jadi masalah — untuk MVP cukup `number` biasa.
- Error: `{"detail": "pesan"}` dengan status code HTTP standar (400 validasi, 401 tidak terautentikasi, 403 tidak berizin, 404 tidak ditemukan, 409 konflik state, 422 validasi body).
- Daftar (list) mendukung `?skip=0&limit=20` (default `limit=20`, maksimum `100`; di luar rentang → `422`) dengan urutan tetap. Total seluruh data (tanpa paginasi) dikirim di header **`X-Total-Count`** (diekspos untuk CORS). Berlaku untuk: jenis-ayam, fase per jenis, nutrisi, bahan-pakan, kandang, users, notifikasi, riwayat formulasi, riwayat perintah, transaksi stok. Tidak dipaginasi karena kecil/terbatas: `GET /kandang/{id}/stok`, `GET /template/jenis-ayam`.
- Endpoint yang mengubah data milik Pekerja/Pemilik mengecek kepemilikan/penugasan kandang di level service, bukan hanya role — lihat kolom "Otorisasi" tiap endpoint.

## Ringkasan status code khusus

| Situasi | Status |
|---|---|
| Validasi gagal (body salah bentuk/nilai, mis. `jumlah` ≤ 0, `limit` > 100) | 422 |
| Nilai request tidak valid terhadap aturan (mis. total proporsi ≠ 1, fase bukan milik jenis ayam, tidak ada field yang diubah) | 400 |
| Bertentangan dengan keadaan data (siklus sudah selesai, alat/wadah sudah ada, kandang belum punya alat, alat offline, stok tidak cukup, masih dipakai saat dihapus, kandang NONAKTIF) | 409 |
| Berhasil membuat resource | 201 |
| Berhasil, tidak ada body balik | 204 |

---

## 1. Auth

| Method | Path | Body | Response | Catatan |
|---|---|---|---|---|
| POST | `/auth/login` | `{email, kata_sandi}` | `{access_token, token_type, user}` | Menerima JSON murni. `401` email/kata sandi salah; `403` user `NONAKTIF`; `429` + header `Retry-After` setelah 5 percobaan gagal per email+alamat klien dalam 300 detik (in-memory per proses) |
| GET | `/auth/me` | — | `User` | Butuh JWT |
| POST | `/auth/ganti-kata-sandi` | `{kata_sandi_lama, kata_sandi_baru}` | 204 | Butuh JWT |

> **Catatan Endpoint Login & Swagger UI:**
> `POST /auth/login` secara ketat **hanya** menerima body **JSON** (sebagai *source of truth* untuk Frontend). 
> Terdapat satu endpoint internal tersembunyi (`POST /auth/swagger-login`) yang dikhususkan untuk menerima Form-Data `application/x-www-form-urlencoded`. Endpoint internal ini **hanya** digunakan agar fitur tombol gembok "Authorize" bawaan Swagger UI (`/docs`) dapat berfungsi untuk keperluan testing. Frontend developer **dilarang** menggunakan endpoint `swagger-login` tersebut dan harus tetap menggunakan `/auth/login` dengan payload JSON.

## 2. User & Penugasan (BR-02, BR-03)

> **Daftar penugasan (5B), hanya Pemilik:** `GET /kandang/{id}/penugasan` (pekerja di sebuah kandang) dan `GET /users/{id}/penugasan` (kandang milik seorang Pekerja). Respons `[{id, user_id, kandang_id, tanggal_mulai, status, nama_pekerja, email_pekerja, nama_kandang}]`, tanggal mulai terbaru dulu, berpaginasi (`X-Total-Count`), filter `?status=AKTIF|BERAKHIR` (nilai lain `422`). Id penugasan dipakai oleh `DELETE /penugasan/{id}`. Pekerja `403`; Pemilik lain `403/404`.

> **Fase 1:** Pekerja dimiliki Pemilik yang membuatnya (`User.pemilik_id`, tidak diekspos di response). `GET /users` dan `PATCH /users/{id}/status` hanya
> menjangkau Pekerja milik Pemilik yang login; penugasan memvalidasi kandang & Pekerja milik Pemilik, penugasan aktif ganda → `409`.

| Method | Path | Body | Response | Otorisasi |
|---|---|---|---|---|
| POST | `/users` | `{nama, email, kata_sandi, role}` | `User` (201) | Hanya Pemilik; role yang dibuat harus `PEKERJA` |
| GET | `/users` | — | `User[]` | Hanya Pemilik (daftar Pekerja miliknya) |
| PATCH | `/users/{id}/status` | `{status}` | `User` | Hanya Pemilik, nonaktifkan Pekerja |
| POST | `/users/{id}/penugasan` | `{kandang_id, tanggal_mulai}` | `PenugasanKandang` (201) | Hanya Pemilik |
| DELETE | `/penugasan/{id}` | — | 204 | Hanya Pemilik (set status `BERAKHIR`, bukan hard delete) |

## 3. Kandang & Alat (UC-03, UC-04)

> **Hapus data salah input (Fase 1 – P2), hanya Pemilik pemilik data.** Penghapusan keras hanya bila belum ada riwayat; selain itu `409` dengan rincian. Semuanya tercatat di `AuditLog` (`HAPUS_*`).
>
> | Method | Path | Aturan |
> |---|---|---|
> | DELETE | `/wadah/{id}` | Ditolak bila wadah pernah mengeluarkan pakan (ada transaksi `PENGELUARAN`) atau stok belum 0 (koreksi ke 0 dulu). Stok dan transaksi isi ulang/koreksi ikut terhapus. Bila bahannya tidak lagi terpasang di wadah lain, formulasi aktif → `PERLU_DITINJAU` |
> | DELETE | `/alat/{id}` | Ditolak bila alat sudah punya perintah (riwayat) atau stok wadah belum 0. Wadah, stok, dan transaksi stoknya ikut terhapus; formulasi aktif → `PERLU_DITINJAU` |
> | DELETE | `/kandang/{id}` | Ditolak bila pernah punya siklus, alatnya punya perintah, atau stok belum 0 (gunakan `PATCH status=NONAKTIF`). Penugasan, alat, wadah, dan stok ikut terhapus |

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
| GET | `/kandang/{id}/alat` | — | `AlatDetail \| null` | Pemilik pemilik / Pekerja ditugaskan. Alat + `wadah[]` (`nomor_wadah`, `bahan_pakan_id`, `nama_bahan`, `jumlah_stok`, `ambang_menipis`). Status memperhitungkan heartbeat kedaluwarsa; **tanpa** `device_token`. `null` bila belum ada alat |

## 4. Master Data (UC-05)

> **DELETE master data (Fase 1 – P1):** hanya Pemilik pemilik data. Bila masih dipakai → `409` dengan rincian (tanpa penghapusan diam-diam):
> bahan pakan (dipakai wadah / item formulasi), nutrisi (kandungan bahan / kebutuhan fase / hasil formulasi), fase dan jenis ayam (dipakai siklus).
> Kandungan bahan pakan, standar konsumsi, kebutuhan fase, dan fase milik jenis ayam ikut terhapus. Setiap penghapusan dicatat di `AuditLog` (`HAPUS_*`).

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

> **Endpoint baca (5B, untuk layar edit di UI)** — hanya Pemilik pemilik data; `404` bila bukan miliknya:
>
> | Method | Path | Response |
> |---|---|---|
> | GET | `/bahan-pakan/{id}/nutrisi` | `[{id, bahan_pakan_id, nutrisi_id, nilai_per_kg, nama_nutrisi, satuan}]` urut nama nutrisi |
> | GET | `/fase/{id}/kebutuhan-nutrisi` | `[{id, fase_id, nutrisi_id, batas_min, batas_max, nama_nutrisi, satuan}]` urut nama nutrisi |
> | GET | `/fase/{id}/standar-konsumsi` | `StandarKonsumsi` atau `null` bila belum diatur |
>
> Daftar ini tidak dipaginasi (jumlahnya terbatas per bahan/fase).

| Method | Path | Body | Response |
|---|---|---|---|
| PUT | `/bahan-pakan/{id}/nutrisi` | `[{nutrisi_id, nilai_per_kg}]` | `KandunganNutrisiBahan[]` — replace semua sekaligus, lebih praktis dari form di UI daripada CRUD satu-satu |
| PUT | `/fase/{id}/kebutuhan-nutrisi` | `[{nutrisi_id, batas_min?, batas_max?}]` | `KebutuhanNutrisiFase[]` |

### Template referensi (BR-13)

| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/template/jenis-ayam` | — | `TemplateJenisAyam[]` (`id`, `nama`, `deskripsi`, `fase[]` dengan `kebutuhan[]` dan `standar_konsumsi`) — data statis bawaan (`broiler`, `petelur`), read-only, tidak terikat `pemilik_id`. **Hanya Pemilik** |
| POST | `/template/jenis-ayam/{template_id}/salin` | `{}` atau `{"nama": "..."}` (opsional) | `JenisAyam` (201) — menyalin jenis ayam + fase + kebutuhan nutrisi + standar konsumsi ke akun Pemilik yang login |

Aturan salin: nutrisi dicocokkan berdasarkan **nama** (tanpa membedakan huruf) dengan nutrisi milik Pemilik; yang belum ada dibuat otomatis (`Protein`, `Energi Metabolis`, `Kalsium`, `Fosfor Tersedia`, `Lisin`). Nama jenis ayam yang sudah ada → `409` (kirim `nama` lain). Template tidak dikenal → `404`. Dicatat di `AuditLog` (`SALIN_TEMPLATE`).
**Nilai template hanya contoh berdasarkan kisaran umum, bukan rekomendasi gizi resmi** — Pemilik wajib menyesuaikannya sebelum dipakai.

## 5. Siklus & Populasi (UC-06)

> **Daftar populasi (5B):** `GET /siklus/{id}/populasi` → `PerubahanPopulasi[]` (tanggal terbaru dulu), berpaginasi (`?skip&limit`, header `X-Total-Count`). Boleh dibaca Pemilik dan Pekerja yang ditugaskan; id dari daftar ini dipakai untuk `DELETE /siklus/{id}/populasi/{populasi_id}`.

> **Koreksi salah input (Fase 1 – P1), hanya Pemilik & siklus `AKTIF`:**
>
> | Method | Path | Body | Response | Catatan |
> |---|---|---|---|---|
> | PATCH | `/siklus/{id}` | `{jumlah_ayam?, tanggal_mulai?}` | `SiklusKandang` | `jumlah_ayam` menggantikan nilai saat ini (≥ 0). Bila populasi berubah, formulasi aktif → `PERLU_DITINJAU` + notifikasi. Tanpa field → `400`. Audit `KOREKSI_SIKLUS` |
> | DELETE | `/siklus/{id}/populasi/{populasi_id}` | — | 204 | Efek catatan dibalik pada `jumlah_ayam` (mortalitas/panen ditambah kembali, penambahan dikurangi). `409` bila jumlah akan negatif. Audit `HAPUS_PERUBAHAN_POPULASI` |
>
> **Hapus siklus salah input (P2), hanya Pemilik:** `DELETE /siklus/{id}` → `204`. Catatan populasi dan formulasi (beserta item/hasil nutrisi) ikut terhapus. `409` bila formulasinya sudah dipakai perintah — gunakan `POST /siklus/{id}/selesai`.

| Method | Path | Body | Response | Catatan |
|---|---|---|---|---|
| POST | `/kandang/{id}/siklus` | `{jenis_ayam_id, fase_id, jumlah_ayam, tanggal_mulai}` | `SiklusKandang` (201) | Ditolak (409) jika kandang masih punya siklus `AKTIF` |
| GET | `/kandang/{id}/siklus/aktif` | — | `SiklusKandang \| null` | |
| PATCH | `/siklus/{id}/fase` | `{fase_id}` | `SiklusKandang` | Pindah fase; formulasi lama otomatis ditandai `PERLU_DITINJAU` |
| POST | `/siklus/{id}/populasi` | `{jenis, jumlah, tanggal, catatan?}` | `PerubahanPopulasi` (201) | `jenis = MORTALITAS` dan `PANEN` mengurangi `jumlah_ayam`; `PENAMBAHAN` menambah |
| POST | `/siklus/{id}/selesai` | `{}` | `SiklusKandang` | status → `SELESAI` |

## 6. Formulasi — inti MVP (UC-07, BR-08/BR-09)

> **Fase 1:** endpoint `otomatis`, `manual`, dan `POST /formulasi` hanya untuk **Pemilik** (Pekerja `403`); `GET` tetap untuk Pekerja yang ditugaskan.
> Objek `Formulasi` memuat field `aktif` (boolean): hanya satu formulasi VALID per siklus yang `aktif=true`; `status` menyatakan validitas
> (`VALID`/`TIDAK_SEMPURNA`/`PERLU_DITINJAU`).
> `POST /formulasi` **tidak mempercayai angka dari klien**: server hanya memakai `mode` dan komposisi (`item[].bahan_pakan_id`, `proporsi`), lalu menghitung ulang
> biaya, berat per sesi, nilai dan status nutrisi. Mode `OTOMATIS` harus cocok dengan hasil LP terbaru (biaya dalam toleransi 0,1% dan `batas_maksimum` bahan terpenuhi),
> bila tidak `409` (hitung ulang). Komposisi kosong → `400`; siklus sudah selesai → `409`.
>
> `DELETE /formulasi/{id}` (hanya Pemilik) → `204`; item dan hasil nutrisi ikut terhapus. `409` bila formulasi sudah dipakai perintah (riwayat).

| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/siklus/{id}/formulasi/otomatis` | `{}` | `FormulasiPreview` (lihat bentuk di bawah) — **belum tersimpan** |
| POST | `/siklus/{id}/formulasi/manual` | `{item: [{bahan_pakan_id, proporsi}]}` | `FormulasiPreview` — dihitung & divalidasi, **belum tersimpan** |
| POST | `/formulasi` | `FormulasiPreview` (hasil salah satu endpoint di atas) | `Formulasi` (201) — baru disimpan permanen sebagai snapshot di sini |
| GET | `/siklus/{id}/formulasi` | — | `Formulasi[]` (riwayat snapshot, terbaru dulu) |
| GET | `/formulasi/{id}` | — | `Formulasi` lengkap dengan `item[]` (memuat `nama_bahan`) dan `nutrisi_hasil[]` (memuat `nama_nutrisi`, `satuan`) |

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
  Diagnosis (S-1): `nutrisi_hasil[]` memuat **semua** nutrisi kebutuhan fase dengan `status` (`KURANG`/`BERLEBIH`/`SESUAI`), `nilai_hasil`, dan field baru `keterangan` (null bila tidak bermasalah). Tiga jenis temuan:
  1. *Mustahil sendiri*: batas di luar rentang yang mungkin dengan bahan terpasang (mis. protein min 60% padahal bahan terbaik hanya 44%) → `nilai_hasil` = nilai terbaik yang mungkin, `keterangan` "tidak tercapai ...".
  2. *Berbenturan*: tiap batas mungkin sendiri-sendiri, tidak bersama → `nilai_hasil` dari komposisi kompromi terdekat (pelanggaran relatif terkecil), `keterangan` "Berbenturan ...", `pesan` memuat "saling bertentangan". Nutrisi yang disebut hanyalah salah satu pilihan kompromi.
  3. *Batas maksimum bahan*: jumlah `batas_maksimum` bahan terpasang < 100% → `nutrisi_hasil = []`, `pesan` menyebut persentasenya.
  `nilai_hasil` pada preview ini bukan formulasi yang dapat disimpan (`item` kosong; `POST /formulasi` menolak dengan `400`).
- `harga` kosong pada salah satu bahan yang terpasang di wadah → endpoint otomatis balas `409` dengan pesan bahan mana yang belum ada harganya.
- Endpoint `/formulasi` (simpan) menolak (`409`) kalau sejak preview dibuat ada bahan yang dilepas dari wadah — mencegah snapshot menyimpan data yang sudah tidak valid.

## 7. Beri Makan Manual & Perintah (UC-08, BR-24/BR-26)

> **Aturan tambahan (Fase 1):** `beri-makan` mengembalikan `404` bila formulasi tidak ada dan `409` bila formulasi bukan milik siklus aktif kandang,
> tidak `aktif`/bukan `VALID`, atau stok bahan tidak cukup (pesan merinci bahan yang kurang). Perintah yang tidak diproses alat menjadi `TIMEOUT`
> (PENDING/DIAMBIL > 60 dtk, BERJALAN > 300 dtk; konfigurabel) dan alat yang tidak heartbeat > 3x interval dianggap `OFFLINE`; keduanya dievaluasi saat request (tanpa job latar).
> `stop-darurat` membatalkan perintah aktif (→ `GAGAL`) dan boleh dikirim walau alat offline.

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
| POST | `/device/perintah/{id}/log` | `{id_eksekusi_unik, berat_aktual, status: "SUKSES"\|"GAGAL"}` | `LogEksekusi` (201) | Idempoten lewat `id_eksekusi_unik` — kirim ulang dengan id sama tidak membuat log ganda (balas log yang sudah ada, **200** bukan 201). Log kedua dengan id berbeda untuk perintah yang sama, atau id yang dipakai perintah lain → `409`; perintah harus berstatus `DIAMBIL`/`BERJALAN` (selain itu `409`). `SKIPPED_STOCK` menjadikan perintah `GAGAL` tanpa mengurangi stok. Server otomatis: update `Perintah.status`, kurangi `Stok` kalau SUKSES, catat `TransaksiStok` jenis `PENGELUARAN`, buat `Notifikasi` |

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
