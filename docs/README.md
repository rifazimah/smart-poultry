# Dokumentasi Smart Poultry

Semua dokumen proyek berada di folder ini. Baca berurutan bila baru bergabung.

| Folder / file | Isi | Untuk siapa |
|---|---|---|
| [00-ringkasan-eksekutif.md](00-ringkasan-eksekutif.md) | Status, kesiapan, 5 hal terpenting, rekomendasi | Semua |
| [analisis/01-analisis-kebutuhan.md](analisis/01-analisis-kebutuhan.md) | Aktor, use case, FR/NFR, aturan bisnis, keterlacakan | Analis, PO |
| [analisis/02-analisis-arsitektur-dan-data.md](analisis/02-analisis-arsitektur-dan-data.md) | Arsitektur, ERD, state machine, sequence, LP, keamanan | Developer |
| [analisis/03-review-kode.md](analisis/03-review-kode.md) | Temuan review kode (severity, file:baris, perbaikan) | Developer |
| [analisis/04-gap-analysis-api.md](analisis/04-gap-analysis-api.md) | Kontrak API vs implementasi | Developer, FE |
| [analisis/05-risiko-dan-technical-debt.md](analisis/05-risiko-dan-technical-debt.md) | Risiko, utang teknis, keputusan terbuka | Tim, PO |
| [analisis/06-analisis-endpoint-delete.md](analisis/06-analisis-endpoint-delete.md) | Analisis & usulan endpoint DELETE | Developer, PO |
| [roadmap/ROADMAP-TAHAPAN-BERIKUTNYA.md](roadmap/ROADMAP-TAHAPAN-BERIKUTNYA.md) | Fase 0–6 menuju selesai | Semua |
| [spesifikasi/PRD-MVP.md](spesifikasi/PRD-MVP.md) | Cakupan & definisi selesai MVP | Semua |
| [spesifikasi/ARCHITECTURE.md](spesifikasi/ARCHITECTURE.md) | Komponen, alur data, keputusan teknis final | Developer |
| [spesifikasi/API_CONTRACT.md](spesifikasi/API_CONTRACT.md) | Kontrak endpoint | Developer, FE |
| [spesifikasi/CONVENTIONS.md](spesifikasi/CONVENTIONS.md) | Aturan kode (hashing, LP, struktur) | Developer |
| [panduan/setup-backend.md](panduan/setup-backend.md) | Menjalankan DB, migrasi, server | Developer |
| [panduan/smoke-test-swagger.md](panduan/smoke-test-swagger.md) | Skenario smoke test lewat Swagger UI | Developer, QA |
| [panduan/smoke-test-fase-1.md](panduan/smoke-test-fase-1.md) | Smoke test khusus perilaku baru Fase 1 | Developer, QA |
| [panduan/simulator.md](panduan/simulator.md) | Simulator alat IoT (cara pakai, opsi, skenario demo) | Developer, QA |
| [panduan/AGENTS.md](panduan/AGENTS.md) | Aturan untuk AI coding agent | Agent/Developer |

## Aturan pemeliharaan
- Dokumen baru `.md` ditaruh di `docs/` (tidak di folder kode).
- Ubah kontrak/arsitektur → perbarui `spesifikasi/` pada PR yang sama.
- Setelah tiap fase roadmap selesai, perbarui status di `analisis/03` dan `analisis/04`.
- Catatan: alat yang otomatis membaca `AGENTS.md`/`README.md` dari root tidak akan menemukannya lagi; arahkan alat tersebut ke `docs/panduan/AGENTS.md`.
