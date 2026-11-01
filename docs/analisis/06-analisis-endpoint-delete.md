# 06 — Analisis Endpoint DELETE

Tanggal: 1 November 2026 · Pemicu: pengguna ingin bisa menghapus data yang salah input.
Status: **usulan, belum diimplementasi** — menunggu keputusan di bagian 6. (AGENTS.md melarang menambah endpoint di luar kontrak tanpa bertanya.)

## 1. Kondisi sekarang

DELETE hanya ada untuk master data (`jenis-ayam`, `fase`, `nutrisi`, `bahan-pakan`) dan `penugasan` (soft: status `BERAKHIR`).
Tidak ada DELETE untuk kandang, alat, wadah, siklus, perubahan populasi, formulasi, pekerja, dan notifikasi.

**Empat DELETE yang sudah ada tidak aman** (dibuktikan dengan test sementara di database test, 1 Nov 2026):

| Aksi | Hasil | Dampak |
|---|---|---|
| Hapus bahan pakan yang terpasang di wadah | **204 sukses** | Wadah diam-diam kehilangan bahannya (`bahan_pakan_id` jadi `NULL`); stok jadi tanpa nama; formulasi aktif tidak lagi bisa dipakai tanpa penjelasan |
| Hapus nutrisi yang dipakai kandungan/kebutuhan/hasil formulasi | **500** | Error `IntegrityError` mentah |
| Hapus fase yang dipakai siklus | **500** | idem |
| Hapus jenis ayam yang dipakai siklus | **500** | idem |

Ini sama dengan temuan S-15 di [03-review-kode](03-review-kode.md), tetapi lebih serius karena kasus pertama merusak data tanpa error.

## 2. Prinsip

1. **Salah input diperbaiki dengan cara paling ringan:** edit (PATCH) bila bisa; hapus keras hanya bila tidak ada yang bergantung; entitas yang punya riwayat → ditolak `409` dengan petunjuk (mis. "pakai PATCH status NONAKTIF").
2. **Riwayat dan jejak audit tidak boleh dihapus:** `Perintah`, `LogEksekusi`, `TransaksiStok`, `AuditLog`. Salah isi stok diperbaiki dengan **koreksi** (sudah ada), bukan menghapus transaksi.
3. **Hanya Pemilik** yang boleh menghapus; Pekerja tidak pernah. Semua tetap di-scope ke Pemilik (404/403 untuk milik orang lain).
4. **Tidak ada penghapusan diam-diam:** bila dipakai, balas `409` dengan rincian (`"Bahan dipakai di 2 wadah dan 1 formulasi"`).
5. **Setiap penghapusan keras ditulis ke `AuditLog`** (`HAPUS_<ENTITAS>`, ringkasan nilai lama).
6. Tidak menambah kolom `deleted_at`/arsip dulu (YAGNI, ubah skema); evaluasi ulang bila frontend membutuhkan "arsip".

## 3. Peta ketergantungan (FK) yang menentukan aturan

```
user ─< kandang ─< siklus ─< perubahan_populasi            (cascade)
              │         └─< formulasi ─< formulasi_item / formulasi_nutrisi_hasil  (cascade)
              │                  └─< perintah ─1 log_eksekusi
              ├─1 alat ─< wadah ─1 stok ; wadah ─< transaksi_stok
              │      └─< perintah
              └─< penugasan_kandang
user ─< jenis_ayam ─< fase ─1 standar_konsumsi ; fase ─< kebutuhan_nutrisi_fase
user ─< nutrisi ;  user ─< bahan_pakan ─< kandungan_nutrisi_bahan
referensi dari data operasional: siklus→jenis_ayam,fase ; formulasi_item→bahan ; hasil→nutrisi ; wadah→bahan
```

## 4. Rekomendasi per resource

### 4.1 Perbaiki yang sudah ada (prioritas P1 — ini bug)

| Endpoint | Aturan baru |
|---|---|
| `DELETE /bahan-pakan/{id}` | `409` bila terpasang di wadah **atau** dipakai `formulasi_item`; kandungan nutrisinya ikut terhapus (definisi bahan sendiri) |
| `DELETE /nutrisi/{id}` | `409` bila dipakai `kandungan_nutrisi_bahan`, `kebutuhan_nutrisi_fase`, atau `formulasi_nutrisi_hasil` (lepas dulu lewat `PUT .../nutrisi` / `PUT .../kebutuhan-nutrisi`) |
| `DELETE /fase/{id}` | `409` bila dipakai siklus (status apa pun); standar konsumsi & kebutuhan ikut terhapus |
| `DELETE /jenis-ayam/{id}` | `409` bila dipakai siklus; fase turunannya ikut terhapus (cascade yang sudah ada) |

### 4.2 Endpoint baru

| Prioritas | Endpoint | Untuk kasus salah input | Aturan |
|---|---|---|---|
| **P1** | `DELETE /siklus/{id}/populasi/{pid}` | Salah catat mortalitas/panen/penambahan | Hanya siklus `AKTIF`. Efek dibalik pada `jumlah_ayam` (MORTALITAS/PANEN → ditambah; PENAMBAHAN → dikurangi; tidak boleh < 0). Audit |
| **P1** | `PATCH /siklus/{id}` `{jumlah_ayam?, tanggal_mulai?}` *(bukan DELETE, tetapi solusi utama salah input siklus)* | Salah jumlah awal/tanggal | Hanya siklus `AKTIF`; `jumlah_ayam` menggantikan nilai saat ini; formulasi aktif ditandai `PERLU_DITINJAU` (berat per sesi bergantung populasi) + notifikasi |
| P2 | `DELETE /siklus/{id}` | Siklus salah jenis ayam / salah kandang | `409` bila ada `perintah` yang memakai formulasi siklus ini; selain itu populasi + formulasi (item/hasil) ikut terhapus. Siklus yang sudah berjalan → pakai `/selesai` |
| P2 | `DELETE /formulasi/{id}` | Formulasi percobaan | `409` bila dipakai `perintah`; item/hasil ikut terhapus. Bila yang dihapus `aktif`, siklus tidak punya formulasi aktif sampai disimpan ulang |
| P2 | `DELETE /wadah/{id}` | Wadah salah nomor/tidak jadi dipakai | `409` bila ada transaksi `PENGELUARAN` (sudah pernah dipakai makan); stok & transaksi `ISI_ULANG`/`KOREKSI_MANUAL` ikut terhapus; formulasi aktif yang memakai bahannya → `PERLU_DITINJAU` + notifikasi |
| P2 | `DELETE /alat/{id}` | Alat salah daftar/diganti | `409` bila ada `perintah`; wadah+stok ikut terhapus (cascade yang sudah ada) |
| P2 | `DELETE /kandang/{id}` | Kandang salah input | `409` bila ada siklus atau perintah (gunakan `PATCH status=NONAKTIF`); penugasan, alat, wadah, stok ikut terhapus |
| P3 | `DELETE /users/{id}` (Pekerja) | Salah email/nama | **Tidak disarankan.** Pekerja cepat punya jejak (notifikasi, perintah, transaksi, audit). Pakai `PATCH /users/{id}/status` → `NONAKTIF`. Alternatif: hapus keras hanya bila belum punya jejak apa pun — lihat keputusan K-2 |
| P3 | `DELETE /notifikasi/{id}` | Bersihkan daftar | Hanya milik sendiri; nilai kecil, tunda sampai frontend butuh |
| — | `DELETE` perintah, log, transaksi stok, audit log | — | **Tidak disediakan** (riwayat/jejak audit) |

## 5. Rencana implementasi (bila disetujui)

- `app/services/hapus.py`: helper `hitung_referensi(session, [(Model, kondisi, label)])` → daftar `"2 wadah"`, `"1 formulasi"`; `pastikan_tidak_dipakai(...)` melempar `409` berisi rincian.
- Setiap endpoint: ambil entitas dengan scope Pemilik (pakai `get_entity_or_404`/`_get_kandang_or_404`), cek referensi, tulis `AuditLog`, `commit`, `204`.
- Cascade manual untuk tabel tanpa `cascade` di model (mis. `TransaksiStok` milik wadah, `Perintah`-less cleanup) — ditulis eksplisit di service, **tanpa mengubah skema**.
- Test per endpoint: bebas → `204` (+ baris benar-benar hilang, baris terkait ikut/ tidak ikut sesuai aturan), dipakai → `409` dengan pesan, milik Pemilik lain → `404/403`, Pekerja → `403`, audit tercatat.
- Perbarui `API_CONTRACT.md` (bagian 2–5), `04-gap-analysis`, dan skenario smoke test.
- Estimasi: P1 ±½ hari, P2 ±1 hari, P3 sesuai keputusan.

## 6. Keputusan yang diperlukan

| # | Pertanyaan | Rekomendasi |
|---|---|---|
| K-1 | Master data yang dipakai: tolak `409` (strict) atau izinkan `?cascade=true` yang ikut menghapus kandungan/kebutuhan? | **Strict dulu.** Cascade pada definisi dapat mengubah perhitungan formulasi tanpa disadari |
| K-2 | Pekerja: hanya nonaktifkan, atau boleh hapus keras bila belum punya jejak? | Hanya nonaktifkan untuk MVP |
| K-3 | Setuju menambah `PATCH /siklus/{id}` (di luar permintaan DELETE) untuk koreksi jumlah/tanggal? | Ya — lebih tepat daripada menghapus siklus |
| K-4 | Hapus wadah yang masih berstok > 0: izinkan (stok hilang bersama wadah) atau wajib dikoreksi ke 0 dulu? | Wajib dikoreksi ke 0 dulu agar jumlah fisik tercatat |
| K-5 | Cakupan implementasi awal | P1 (perbaiki 4 DELETE + hapus populasi + PATCH siklus), P2 menyusul |
