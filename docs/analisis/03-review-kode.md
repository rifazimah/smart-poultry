# 03 — Review Kode (perspektif Senior Developer)

Cakupan: seluruh `smart-poultry-backend/app/` (±4.500 baris), `alembic/`, `docker-compose.yml`.
Metode: pembacaan manual + `grep` untuk membuktikan setiap temuan. Nomor baris mengacu pada kondisi commit `9864a8b`.
Kode **belum dijalankan end-to-end** pada saat review; temuan KRITIS bersifat pasti dari pembacaan statis
(atribut enum tidak ada di `enums.py` maupun migrasi `903f737d4420`) dan perlu dikonfirmasi lewat smoke test (Fase 0 roadmap).

Legenda severity: **K** = Kritis (fitur inti gagal / data salah), **T** = Tinggi, **S** = Sedang, **R** = Rendah.

## A. Ringkasan penilaian

| Aspek | Penilaian | Catatan |
|---|---|---|
| Struktur & konvensi | Baik | Layering router → service → model konsisten; schema terpisah dari tabel; password tidak bocor |
| Kesesuaian kontrak API | Sedang | ±85% endpoint ada; template (BR-13) & paginasi belum |
| Kebenaran logika inti | **Kurang** | 3 mismatch enum membuat simpan-formulasi & log alat crash |
| Keamanan / otorisasi | **Kurang** | Beberapa IDOR antar-Pemilik, tidak ada relasi Pemilik→Pekerja |
| Ketahanan (idempotensi, state machine) | Kurang | Tidak ada TIMEOUT, OFFLINE detection, validasi transisi |
| Testabilitas | **Belum ada** | 0 test; logika LP ada di service (bagus untuk di-test) |
| Operasional | Sedang | Compose DB ada; belum ada Dockerfile backend/CI/logging terstruktur |

## B. Temuan

> **T-4 selesai (1 Nov 2026):** `POST /formulasi` kini hanya memakai komposisi dari klien dan menghitung ulang semua nilai di server. Temuan baru tentang DELETE: lihat [06](06-analisis-endpoint-delete.md).

> **Pembaruan 1 Nov 2026 (branch `fitur/fase-1-logika-inti`):** temuan bertanda ✅ sudah diperbaiki dan diuji
> (`pytest`, 46 test). Masih terbuka: S-1..S-4, S-6..S-8, S-10, S-11, S-15, S-16, dan seluruh R-*.
> Catatan T-10: `berat_aktual` belum dipakai untuk koreksi stok (stok dikurangi menurut `berat_per_sesi`).

### Kritis

| ID | Lokasi | Temuan | Dampak | Perbaikan |
|---|---|---|---|---|
| K-1 ✅ *diperbaiki 1 Nov 2026* | `services/formulasi.py:98,100,201,265` | Memakai `StatusNutrisi.TIDAK_SESUAI`; enum hanya `KURANG/SESUAI/BERLEBIH` (`models/enums.py`, migrasi baris 253) | `AttributeError` pada **setiap** formulasi manual dan hampir setiap otomatis → fitur inti tidak jalan | Pakai `KURANG` bila `< batas_min`, `BERLEBIH` bila `> batas_max`; "tidak sesuai" = status ≠ `SESUAI` |
| K-2 ✅ *diperbaiki 1 Nov 2026: kolom `Formulasi.aktif` + migrasi `b7c1a2d93e5f`* | `services/formulasi.py:311,315,324`; `routers/siklus.py:124,193,197` | Memakai `StatusFormulasi.AKTIF/NONAKTIF`; enum hanya `VALID/TIDAK_SEMPURNA/PERLU_DITINJAU` | Simpan formulasi, pindah fase, dan selesaikan siklus → `AttributeError` | Opsi A: tambah nilai `AKTIF`,`NONAKTIF` ke enum + migrasi Alembic (ALTER TYPE). Opsi B (tanpa migrasi): tandai "aktif" = formulasi terbaru berstatus `VALID`; `PERLU_DITINJAU` tetap. **Perlu keputusan tim** — lihat dok 05 |
| K-3 ✅ *diperbaiki 1 Nov 2026* | `services/device.py:74` | `JenisNotifikasi.SISTEM` / `.ALARM` tidak ada (enum: `PERINTAH_SUKSES`, `PERINTAH_GAGAL`, …) | `/device/perintah/{id}/log` crash **setelah** status & stok diubah di session tetapi sebelum commit → perintah tak pernah SUKSES | Pakai `PERINTAH_SUKSES` / `PERINTAH_GAGAL` |

### Tinggi

| ID | Lokasi | Temuan | Dampak | Perbaikan |
|---|---|---|---|---|
| T-1 ✅ *diperbaiki Fase 1, 1 Nov 2026* | `routers/users.py:96-121` | `buat_penugasan` tidak memverifikasi `kandang_id` milik Pemilik yang login (ada komentar "di-skip") | Pemilik A bisa menugaskan Pekerja ke kandang Pemilik B → pekerja dapat akses data kandang B (IDOR) | Panggil `_get_kandang_or_404(session, kandang_id, current_pemilik)`; cek duplikat penugasan aktif |
| T-2 ✅ *diperbaiki Fase 1, 1 Nov 2026* | `routers/users.py:124-137` | `akhiri_penugasan` tidak cek kepemilikan kandang dari penugasan | Pemilik mana pun bisa mengakhiri penugasan Pemilik lain | Validasi lewat `penugasan.kandang_id` |
| T-3 ✅ *diperbaiki Fase 1, 1 Nov 2026* | `models/akses.py` `User`; `routers/users.py:61-75,77-93` | Tidak ada relasi Pemilik→Pekerja (`dibuat_oleh_id`/`pemilik_id`). `GET /users` mengembalikan **semua** Pekerja seluruh sistem; `PATCH /users/{id}/status` bisa menonaktifkan pekerja Pemilik lain | Kebocoran data & sabotase lintas-tenant. Kontrak: "daftar Pekerja miliknya" | Tambah kolom `pemilik_id` nullable di `user` (migrasi) → perlu persetujuan karena `CONVENTIONS` menyatakan model final. Alternatif tanpa skema: batasi via `penugasan_kandang` ⨝ `kandang.pemilik_id` (pekerja tanpa penugasan tak terlihat) |
| T-4 ✅ *diperbaiki 1 Nov 2026* | `services/formulasi.py:278-339`, `routers/formulasi.py:70` | `POST /formulasi` menyimpan `FormulasiPreview` dari klien apa adanya (proporsi, biaya, status, nutrisi) | Klien bisa menyimpan formulasi "VALID" palsu lalu mengirim ke alat; `nutrisi_id` & `bahan_pakan_id` tak divalidasi kepemilikannya | Hitung ulang server-side dari `mode` + `item` (bandingkan toleransi), atau simpan hanya hasil kalkulasi server |
| T-5 ✅ *diperbaiki Fase 1, 1 Nov 2026* | `routers/perintah.py:23-65` | `formulasi_id` tidak divalidasi: ada? milik siklus aktif kandang ini? status layak (bukan `TIDAK_SEMPURNA`/`PERLU_DITINJAU`)? Dan tidak cek kecukupan stok | Perintah menunjuk formulasi kandang lain / formulasi tak valid; alat diperintah mengeluarkan pakan yang stoknya kosong | Validasi + cek `Stok >= berat_per_sesi` per item (409 / atau `SKIPPED_STOCK`) |
| T-6 ✅ *diperbaiki Fase 1, 1 Nov 2026* | `routers/kandang.py:196-218` + `routers/stok.py:66-74` | `Stok` baru dibuat *lazy* saat endpoint stok dipanggil, bukan saat `Wadah` dibuat | `proses_log_eksekusi` (`services/device.py:44-47`) men-skip pengurangan stok diam-diam bila belum ada baris `Stok`; `GET /kandang/{id}/stok` tidak menampilkan wadah tanpa baris Stok | Buat `Stok` bersama `Wadah` (satu transaksi); backfill via migrasi data |
| T-7 ✅ *diperbaiki Fase 1, 1 Nov 2026* | `routers/device.py:30-56`, tidak ada job | `Alat.status` hanya berubah saat heartbeat; tidak ada deteksi heartbeat kedaluwarsa | Alat mati tetap tampil `ONLINE`; cek "alat OFFLINE → 409" di `perintah.py:34` tak pernah relevan setelah heartbeat pertama; notifikasi `ALAT_OFFLINE` tak pernah ada | Hitung efektif: `status=OFFLINE` bila `now - waktu_terakhir_sinkron > 3×interval` (di read path & saat beri-makan). Tanpa Celery (sesuai keputusan arsitektur) |
| T-8 ✅ *diperbaiki Fase 1, 1 Nov 2026* | seluruh `Perintah` | Tidak ada TIMEOUT: status `TIMEOUT` ada di enum tetapi tak pernah di-set. Perintah `PENDING` yang tak diambil memblokir alat selamanya (cek `perintah.py:41-49`) | Alat "macet" – tak bisa beri makan lagi sampai DB diubah manual | Lazy-expire: saat membuat perintah / membaca, tandai `PENDING/DIAMBIL/BERJALAN` yang lebih tua dari N detik jadi `TIMEOUT` + notifikasi |
| T-9 ✅ *diperbaiki Fase 1, 1 Nov 2026* | `routers/device.py:59-91` | `ambil`/`mulai` tak memvalidasi transisi; `mulai` dari `PENDING` melompati `DIAMBIL`; perintah terminal (SUKSES/GAGAL/TIMEOUT) bisa di-log ulang; `STOP_DARURAT` tak mengubah/menghentikan perintah yang sedang berjalan | State machine PRD (PENDING→DIAMBIL→BERJALAN→SUKSES/GAGAL/TIMEOUT) tak ditegakkan | Tabel transisi legal di service; STOP_DARURAT membatalkan perintah aktif (→ `GAGAL`) |
| T-10 ✅ *diperbaiki Fase 1, 1 Nov 2026* | `services/device.py:16-23`, `routers/device.py:94-110` | Idempotensi memeriksa `id_eksekusi_unik` secara global (bukan per perintah) dan endpoint selalu 201; kontrak: duplikat → 200 dengan log lama. `berat_aktual` dan `SKIPPED_STOCK` tidak dipakai (status ≠ SUKSES selalu jadi `GAGAL`) | Replay memberi 201 ganda; id yang sama untuk perintah lain mengembalikan log perintah lain | Cek `(perintah_id, id_eksekusi_unik)`; set `response.status_code=200` saat duplikat; tangani `SKIPPED_STOCK` |
| T-11 ✅ *diperbaiki Fase 1, 1 Nov 2026* | `services/device.py:68-81` | Notifikasi hanya ke `dibuat_oleh_id`; tidak ada notifikasi `STOK_MENIPIS/KOSONG`, `ALAT_OFFLINE/ERROR`, `PERLU_DITINJAU` (padahal enum & PRD #8 memintanya); `Stok.ambang_menipis` tak pernah dipakai | Pemilik tak diberi tahu bila Pekerja yang menekan tombol; fitur notifikasi dasar tidak lengkap | Helper `notify(session, kandang, jenis, …)` → Pemilik + pekerja ditugaskan; panggil dari log, pindah fase, stok |
| T-12 ✅ *diperbaiki Fase 1, 1 Nov 2026* | `routers/kandang.py:196-247` | `bahan_pakan_id` pada `create_wadah`/`update_wadah` tidak divalidasi kepemilikannya (milik Pemilik lain bisa dipasang); `update_wadah` tidak bisa melepas bahan (`None` diabaikan, baris 244) | Cross-tenant reference; tak bisa mengosongkan wadah (kontrak T4: "dilepas dari wadah") | Validasi `get_entity_or_404(BahanPakan, …)`; pakai `exclude_unset` agar `null` eksplisit berlaku |

### Sedang

| ID | Lokasi | Temuan | Perbaikan |
|---|---|---|---|
| S-1 | `services/formulasi.py:186-197` | Infeasible LP mengembalikan `nutrisi_hasil=[]` dan pesan generik; kontrak & CONVENTIONS §2.5 meminta daftar nutrisi yang tak terpenuhi | Saat infeasible, hitung diagnosis per nutrisi (mis. maksimum yang bisa dicapai per nutrisi dengan LP satu-nutrisi) atau minimal sebut nutrisi berbatas |
| S-2 | `services/formulasi.py:130-140` | `kebutuhan` kosong → 400, tetapi `bahan` tanpa baris kandungan untuk suatu nutrisi diperlakukan 0 tanpa peringatan | Beri peringatan di `pesan` bila data kandungan tidak lengkap |
| S-3 | `services/formulasi.py` (`_evaluate_nutrisi`) | Satuan `nilai_per_kg` bahan vs batas kebutuhan (% atau kkal/kg) tidak dinormalisasi atau divalidasi | Dokumentasikan: satuan harus sama per nutrisi; validasi/peringatan di master data |
| S-4 | `services/formulasi.py:1-4,279` | Import tak teratur di atas file; `simpan_formulasi_service` meng-import dari `app.routers.siklus` (service → router, risiko circular) | Pindahkan `_get_siklus_or_404` ke service/dependency bersama |
| S-5 ✅ *diperbaiki Fase 1, 1 Nov 2026* | `routers/formulasi.py` | Semua endpoint formulasi memakai `get_current_user` – Pekerja bisa membuat/menyimpan formulasi. PRD: Pemilik "menjalankan formulasi" | Putuskan: batasi simpan/otomatis ke Pemilik (ubah ke `get_current_pemilik`) atau dokumentasikan Pekerja boleh |
| S-6 | `routers/siklus.py:101-115` | `catat_perubahan_populasi`: `jumlah` tak divalidasi `>0`; validasi `jumlah_ayam<0` terjadi setelah mutasi objek (rollback otomatis karena tak commit, tetapi rapuh); siklus pada kandang `NONAKTIF` tetap bisa dibuat | Validasi di schema (`gt=0`) dan sebelum mutasi |
| S-7 | `routers/siklus.py:34-53` | `create_siklus` tak cek `kandang.status == AKTIF`; fase tak dibandingkan dengan umur ayam | Tambah cek status; umur→fase boleh ditunda |
| S-8 | `routers/*` list endpoint | Paginasi `?skip&limit` (kontrak) tak ada di semua list | Dependency `Pagination` bersama (default 20, maks 100) |
| S-9 ✅ *diperbaiki* | `routers/device.py:56` | `heartbeat_interval_seconds=10` hardcode padahal ada `settings.device_heartbeat_interval_seconds` | Pakai settings |
| S-10 | `services/auth.py:31-33` | `datetime.utcnow()` deprecated (Python 3.12); `sub=email` rawan bila email diubah | `datetime.now(timezone.utc)`; pertimbangkan `sub=user.id` |
| S-11 | `routers/auth.py:36-48` | Login tidak menolak `NONAKTIF` (baru ditolak di request berikutnya, 403); `WAJIB_GANTI_SANDI` tak ditegakkan; tak ada rate-limit | Tolak di login; paksa ganti sandi; rate-limit sederhana bila perlu |
| S-12 ✅ *diperbaiki (`SQL_ECHO`)* | `database.py:7` | `echo=True` (komentar menyuruh dimatikan sebelum demo) – log SQL berisik & bocor data | Jadikan setting `SQL_ECHO` default `False` |
| S-13 ✅ *diperbaiki (CORS, `CORS_ORIGINS`)* | `main.py` | Tidak ada CORS → React (origin berbeda) akan diblok browser | `CORSMiddleware` dengan origin dari settings |
| S-14 ✅ *diperbaiki Fase 1, 1 Nov 2026* | `models/akses.py` `AuditLog` | Tabel ada, tak pernah ditulis (BR-03/BR-34: koreksi stok, penugasan, perubahan status) | Tulis audit di koreksi stok, penugasan, nonaktifkan user |
| S-15 | `routers/masterdata.py` DELETE | Hapus `BahanPakan` yang terpasang di wadah / dipakai `FormulasiItem`, atau `Nutrisi` yang dipakai → `IntegrityError` 500 | Cek referensi → 409 dengan pesan |
| S-16 | `config.py:9` | `jwt_secret` default `"ganti-ini-di-.env"` – app tetap jalan dengan secret lemah | Gagal start bila production & secret default |

### Rendah / kebersihan

| ID | Temuan |
|---|---|
| R-1 | `docker-compose.yml`: key `version: "3.9"` obsolete di Compose v2; kredensial `admin/popuri123` hardcode & juga ada di `.env.example` (dev saja – beri catatan, jangan dipakai di demo publik). |
| R-2 | `seed_admin.py` mencetak kredensial default (`admin123`); cukup untuk dev, hindari di demo online. |
| R-3 | Tidak ada logging terstruktur/`request_id`; tidak ada `/health` yang menyentuh DB. |
| R-4 | `from_attributes` memakai `class Config` (Pydantic v2 → `model_config = ConfigDict(from_attributes=True)`), muncul sebagai deprecation warning. |
| R-5 | Docstring/komentar bercampur Indonesia–Inggris; wajar untuk tim, tapi tetapkan satu bahasa di CONVENTIONS. |
| R-6 | Beberapa endpoint melakukan query berulang per-item (N+1 kecil di `services/device.py` loop item); aman untuk skala MVP. |

## C. Hal yang sudah baik (pertahankan)
- Pemisahan `models / schemas / routers / services` rapi; `UserPublic` tidak membocorkan `kata_sandi_hash`.
- Dua jalur autentikasi (JWT vs `X-Device-Token`) terpisah sesuai ARCHITECTURE; `swagger-login` disembunyikan dari schema.
- LP memakai `scipy.optimize.linprog(method="highs")` dengan constraint sesuai CONVENTIONS §2 (equality Σ=1, batas min/max, `batas_maksimum` per bahan).
- Skema DB ternormalisasi, FK + index lengkap, unik `device_token`, `command_id`, `id_eksekusi_unik`; satu migrasi Alembic bersih.
- Pengecekan akses kandang terpusat di `_get_kandang_or_404` (Pemilik vs Pekerja ditugaskan).
- Kontrak API terdokumentasi baik dan sebagian besar diikuti.

## D. Bukti verifikasi yang disarankan (jalankan di Fase 0)
```bash
cd smart-poultry-backend
grep -rn "TIDAK_SESUAI\|StatusFormulasi.AKTIF\|StatusFormulasi.NONAKTIF\|JenisNotifikasi.SISTEM\|JenisNotifikasi.ALARM" app
python -c "from app.models.enums import StatusNutrisi; print(list(StatusNutrisi))"
```
Lalu smoke test: login → buat nutrisi/bahan/jenis/fase → kandang+alat+wadah → siklus → `POST /siklus/{id}/formulasi/manual` (harus 500 karena K-1).
