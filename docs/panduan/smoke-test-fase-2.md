# Smoke Test Fase 2

Menguji tambahan Fase 2: template jenis ayam, paginasi, `GET /kandang/{id}/alat`, nama pada formulasi, dan konsistensi kode error.
Prasyarat: lingkungan siap ([setup-backend](setup-backend.md)), server menyala, data demo ada (`python seed_demo.py`). Authorize di `/docs` sebagai `admin@smartpoultry.com` / `admin123`. Waktu ±15 menit.

> Kode ditulis dan diuji otomatis (139 test). Skenario ini belum dijalankan manual lewat Swagger; laporkan langkah yang tidak sesuai.

## A. Template jenis ayam (BR-13)

| # | Aksi | Harapan |
|---|---|---|
| A.1 | `GET /template/jenis-ayam` | 200, dua template (`broiler`, `petelur`); tiap template punya `deskripsi` yang menyebut *bukan rekomendasi gizi resmi*, 3 fase, `kebutuhan[]` (Protein, Energi Metabolis, Kalsium, Fosfor Tersedia, Lisin) dan `standar_konsumsi` |
| A.2 | `GET /nutrisi` (catat jumlah dan namanya), lalu `POST /template/jenis-ayam/broiler/salin` `{"nama":"Broiler Template"}` | **201**, `JenisAyam` bernama `Broiler Template` → catat `id` |
| A.3 | `GET /jenis-ayam/{id}/fase` | 3 fase terurut umur: Starter (0–14), Grower (15–28), Finisher (29–42) |
| A.4 | `GET /nutrisi` | Hanya `Fosfor Tersedia` dan `Lisin` yang bertambah (Protein, Energi Metabolis, Kalsium dari data demo dipakai ulang, tanpa duplikat) |
| A.5 | Ulangi A.2 | **409** (nama sudah ada) |
| A.6 | `POST /template/jenis-ayam/tidak-ada/salin` `{}` | **404** |
| A.7 | `POST /template/jenis-ayam/petelur/salin` tanpa body | **201**, nama `Ayam Petelur` |
| A.8 | Sebagai Budi (Pekerja): `GET /template/jenis-ayam` | **403** |
| A.9 | (Opsional) `DELETE /jenis-ayam/{id}` salinan yang belum dipakai siklus | **204** |

## B. Paginasi

Buat data banyak lewat `POST /bahan-pakan` (mis. 25 kali `{"nama":"Uji 01","harga":1}` dst.), atau gunakan list yang sudah ada.

| # | Aksi | Harapan |
|---|---|---|
| B.1 | `GET /bahan-pakan` | Paling banyak **20** item; header respons `X-Total-Count` = jumlah seluruh bahan |
| B.2 | `GET /bahan-pakan?skip=20` | Sisa item; `X-Total-Count` sama |
| B.3 | `GET /bahan-pakan?limit=5` | 5 item |
| B.4 | `GET /bahan-pakan?limit=101`, `?limit=0`, `?skip=-1` | **422** |
| B.5 | Halaman 1 + 2 dengan `limit=10` | Urut nama, tidak ada duplikat/hilang |
| B.6 | `GET /notifikasi?limit=2`, `GET /users?limit=1`, `GET /kandang?limit=1` | Respons dibatasi; `X-Total-Count` benar |
| B.7 | `GET /kandang/{kandang}/stok` | Tetap tanpa paginasi (4 wadah) |

> Header `X-Total-Count` terlihat di tab *Response headers* Swagger (atau browser DevTools → Network).

## C. `GET /kandang/{id}/alat`

| # | Aksi | Harapan |
|---|---|---|
| C.1 | `GET /kandang/{kandang}/alat` (Kandang A) | Alat dengan `wadah[]` terurut `nomor_wadah`: `nama_bahan`, `jumlah_stok`, `ambang_menipis`. **Tidak ada** `device_token` |
| C.2 | `POST /kandang` `{"nama":"Tanpa alat"}` → `GET /kandang/{id}/alat` | **200** dengan body `null` |
| C.3 | Jalankan simulator beberapa detik, lalu C.1 | `status: ONLINE`, `waktu_terakhir_sinkron` terisi; hentikan simulator ±40 detik → `OFFLINE` |
| C.4 | Sebagai Budi (belum ditugaskan): C.1 | **403**; setelah ditugaskan → 200 |

## D. Nama pada formulasi

| # | Aksi | Harapan |
|---|---|---|
| D.1 | `POST /siklus/{siklus}/formulasi/otomatis` → `POST /formulasi` → `GET /formulasi/{id}` | `item[].nama_bahan` terisi; `nutrisi_hasil[].nama_nutrisi` dan `satuan` terisi |

## E. Konsistensi kode error

| # | Aksi | Harapan |
|---|---|---|
| E.1 | `POST /siklus/{siklus}/populasi` `{"jenis":"MORTALITAS","jumlah":0,"tanggal":"2026-11-02"}` | **422** |
| E.2 | Populasi `PANEN` dengan jumlah lebih besar dari populasi | **409** `... (populasi saat ini N)`; `jumlah_ayam` tidak berubah |
| E.3 | `POST /wadah/{wadah}/stok/isi-ulang` `{"jumlah":0}` | **422** |
| E.4 | `POST /kandang/{kandang}/alat` (sudah ada alat) dan `POST /alat/{alat}/wadah` `{"nomor_wadah":1}` | **409** keduanya |
| E.5 | `PATCH /kandang/{id}` `{"status":"NONAKTIF"}` pada kandang uji → `POST /kandang/{id}/siklus` | **409** `Kandang NONAKTIF`; kembalikan `AKTIF` lalu 201 |
| E.6 | `POST /kandang/{id}/perintah/beri-makan` pada kandang tanpa alat | **409** |
| E.7 | `PATCH /siklus/{siklus}` `{}` | **400** (tidak ada yang diubah) |
| E.8 | Formulasi manual dengan total proporsi ≠ 1 | **400** |

Aturan ringkas: **422** = bentuk/nilai body salah, **400** = nilai request melanggar aturan, **409** = bertentangan dengan keadaan data.
