# 07 — Analisis Frontend: Smart Poultry vs referensi Smart-Ransum

Tanggal: 2 November 2026 · Status: **analisis sebelum coding; belum ada kode frontend**.
Referensi: `smart-poultry-zumar/frontend` (repo lain, **hanya acuan desain** — tidak disalin). Backend kita dibaca dari kode di `main` (76 operasi API, OpenAPI).

## 1. Kesimpulan singkat

1. **Referensi adalah produk yang berbeda** (Smart-Ransum: riset tugas akhir tentang optimasi ransum ayam KUB dengan perbandingan solver LP/HOA/DBO, tanpa kandang, alat IoT, siklus, atau perintah). Yang layak diambil adalah **pola UX dan tata letak**, bukan fiturnya.
2. **Yang layak diadopsi:** alur terpandu untuk formulasi (pilih fase → populasi → konfirmasi → hasil), kartu KPI, tabel resep dengan total, modal evaluasi nutrisi, banner situasi khusus (alternatif/parsial), format Rupiah/angka `id-ID`, pola CRUD master data berbasis modal.
3. **Yang tidak diikuti:** URL API di-hardcode (dan salah path untuk kita), `alert()` sebagai penanganan galat, halaman 1.000 baris, tidak ada cache/tipe/test, sidebar tetap 256 px tanpa mode ponsel, Dockerfile menjalankan dev server, logo institusi Telkom/BRIN, halaman perbandingan solver.
4. **Domain kita jauh lebih luas** → butuh 10+ layar yang tidak ada di referensi (kandang, alat/wadah, siklus/populasi, beri makan dengan polling status, notifikasi, pekerja/penugasan) dan pengeditan data nutrisi yang **dinamis** (referensi memakai kolom tetap protein/energi/kalsium/fosfor).
5. **API kita belum cukup untuk UI penuh:** ada 8 celah (7 di antaranya operasi baca) yang membuat sebagian layar tidak bisa dibuat, mis. membaca kebutuhan nutrisi fase, riwayat populasi, dan daftar penugasan. Ini harus ditutup di backend sebelum/selama layar terkait dibuat (bagian 8).
6. **Rekomendasi stack:** Vite + React + **TypeScript** + Tailwind v4 (sama dengan acuan, agar tim familier) ditambah **TanStack Query**, tipe otomatis dari OpenAPI, dan komponen aksesibel berbasis Radix. Letakkan di `frontend/` pada monorepo ini.

## 2. Profil referensi (hasil membaca kode)

| Aspek | Temuan |
|---|---|
| Stack | React 19, Vite, Tailwind v4 (`@tailwindcss/vite`), React Router 7, Axios, lucide-react; **JavaScript** (tanpa TypeScript), lint `oxlint`; tanpa test |
| Struktur | `src/{auth,components,layouts,pages,pages/master,utils}`; 8 halaman; ada dua berkas `AppLayout` (duplikat) |
| Halaman | Login, Dashboard (3 KPI + 2 tautan cepat), **Formulasi** (1.003 baris), Inventory (edit stok inline), Riwayat (daftar + detail), Master Bahan Pakan (CRUD modal), Master Fase Ayam (CRUD modal), Komparasi Solver (779 baris, riset TA) |
| Auth | `POST /api/auth/login` **form-urlencoded**, token di `localStorage`, `GET /api/auth/me` saat muat; peran `MASTER`/`USER` (username); `ProtectedRoute` di sisi klien; respons 401 **tidak ditangani global** (ada komentar kosong) |
| API client | `axios.create({ baseURL: 'http://localhost:8000/api' })` **hardcode**, dan `AuthProvider` memanggil URL penuh sendiri (dua tempat); tidak ada env var untuk URL |
| Data | `useEffect` + `useState` per halaman; tanpa cache, tanpa batalkan request, tanpa invalidasi setelah mutasi (memanggil ulang manual) |
| Galat | `alert(...)` dan `console.error` (39 pemakaian `alert/confirm/console/localStorage`); pesan dari `err.response.data.detail` |
| Desain | Merah institusi `#E31E24`, kartu putih `rounded-2xl/3xl`, badge pil, font sistem; header atas dengan logo Telkom → FTE → BRIN; sidebar kiri `w-64` tetap (`ml-64`), **tidak responsif** |
| Alur Formulasi | `SELECT_PHASE → CALCULATING → RESULT`; modal populasi (dengan tombol tambah cepat) → modal konfirmasi → hasil: banner alternatif/parsial/gagal, 4 kartu KPI, tabel resep (bahan, harga, takaran kg, proporsi %, subtotal) + total, modal evaluasi nutrisi, tombol "Konfirmasi Produksi" (memotong stok) |
| Operasional | Docker Compose dengan `frontend` yang menjalankan `npm run dev --host` (bukan build produksi); backend `--reload` dengan volume |
| Backend pasangannya | FastAPI + SQLAlchemy + PuLP; `/api/{auth,bahan-pakan,fase-ayam,kalkulasi,history}`, WebSocket `/ws`; stok per **bahan** (`stok_kg`), bukan per wadah |

## 3. Perbandingan domain dan kebutuhan UI

| Aspek | Smart-Ransum (referensi) | Smart Poultry (kita) | Dampak pada frontend |
|---|---|---|---|
| Tujuan | Riset optimasi, perbandingan solver | Operasional kandang + alat IoT + formulasi LP | Layar operasional, bukan layar riset |
| Pengguna | `MASTER` / `USER` (username), data bersama | `PEMILIK` / `PEKERJA` (email), data per Pemilik, Pekerja per penugasan kandang | Navigasi dan tombol bergantung peran **dan** penugasan; 403/404 lintas-tenant |
| Entitas | Bahan, Fase, Riwayat | Nutrisi, Bahan (+kandungan), Jenis Ayam, Fase (+kebutuhan, +standar), Kandang, Alat, Wadah, Stok, Siklus, Populasi, Formulasi, Perintah, Notifikasi, User, Penugasan | ±14 resource, banyak relasi |
| Nutrisi | Kolom tetap (protein, energi, kalsium, fosfor) | Tabel `Nutrisi` dinamis; matriks bahan × nutrisi; kebutuhan min/maks per fase per nutrisi | Editor tabel dinamis (baris = nutrisi), bukan formulir tetap |
| Hasil formulasi | Resep per batch (kg), total biaya | Proporsi 0–1, `berat_per_sesi` (gram), biaya/kg; preview → **simpan** (snapshot, `aktif`) → beri makan | Wizard dua tahap (preview vs tersimpan); tampilkan gram/sesi |
| Aksi fisik | Tombol "produksi" memotong stok | Perintah ke alat: `PENDING → DIAMBIL → BERJALAN → SUKSES/GAGAL/TIMEOUT`, stop darurat, alat online/offline, stok dipotong oleh log alat | Layar status dengan **polling 1–2 dtk**, penanganan 409 (offline, stok, formulasi) |
| Stok | Angka per bahan, edit langsung | Per wadah; isi ulang dan **koreksi dengan alasan wajib**; riwayat transaksi tak dapat dihapus | Dua aksi terpisah + tabel riwayat |
| Real-time | WebSocket | Polling saja (keputusan arsitektur) | TanStack Query `refetchInterval` |
| Galat API | `detail` string | `detail` string atau daftar 422 FastAPI; 400/409/422/429 punya arti beda | Satu pemeta galat terpusat |
| Paginasi | Tidak ada | `?skip&limit` + header `X-Total-Count` | Komponen tabel berpaginasi |

## 4. Pola referensi: adopsi, adaptasi, tolak

| Pola referensi | Keputusan | Catatan untuk kita |
|---|---|---|
| Alur terpandu "Langkah 1 dari 3" untuk formulasi | **Adaptasi** | Langkah: pilih kandang/siklus → mode (otomatis/manual) → preview → simpan → beri makan. Tombol besar, bahasa sederhana untuk peternak |
| Kartu KPI + tabel resep + total | **Adopsi gaya** | Kolom: bahan, proporsi %, gram/sesi, subtotal biaya/kg |
| Modal evaluasi nutrisi | **Adaptasi** | Bar rentang min–maks dengan penanda nilai; warna KURANG/SESUAI/BERLEBIH; tampilkan `keterangan` dari diagnosis S-1 saat TIDAK_SEMPURNA |
| Banner (alternatif/parsial/gagal) | **Adaptasi** | Banner untuk: formulasi `PERLU_DITINJAU`, alat offline, stok kurang (409), diagnosis infeasible |
| Format `Rp` dan `toLocaleString('id-ID')` | **Adopsi** | Satu helper `format.ts` |
| CRUD master data lewat modal + tabel | **Adaptasi** | Ditambah tombol salin template, penanganan 409 saat hapus ("masih dipakai oleh ...") |
| Edit stok inline | **Tolak** | Kita wajib memisahkan isi ulang dan koreksi (alasan wajib, audit) |
| Header institusi dengan 3 logo | **Tolak** | Bukan identitas proyek kita; gunakan merek sendiri |
| Merah institusi `#E31E24` | **Keputusan tim** | Tampung sebagai token tema; lihat bagian 9 |
| Halaman Komparasi Solver (HOA/DBO) | **Tolak** | Di luar PRD (hanya LP) |
| `ProtectedRoute` sisi klien | **Adopsi + perkuat** | Server tetap otoritas (sudah ada 403/404); klien hanya menyembunyikan menu |
| Satu komponen halaman 1.000 baris | **Tolak** | Pecah: hook data, komponen presentasi, helper format (target < 250 baris per berkas) |

## 5. Kelemahan teknis referensi yang harus dihindari

1. URL API hardcode di dua tempat; kita memakai `VITE_API_BASE_URL` dan **satu** klien API.
2. Tidak ada penanganan 401 global (token kedaluwarsa menghasilkan layar rusak); kita: 401 → logout + redirect, 429 → pesan "coba lagi dalam N detik" dari `Retry-After`.
3. `alert()` untuk galat; kita: komponen toast/inline + pemeta galat terpusat.
4. Data diambil dengan `useEffect` manual; kita: TanStack Query (cache, status loading/galat, invalidasi, polling).
5. Tidak ada tipe; kontrak API yang sering berubah mudah lepas. Kita: tipe dari `openapi.json`.
6. Sidebar tetap 256 px; Pekerja memakai ponsel di kandang. Kita: tata letak responsif (drawer di ponsel).
7. Dockerfile menjalankan dev server; kita: build statis + Nginx (SPA fallback).
8. Tanpa test/CI; kita: Vitest + Testing Library + MSW, job CI frontend.
9. Token di `localStorage` tanpa mitigasi; lihat keputusan di bagian 9.
10. Duplikasi (`AppLayout` dua berkas, impor tak terpakai); kita: `oxlint` + `tsc --noEmit` di CI.

## 6. Arsitektur frontend yang direkomendasikan

### 6.1 Stack
| Kebutuhan | Pilihan | Alasan |
|---|---|---|
| Build/UI | Vite + React 19 + **TypeScript** | Sama dengan acuan (tim familier) + keamanan tipe |
| Styling | Tailwind CSS v4 dengan token tema di `@theme` | Satu tempat ganti warna merek; sesuai acuan |
| Routing | React Router 7 | Sama dengan acuan; rute berlapis dan `lazy()` per halaman |
| Data server | **TanStack Query** | Cache, `refetchInterval` untuk polling perintah, invalidasi setelah mutasi, paginasi |
| Tipe & klien API | `openapi-typescript` + `openapi-fetch` (atau Axios dengan tipe) | Tipe dihasilkan dari `/openapi.json` backend; skrip `npm run gen:api` |
| Form | `react-hook-form` + `zod` | Validasi sisi klien yang selaras dengan 422; banyak formulir (nutrisi, bahan, siklus) |
| Komponen dasar | Komponen sendiri di atas **Radix UI** (Dialog, Select, Tabs, Toast) bergaya shadcn/ui | Modal/focus-trap aksesibel tanpa membangun dari nol |
| Ikon | `lucide-react` | Sama dengan acuan |
| Uji | Vitest + Testing Library + MSW; (opsional) Playwright untuk alur demo | Alur kritis: login, formulasi, beri makan |
| Lint | `oxlint` (dipertahankan) + `tsc --noEmit` | Cepat; tipe diperiksa terpisah |

### 6.2 Struktur folder (`frontend/`)
```
frontend/
  src/
    app/            # router, provider (QueryClient, Auth), layout responsif
    api/            # klien tunggal, schema.d.ts (hasil generate), pemeta galat, hook per resource (useKandang, useFormulasi, ...)
    features/       # auth, kandang, alat-stok, siklus, formulasi, perintah, master-data, pekerja, notifikasi
    components/     # ui (Button, Dialog, Table, Badge, Toast, Field), pola umum (EmptyState, ErrorState, Pagination)
    lib/            # format (Rp, angka id-ID, tanggal), konstanta, util
  Dockerfile        # multi-stage: build -> nginx
  nginx.conf        # SPA fallback
```

### 6.3 Keputusan teknis penting
- **Konfigurasi**: `VITE_API_BASE_URL` (mis. `http://localhost:8000/api/v1`); CORS backend sudah mengizinkan `localhost:5173` dan mengekspos `X-Total-Count`.
- **Auth**: `POST /auth/login` (JSON); simpan token; `GET /auth/me` saat muat; 401 → logout otomatis; 403 NONAKTIF dan 429 punya pesan khusus; menu mengikuti `role`, aksi dikunci pula oleh respons server.
- **Polling perintah**: `useQuery(['perintah', id], { refetchInterval: s => final(s) ? false : 1500 })`; stepper status; berhenti pada `SUKSES/GAGAL/TIMEOUT`; tombol **Stop darurat** selalu tampak saat ada perintah aktif.
- **Pemeta galat** (satu fungsi): `422` → pesan per field; `400` → pesan aturan; `409` → banner keadaan (alat offline, stok kurang, formulasi tidak layak, masih dipakai); `429` → hitung mundur dari `Retry-After`; `5xx`/jaringan → pesan umum + coba lagi.
- **Paginasi**: komponen tabel generik membaca `X-Total-Count`.
- **Format**: `Intl.NumberFormat('id-ID')`, mata uang Rupiah, tanggal lokal dari ISO UTC.
- **Peran**: Pemilik = semua; Pekerja = dashboard, kandang yang ditugaskan, beri makan, stok (isi ulang/koreksi), populasi, notifikasi — **tanpa** master data, formulasi (membuat/simpan), pekerja, hapus.

## 7. Peta halaman → endpoint

| Halaman | Peran | Endpoint utama | Catatan |
|---|---|---|---|
| Login | semua | `POST /auth/login`, `GET /auth/me` | 401/403/429 |
| Dashboard | semua | `GET /kandang`, `GET /kandang/{id}`, `GET /kandang/{id}/alat`, `GET /kandang/{id}/stok`, `GET /notifikasi?status=BELUM_DIBACA&limit=1` | Kartu per kandang: status alat (ONLINE/OFFLINE), siklus aktif, stok menipis, jumlah notifikasi (dari `X-Total-Count`). Per kandang beberapa request paralel (cukup untuk skala MVP) |
| Daftar/detail kandang | semua* | `GET/POST/PATCH/DELETE /kandang`, `POST /kandang/{id}/alat`, `POST /alat/{id}/rotasi-token`, `GET /kandang/{id}/alat` | Token alat ditampilkan **sekali** dengan tombol salin; hapus mengikuti aturan 409 |
| Wadah & stok | semua* | `POST/PATCH/DELETE /wadah`, `POST /wadah/{id}/stok/isi-ulang`, `.../koreksi`, `GET .../transaksi` | Koreksi wajib alasan |
| Siklus & populasi | semua* | `POST /kandang/{id}/siklus`, `GET .../siklus/aktif`, `PATCH /siklus/{id}`, `PATCH .../fase`, `POST .../populasi`, `DELETE .../populasi/{pid}`, `POST .../selesai` | Perlu daftar populasi (celah A4) |
| Formulasi (wizard) | Pemilik | `POST /siklus/{id}/formulasi/otomatis`, `.../manual`, `POST /formulasi`, `GET /siklus/{id}/formulasi`, `GET /formulasi/{id}`, `DELETE /formulasi/{id}` | Tampilkan diagnosis infeasible (`keterangan`) dan status `PERLU_DITINJAU` |
| Beri makan | semua* | `POST /kandang/{id}/perintah/beri-makan`, `.../stop-darurat`, `GET /perintah/{id}` (polling), `GET /kandang/{id}/perintah` | Pekerja boleh beri makan |
| Master data | Pemilik | `/nutrisi`, `/bahan-pakan` (+`PUT .../nutrisi`), `/jenis-ayam`, `/jenis-ayam/{id}/fase`, `PUT /fase/{id}/kebutuhan-nutrisi`, `PUT /fase/{id}/standar-konsumsi`, `/template/jenis-ayam` (+salin) | Membaca kandungan/kebutuhan/standar butuh endpoint baru (celah A1–A3) |
| Pekerja & penugasan | Pemilik | `GET/POST /users`, `PATCH /users/{id}/status`, `POST /users/{id}/penugasan`, `DELETE /penugasan/{id}` | Perlu daftar penugasan (celah A5) |
| Notifikasi | semua | `GET /notifikasi`, `PATCH .../baca`, `PATCH .../baca-semua` | Badge di header dari `X-Total-Count` |
| Profil | semua | `POST /auth/ganti-kata-sandi` | |

\* Pekerja hanya untuk kandang yang ditugaskan.

## 8. Celah API untuk UI (harus ditambah di backend)

Dibuktikan dengan memeriksa OpenAPI (`main`, 76 operasi). Semuanya baca-saja atau kecil; belum ada di `API_CONTRACT.md` sehingga perlu persetujuan (aturan AGENTS).

| # | Celah | Mengapa UI membutuhkannya | Usulan | Prioritas |
|---|---|---|---|---|
| A1 | Tidak ada `GET /fase/{id}/kebutuhan-nutrisi` | Tidak bisa menampilkan/mengedit kebutuhan nutrisi fase yang sudah ada (hanya `PUT` replace) | `GET` mengembalikan `KebutuhanNutrisiFase[]` (+ nama nutrisi, satuan) | **P1** |
| A2 | Tidak ada `GET /fase/{id}/standar-konsumsi` | Idem untuk standar konsumsi | `GET` → `StandarKonsumsi \| null` | **P1** |
| A3 | Tidak ada `GET /bahan-pakan/{id}/nutrisi` | Idem untuk kandungan nutrisi bahan | `GET` → `KandunganNutrisiBahan[]` (+ nama nutrisi) | **P1** |
| A4 | Tidak ada `GET /siklus/{id}/populasi` | Daftar catatan populasi untuk memilih yang salah dan dihapus (`DELETE .../populasi/{pid}` butuh id) | `GET` berpaginasi, terbaru dulu | **P1** |
| A5 | Tidak ada daftar penugasan | `DELETE /penugasan/{id}` butuh id; UI perlu "kandang milik pekerja" dan "pekerja di kandang" | `GET /kandang/{id}/penugasan` dan/atau `GET /users/{id}/penugasan` | **P1** |
| A6 | Tidak ada `GET /kandang/{id}/siklus` (riwayat) dan `GET /siklus/{id}` | Riwayat siklus lampau; tautan ke formulasi siklus lama | `GET` berpaginasi + detail | P2 |
| A7 | Tidak ada `PATCH /users/{id}` / reset kata sandi pekerja | Pemilik tidak bisa memperbaiki nama/email atau mengatur ulang sandi Pekerja yang lupa | `PATCH` (nama, email) + `POST .../reset-sandi` | P2 |
| A8 | Tidak ada ringkasan dashboard | Dashboard memanggil beberapa endpoint per kandang | Cukup request paralel dulu; endpoint agregat hanya bila lambat | P3 (ditunda) |

Tidak diperlukan: WebSocket (polling sesuai arsitektur), refresh token (kedaluwarsa 24 jam; 401 → login ulang).

## 9. Keputusan desain

**Diputuskan 2 November 2026** (jawaban pemilik proyek): F-1, F-2, F-3, F-4, F-5, dan F-8 mengikuti rekomendasi; cakupan awal = **potongan demo dulu** (5A + 5B + 5C + 5D + 5E, master data lewat seed/template). F-6 dan F-7 adalah usulan yang belum dikonfirmasi.

| # | Keputusan | Rekomendasi / status |
|---|---|---|
| F-1 | JavaScript atau TypeScript | **DIPUTUSKAN: TypeScript** (tipe dari OpenAPI mencegah selisih kontrak) |
| F-2 | Pengambilan data | **DIPUTUSKAN: TanStack Query** (polling & cache bawaan) |
| F-3 | Komponen UI | **DIPUTUSKAN:** komponen sendiri di atas **Radix** (gaya shadcn/ui) |
| F-4 | Identitas visual | **DIPUTUSKAN:** merek sendiri hijau-kuning agri dengan token tema; tanpa logo Telkom/BRIN |
| F-5 | Lokasi kode | **DIPUTUSKAN:** `frontend/` di monorepo ini (satu PR dapat mengubah API dan UI; CI bersama) |
| F-6 | Penyimpanan token | `localStorage` (seperti acuan; risiko XSS dikurangi dengan tanpa HTML mentah + CSP di Nginx). Alternatif cookie httpOnly menuntut perubahan backend (ditunda) |
| F-7 | Prioritas ponsel | Layar Pekerja (beri makan, stok, populasi) **mobile-first**; layar Pemilik/master data desktop-first tetap responsif |
| F-8 | Celah API A1–A5 | **DIPUTUSKAN:** ditambahkan lebih dulu (P1); A6–A7 menyusul bila dibutuhkan |

## 10. Rencana bertahap (Fase 5)

| Tahap | Isi | Estimasi |
|---|---|---|
| 5A Fondasi | `frontend/` (Vite+TS+Tailwind tokens), klien + tipe OpenAPI, Auth + 401/429, layout responsif, helper format, komponen dasar, Vitest/MSW, CI job frontend | 2–3 hari |
| 5B Backend P1 | Endpoint A1–A5 + test + kontrak (paralel dengan 5A) | 1 hari |
| 5C Alur demo inti | Dashboard, detail kandang (alat/wadah/stok), siklus & populasi | 3–4 hari |
| 5D Formulasi | Wizard preview → simpan, tabel resep, evaluasi nutrisi, diagnosis infeasible | 3 hari |
| 5E Beri makan | Perintah + polling + stop darurat + riwayat; notifikasi | 2–3 hari |
| 5F Master data | Nutrisi, bahan (+kandungan), jenis ayam/fase (+kebutuhan, standar), salin template | 3–4 hari |
| 5G Pekerja | Kelola pekerja & penugasan, peran Pekerja | 1–2 hari |
| 5H Penutup | Dockerfile+Nginx, profil compose `web`, uji ujung ke ujung dengan simulator, panduan | 2 hari |
Total ±3 minggu satu developer (±2 minggu bila dua orang bekerja paralel pada 5C–5F). **Potongan demo minimum**: 5A + 5C + 5D + 5E, dengan master data diisi lewat `seed_demo.py`/template terlebih dahulu.

## 11. Risiko

| Risiko | Mitigasi |
|---|---|
| Lingkup UI besar untuk waktu tersisa | Kerjakan potongan demo minimum dulu; master data lewat seed/template |
| Selisih kontrak API ↔ UI | Tipe dibuat otomatis; CI memeriksa `gen:api` tidak menimbulkan diff |
| Editor matriks nutrisi rumit | Mulai dari tabel sederhana per bahan (baris = nutrisi) dengan satuan |
| Pekerja memakai ponsel | Mobile-first untuk layar Pekerja, uji di lebar 375 px |
| Menyalin kode referensi menimbulkan masalah lisensi/identitas | Menulis ulang; hanya meniru pola UX |
