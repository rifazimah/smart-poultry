# 05 — Risiko, Technical Debt, dan Keputusan Terbuka

## 1. Risk register
Skala: Kemungkinan (K) & Dampak (D) 1–3; skor = K×D.

| ID | Risiko | K | D | Skor | Mitigasi | Pemilik |
|---|---|---|---|---|---|---|
| RS-1 (teratasi Fase 0) | Fitur inti (formulasi/log alat) crash karena mismatch enum; baru ketahuan saat demo | 3 | 3 | 9 | Fase 0: perbaiki + smoke test otomatis | Dev backend |
| RS-2 | Frontend & simulator belum ada → demo end-to-end tak mungkin | 3 | 3 | 9 | Mulai simulator (Fase 3) segera setelah Fase 0; frontend paralel | Tim |
| RS-3 (mitigasi berjalan: 46 test) | Tidak ada test → regresi saat refactor | 3 | 2 | 6 | Fase 4 mulai dari test LP + alur beri-makan; tambah test tiap perbaikan Fase 1 | Dev backend |
| RS-4 (teratasi Fase 1) | Kebocoran data lintas-Pemilik (IDOR) saat demo multi-akun | 2 | 3 | 6 | Fase 1 prioritas T-1..T-3, T-12 + test otorisasi | Dev backend |
| RS-5 (teratasi Fase 1) | Alat tampak ONLINE padahal mati / perintah macet PENDING → demo "hang" | 2 | 3 | 6 | Lazy timeout + OFFLINE efektif | Dev backend |
| RS-6 | Perubahan skema (enum/`pemilik_id`) bertentangan dengan aturan "model final" | 2 | 2 | 4 | Minta persetujuan eksplisit; migrasi Alembic autogenerate | Product owner |
| RS-7 | Estimasi waktu frontend meleset (tim kecil, 1 bulan) | 3 | 2 | 6 | Potong UI ke alur demo saja (lihat roadmap Fase 5), pakai komponen siap pakai | Tim |
| RS-8 (sebagian: Dockerfile + CI siap, staging online ditunda, lihat D-10) | Deploy demo tertunda karena platform belum dipilih | 2 | 2 | 4 | Putuskan di akhir Fase 2; siapkan Dockerfile lebih awal | Tim |
| RS-9 | Data nutrisi salah satuan membuat LP infeasible tanpa petunjuk | 2 | 2 | 4 | Seed data demo tervalidasi + pesan diagnosis (S-1) | Dev backend |

## 2. Technical debt (urut prioritas bayar)
1. Mismatch enum (K-1..K-3) — blocking.
2. Tidak ada test otomatis.
3. Tenant isolation inkonsisten (helper `get_entity_or_404` hanya di masterdata; logika serupa di tempat lain tidak ada).
4. Logika status siklus-hidup tersebar (router siklus, service formulasi) → pusatkan di service.
5. Dependency antar-lapisan salah arah (`services/formulasi.py` mengimpor `routers/siklus.py`).
6. Konfigurasi hardcode (heartbeat interval, `echo`, secret).
7. Dokumen tersebar → **sudah dirapikan ke `docs/`**; perlu dijaga tetap sinkron dengan kode.
8. Deprecation: `datetime.utcnow()`, `class Config` Pydantic.

## 3. Keputusan terbuka (butuh jawaban tim/PO)
| # | Keputusan | Opsi | Rekomendasi |
|---|---|---|---|
| D-1 | Representasi formulasi "aktif" (K-2) | A: tambah `AKTIF/NONAKTIF` ke enum + migrasi; B: tanpa migrasi, aktif = terbaru VALID; C: kolom boolean `aktif` | **DIPUTUSKAN: C** — kolom boolean `aktif` (1 Nov 2026), sudah diterapkan |
| D-2 | Relasi Pemilik→Pekerja (T-3) | Tambah `User.pemilik_id` / hanya via penugasan | **DIPUTUSKAN & DITERAPKAN:** `pemilik_id` nullable, diisi saat `POST /users` (migrasi `3c390b676f31`) |
| D-3 | Siapa boleh formulasi & simpan (S-5) | Pemilik saja / Pemilik+Pekerja | **DIPUTUSKAN & DITERAPKAN:** Pemilik saja untuk otomatis/manual/simpan; Pekerja boleh lihat & beri makan |
| D-4 | Penanganan stok tidak cukup (T-5) | Tolak 409 / izinkan lalu `SKIPPED_STOCK` | **DIPUTUSKAN & DITERAPKAN:** tolak 409 saat membuat perintah |
| D-5 | Timeout perintah | 60 dtk PENDING, 300 dtk BERJALAN? | **DIPUTUSKAN & DITERAPKAN:** `PERINTAH_TIMEOUT_PENDING_SECONDS=60`, `PERINTAH_TIMEOUT_BERJALAN_SECONDS=300`, `ALAT_OFFLINE_AFTER_SECONDS` (0 = 3x heartbeat) |
| D-6 | Sumber template BR-13 | Tabel baru / JSON statis di kode | JSON statis (YAGNI, tanpa tabel baru) |
| D-7 | Hosting demo | Railway / Render / Fly | Render atau Railway (Postgres managed) |
| D-8 | Simulator online saat demo? | Lokal / deploy | Lokal saat presentasi + rekaman cadangan |
| D-9 | State management React | Context/TanStack Query/Redux | TanStack Query (cocok dengan pola polling) |
| D-11 | Fase 4: cakupan hardening, migrasi container, CI | — | **DIPUTUSKAN (2 Nov 2026):** login NONAKTIF + rate-limit in-memory, seed admin tanpa password bawaan di production, hash token alat; migrasi Alembic otomatis saat container start; CI = lint + migrasi + test (tanpa build image) |
| D-10 | Database untuk tim | Satu DB bersama (Supabase/VPS) / DB lokal per anggota | **DIPUTUSKAN (2 Nov 2026): DB lokal (Docker) per anggota**; panduan lengkap di [setup-backend](../panduan/setup-backend.md). Staging online (Supabase + hosting backend) ditunda sampai ada kebutuhan demo bersama; saat itu pakai DB staging terpisah dari DB lokal dan jangan dipakai untuk test |
