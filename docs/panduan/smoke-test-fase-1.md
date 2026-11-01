# Smoke Test Fase 1 (hanya perilaku baru)

Melengkapi [smoke-test-swagger.md](smoke-test-swagger.md) (Fase 0, sudah lulus). Skenario ini hanya menguji perubahan Fase 1.
Prasyarat: data demo ada (`python seed_demo.py`, lihat [setup-backend](setup-backend.md#data-demo)). Waktu: ±25 menit (ada dua jeda tunggu).

## 0. Persiapan

> **Tip:** langkah manual `/device/*` (heartbeat, ambil, mulai, log) pada bagian B–G dapat digantikan oleh [simulator](simulator.md): `python simulator/run.py --device-token <TOKEN> --interval 3`.

```bash
cd smart-poultry-backend
.venv\Scripts\activate
alembic current            # harus 9d4e7a1c5b20 (head)
uvicorn app.main:app --reload
```
Buka `http://localhost:8000/docs`, **Authorize** sebagai `admin@smartpoultry.com` / `admin123`, lalu catat ID:

| Catatan | Cara mendapatkan |
|---|---|
| `kandang` | `GET /kandang` |
| `siklus` | `GET /kandang/{kandang}/siklus/aktif` |
| `wadah_jagung`, dst. | `GET /kandang/{kandang}/stok` (cocokkan `nama_bahan`) |
| `alat` | `885455a7-ab5c-495b-afcd-1fef690f3d75` (dari output seed; atau cek DB bila Anda menjalankan ulang seed di database lain) |
| `device_token` | `POST /alat/{alat}/rotasi-token` → salin token baru |
| `budi` | `GET /users` |
| `bahan_jagung` | `GET /bahan-pakan` |

Untuk endpoint `/device/*`, isi kolom **x-device-token** dengan `device_token`.
Penanda waktu: catat jam saat Anda mulai bagian D dan E.

## A. Stok otomatis (T-6)

| # | Aksi | Harapan |
|---|---|---|
| A.1 | `GET /kandang/{kandang}/stok` | 4 baris: Jagung 20000, Kedelai 10000, Dedak 10000, Tepung Batu 2000 |
| A.2 | `POST /kandang` `{"nama":"Kandang Uji"}` → `POST /kandang/{id}/alat` → `POST /alat/{id}/wadah` `{"nomor_wadah":1,"bahan_pakan_id":"<bahan_jagung>"}` → `GET /kandang/{id}/stok` | Baris stok untuk wadah baru langsung ada, `jumlah_estimasi: 0` (tanpa isi ulang) |

## B. Validasi beri makan (T-5, D-4)

Siapkan formulasi: `POST /siklus/{siklus}/formulasi/otomatis` → tempel hasilnya ke `POST /formulasi` → catat `formulasi` (harapan `aktif: true`, `status: VALID`).
Lalu `POST /device/heartbeat` `{"status":"ONLINE"}` supaya alat online.

| # | Aksi | Harapan |
|---|---|---|
| B.1 | `POST /kandang/{kandang}/perintah/beri-makan` `{"formulasi_id":"00000000-0000-0000-0000-000000000001"}` | **404** Formulasi tidak ditemukan |
| B.2 | Beri makan ke kandang lain dengan `formulasi` ini (pakai `Kandang Uji` dari A.2 + heartbeat alatnya) | 409 bukan milik siklus aktif / belum ada alat online |
| B.3 | `POST /wadah/{wadah_jagung}/stok/koreksi` `{"jumlah_baru":10,"alasan":"uji stok kurang"}` lalu beri makan dengan `formulasi` | **409** `Stok tidak cukup: Jagung (butuh ... g, tersedia 10.0 g)` |
| B.4 | Kembalikan: koreksi `{"jumlah_baru":20000,"alasan":"kembalikan setelah uji"}` | 201 |
| B.5 | `POST /siklus/{siklus}/formulasi/manual` (komposisi valid dari smoke test lama) → `POST /formulasi` → beri makan dengan **formulasi lama** | **409** formulasi tidak dapat dipakai (`aktif=False`) |
| B.6 | Ulangi B.0 (formulasi otomatis baru → simpan) untuk mendapatkan formulasi aktif terbaru | Pakai ID ini di bagian berikutnya |

## C. State machine dan idempotensi log (T-9, T-10)

| # | Aksi | Harapan |
|---|---|---|
| C.1 | Beri makan dengan formulasi aktif | 201 `PENDING` → `perintah` |
| C.2 | `POST /device/perintah/{perintah}/mulai` | **409** transisi tidak valid (belum `ambil`) |
| C.3 | `ambil` dua kali berturut-turut | keduanya 200 (`DIAMBIL`) |
| C.4 | `mulai` dua kali | keduanya 200 (`BERJALAN`) |
| C.5 | `log` `{"id_eksekusi_unik":"3f1c2b7e-8a44-4d1e-9a31-5b6c0d9e7a10","berat_aktual":1250,"status":"SUKSES"}` | **201** |
| C.6 | `log` persis sama | **200**, `id` log sama, stok tidak berkurang lagi (cek `GET .../stok`) |
| C.7 | `log` dengan `id_eksekusi_unik` lain untuk perintah yang sama | **409** |
| C.8 | `GET /perintah/{perintah}` | `SUKSES` dengan `log_eksekusi` |
| C.9 | `GET /kandang/{kandang}/stok` | Total pengurangan ≈ 1250 g dibanding A.1 |
| C.10 | Perintah baru → `ambil` → `mulai` → `log` `{"id_eksekusi_unik":"<uuid baru>","berat_aktual":0,"status":"SKIPPED_STOCK"}` | 201; `GET /perintah/{id}` = `GAGAL`; stok tidak berubah |

## D. Timeout (T-8) — jeda tunggu ±70 detik

| # | Aksi | Harapan |
|---|---|---|
| D.1 | `heartbeat` lalu beri makan | 201 `PENDING` → `perintah_t` |
| D.2 | **Jangan** `ambil`. Tunggu 70 detik, **lanjutkan heartbeat tiap ±10 detik** agar alat tetap online | — |
| D.3 | `GET /perintah/{perintah_t}` | `TIMEOUT` |
| D.4 | `GET /notifikasi` | Ada `PERINTAH_GAGAL` berjudul "Perintah timeout" |
| D.5 | Beri makan lagi | 201 (alat tidak lagi terblokir). Selesaikan perintah ini lewat `ambil`/`mulai`/`log` SUKSES |

## E. Alat offline (T-7) — jeda tunggu ±40 detik

| # | Aksi | Harapan |
|---|---|---|
| E.1 | Berhenti memanggil heartbeat selama 40 detik (batas = 3 × 10 detik) | — |
| E.2 | `GET /kandang/{kandang}` | `status_alat: OFFLINE` |
| E.3 | Ulangi E.2 tiga kali, lalu `GET /notifikasi` | `ALAT_OFFLINE` hanya **satu** |
| E.4 | Beri makan | **409** Alat sedang OFFLINE |
| E.5 | `heartbeat` `{"status":"ONLINE"}` → `GET /kandang/{kandang}` | `ONLINE` |
| E.6 | `heartbeat` `{"status":"ERROR"}` → `GET /notifikasi` | Ada `ALAT_ERROR`; lalu `heartbeat` ONLINE lagi |

## F. Stop darurat (T-9)

| # | Aksi | Harapan |
|---|---|---|
| F.1 | Heartbeat ONLINE; beri makan → `ambil` → `mulai` (perintah `BERJALAN`) | — |
| F.2 | `POST /kandang/{kandang}/perintah/stop-darurat` | 201 `STOP_DARURAT`, `PENDING` → `stop` |
| F.3 | `GET /perintah/{perintah}` | `GAGAL` (dibatalkan) |
| F.4 | `heartbeat` | `perintah_pending.id` = `stop` |
| F.5 | `ambil` → `mulai` → `log` SUKSES untuk `stop` | `SUKSES`; stok tidak berubah |
| F.6 | (Opsional) hentikan heartbeat 40 detik lalu kirim stop darurat | Tetap 201 walau alat offline |

## G. Stok kosong (T-11)

| # | Aksi | Harapan |
|---|---|---|
| G.1 | `GET /formulasi/{formulasi}` → catat `berat_per_sesi` jagung (mis. 760.2) | — |
| G.2 | Koreksi stok jagung ke **tepat** angka itu (alasan "uji stok kosong") | 201 |
| G.3 | Heartbeat → beri makan → `ambil` → `mulai` → `log` SUKSES | 201 |
| G.4 | `GET /notifikasi` | Ada `STOK_KOSONG` ("Stok habis ... Jagung"); stok jagung 0 |
| G.5 | Isi ulang jagung 20000 (`.../stok/isi-ulang`) | 201 |

## H. Peran Pekerja dan notifikasi ke pekerja (T-11, D-3)

| # | Aksi | Harapan |
|---|---|---|
| H.1 | Sebagai admin: `POST /users/{budi}/penugasan` `{"kandang_id":"<kandang>","tanggal_mulai":"2026-11-01"}` | 201 |
| H.2 | Ulangi H.1 | **409** sudah ditugaskan |
| H.3 | Authorize ulang sebagai `budi@example.com` / `budi12345`; `GET /kandang` | Melihat Kandang A |
| H.4 | Sebagai Budi: `POST /siklus/{siklus}/formulasi/otomatis` | **403** |
| H.5 | Sebagai Budi: `POST /formulasi` (body apa saja bentuk preview) | **403** |
| H.6 | Sebagai Budi: `GET /formulasi/{formulasi}` | 200 (boleh membaca) |
| H.7 | Sebagai Budi: heartbeat → beri makan → `ambil`/`mulai`/`log` SUKSES | 201 (Pekerja boleh beri makan) |
| H.8 | `GET /notifikasi` sebagai Budi **dan** sebagai admin | Keduanya punya `PERINTAH_SUKSES` |
| H.9 | Pindah fase: admin `PATCH /siklus/{siklus}/fase` `{"fase_id":"<fase grower>"}` (ID dari `GET /jenis-ayam/{id}/fase`) → `GET /notifikasi` | `PERLU_DITINJAU`; formulasi aktif berstatus `PERLU_DITINJAU`. Kembalikan ke Starter setelahnya |

## I. Isolasi antar-Pemilik (T-1, T-2, T-3, T-12)

Buat Pemilik kedua (satu perintah, jalankan di folder backend dengan venv aktif):
```bash
python -c "from sqlmodel import Session; from app.database import engine; from app.models.akses import User; from app.models.enums import PeranUser; from app.services.auth import get_password_hash as h; s=Session(engine); s.add(User(nama='Pemilik B',email='pemilikb@example.com',kata_sandi_hash=h('pemilikb123'),role=PeranUser.PEMILIK)); s.commit(); print('ok')"
```
Authorize sebagai `pemilikb@example.com` / `pemilikb123`, buat `kandang_b` (`POST /kandang`) dan alatnya, lalu:

| # | Aksi | Harapan |
|---|---|---|
| I.1 | `GET /users` | `[]` (tidak melihat Budi) |
| I.2 | `PATCH /users/{budi}/status` `{"status":"NONAKTIF"}` | **404** |
| I.3 | `POST /users/{budi}/penugasan` ke `kandang_b` | **404** (bukan Pekerjanya) |
| I.4 | `POST /users` (Pekerja baru "Candra") lalu `POST /users/{candra}/penugasan` ke **Kandang A** | **403** (bukan kandangnya) |
| I.5 | `GET /kandang/{kandang}` | **403** |
| I.6 | `POST /alat/{alat_b}/wadah` `{"nomor_wadah":1,"bahan_pakan_id":"<bahan_jagung milik A>"}` | **404** |
| I.7 | Sebagai admin: `GET /users` | Hanya Budi (tidak ada Candra) |
| I.8 | Sebagai admin: `PATCH /wadah/{wadah_jagung}` `{"bahan_pakan_id":null}` | 200, `bahan_pakan_id: null`; kembalikan dengan `{"bahan_pakan_id":"<bahan_jagung>"}` |

## J. Audit log (S-14)

Tidak ada endpoint pembacaan; cek langsung di DB:
```bash
docker exec smart-poultry-db psql -U admin -d smart_poultry -c "select aksi, entitas, nilai_lama, nilai_baru, catatan from audit_log order by waktu"
```
Harapan: baris `KOREKSI_STOK` (alasan di `catatan`), `BUAT_PENUGASAN`, `UBAH_STATUS_USER` bila dilakukan.

## Lembar hasil

| Bagian | Hasil | Catatan |
|---|---|---|
| 0 Persiapan | | |
| A Stok otomatis | | |
| B Validasi beri makan | | |
| C State machine & idempotensi | | |
| D Timeout | | |
| E Alat offline | | |
| F Stop darurat | | |
| G Stok kosong | | |
| H Peran Pekerja & notifikasi | | |
| I Isolasi antar-Pemilik | | |
| J Audit log | | |

**Fase 1 dinyatakan selesai** bila semua bagian A–J sesuai harapan tanpa 500. Hal yang memang belum ada dan tidak dihitung: T-4 (simpan formulasi mempercayai preview), S-1 (infeasible tanpa rincian), STOK_MENIPIS lewat UI (tidak ada endpoint untuk mengatur `ambang_menipis`; sudah teruji otomatis).

## K. DELETE aman dan koreksi salah input (P1)

Authorize sebagai admin (data demo). Catat `jenis_ayam`, `fase_starter`, `bahan_jagung`, `nutrisi_kalsium` dari `GET` masing-masing.

| # | Aksi | Harapan |
|---|---|---|
| K.1 | `DELETE /bahan-pakan/{bahan_jagung}` (terpasang di wadah) | **409** `masih dipakai oleh 1 wadah`; `GET /kandang/{kandang}/stok` tetap menampilkan Jagung |
| K.2 | `DELETE /nutrisi/{nutrisi_kalsium}` | **409** `... kandungan bahan pakan, ... kebutuhan fase` |
| K.3 | `DELETE /fase/{fase_starter}` dan `DELETE /jenis-ayam/{jenis_ayam}` | **409** `masih dipakai oleh 1 siklus` |
| K.4 | `POST /bahan-pakan` `{"nama":"Salah input","harga":1}` → `DELETE` bahan itu | **204**; `GET /bahan-pakan/{id}` → 404 |
| K.5 | `POST /siklus/{siklus}/populasi` `{"jenis":"MORTALITAS","jumlah":5,"tanggal":"2026-11-02"}` → `GET /kandang/{kandang}/siklus/aktif` | `jumlah_ayam` turun 5 |
| K.6 | `DELETE /siklus/{siklus}/populasi/{populasi_id}` (ID dari respons K.5) | **204**; `jumlah_ayam` kembali |
| K.7 | `PATCH /siklus/{siklus}` `{}` | **400** `Tidak ada data yang diubah` |
| K.8 | `PATCH /siklus/{siklus}` `{"jumlah_ayam":120}` | 200; bila ada formulasi aktif → `PERLU_DITINJAU` + notifikasi. Kembalikan ke jumlah semula setelahnya |
| K.9 | Sebagai Budi (Pekerja): `PATCH /siklus/{siklus}` dan `DELETE .../populasi/{id}` | **403** (hanya Pemilik) |
| K.10 | Audit: `select aksi, nilai_lama, nilai_baru from audit_log where aksi like 'HAPUS_%' or aksi = 'KOREKSI_SIKLUS'` | Baris sesuai aksi di atas |

## L. DELETE tahap P2 (siklus, formulasi, wadah, alat, kandang)

Gunakan kandang uji agar data demo utama tidak terpengaruh: `POST /kandang` `{"nama":"Kandang Hapus"}` → `POST /kandang/{id}/alat` → `POST /alat/{alat}/wadah` `{"nomor_wadah":1,"bahan_pakan_id":"<bahan_jagung>"}` (catat `kandang_h`, `alat_h`, `wadah_h`).

| # | Aksi | Harapan |
|---|---|---|
| L.1 | `POST /wadah/{wadah_h}/stok/isi-ulang` `{"jumlah":100}` → `DELETE /wadah/{wadah_h}` | **409** `Stok belum 0: wadah 1 (100.0 g). Koreksi stok ke 0 dulu` |
| L.2 | `POST /wadah/{wadah_h}/stok/koreksi` `{"jumlah_baru":0,"alasan":"salah wadah"}` → `DELETE /wadah/{wadah_h}` | **204**; `GET /kandang/{kandang_h}/stok` → `[]` |
| L.3 | `POST /alat/{alat_h}/wadah` (wadah baru) → `DELETE /alat/{alat_h}` | **204** (stok 0, belum ada perintah); `GET /kandang/{kandang_h}` → `status_alat: null` |
| L.4 | `DELETE /kandang/{kandang_h}` | **204**; `GET /kandang/{kandang_h}` → 404 |
| L.5 | Pada **Kandang A** (data demo): `DELETE /kandang/{kandang}` | **409** `masih dipakai oleh 1 siklus` |
| L.6 | Jalankan satu perintah beri makan sampai SUKSES di Kandang A, lalu `DELETE /siklus/{siklus}` | **409** `formulasinya sudah dipakai ... perintah` |
| L.7 | `DELETE /formulasi/{formulasi}` untuk formulasi yang dipakai perintah itu | **409** |
| L.8 | Formulasi percobaan baru (otomatis → simpan) lalu `DELETE /formulasi/{id_baru}` | **204**; `GET` → 404 |
| L.9 | `DELETE /alat/{alat}` (Kandang A, sudah punya perintah) | **409** `sudah punya ... perintah` |
| L.10 | Sebagai Budi (Pekerja) atau Pemilik B: `DELETE` salah satu di atas | 403 / 404 |
| L.11 | Audit: `select aksi, entitas, nilai_lama from audit_log where aksi like 'HAPUS_%' order by waktu` | `HAPUS_WADAH`, `HAPUS_ALAT`, `HAPUS_KANDANG`, `HAPUS_FORMULASI` |

> Jangan menghapus siklus **tanpa** perintah pada Kandang A kecuali Anda siap membuat ulang data demo (`python seed_demo.py` tidak akan mengisi ulang karena data sudah ada; gunakan kandang uji).
