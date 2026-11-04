# Panduan Frontend

Aplikasi web Smart Poultry ada di folder `frontend/` (Vite + React 19 + TypeScript). Panduan ini untuk anggota tim yang menjalankan atau mengembangkan frontend. Latar belakang keputusan: [analisis/07-analisis-frontend.md](../analisis/07-analisis-frontend.md).

## Prasyarat
- Node.js 22 atau lebih baru (diuji pada Node 24) dan npm.
- Backend berjalan di `http://localhost:8000` ([setup-backend.md](setup-backend.md)). CORS backend sudah mengizinkan `http://localhost:5173`.

## Menjalankan
```bash
cd frontend
cp .env.example .env
npm ci
npm run dev
```
Buka `http://localhost:5173`. Masuk dengan akun dari seed (lihat `setup-backend.md`).

## Variabel lingkungan
| Variabel | Isi | Contoh |
|---|---|---|
| `VITE_API_BASE_URL` | Alamat backend, **hanya origin tanpa `/api/v1`** (path `/api/v1` sudah ada pada tipe hasil generate dari OpenAPI) | `http://localhost:8000` |

Nilai ini ditanam saat build; ubah `.env` lalu jalankan ulang `npm run dev` / `npm run build`.

## Skrip
| Perintah | Fungsi |
|---|---|
| `npm run dev` | Server pengembangan |
| `npm run build` | Cek tipe lalu build produksi ke `dist/` |
| `npm run preview` | Pratinjau hasil build |
| `npm run lint` | oxlint |
| `npm run typecheck` | `tsc --noEmit` |
| `npm test` | Vitest (jsdom + MSW; tidak butuh backend) |
| `npm run gen:api` | Membuat ulang `src/api/schema.d.ts` dari `openapi.json` |
| `npm run check:size` | Memeriksa anggaran ukuran bundle awal (setelah `build`) |

## Struktur
```
frontend/src/
  api/        klien openapi-fetch, ApiError + pemetaan pesan galat, schema.d.ts (hasil generate)
  auth/       token (localStorage), AuthProvider, ProtectedRoute
  app/        providers, rute, layout (menu mengikuti peran)
  components/ui/  komponen dasar (button, card, dialog, toast, ...)
  features/   satu folder per fitur (auth, dashboard, kandang, notifikasi, ...)
  lib/        format angka/rupiah/tanggal, env
  test/       setup Vitest, server MSW, helper render
```

## Perubahan kontrak API (`gen:api`)
Tipe API dihasilkan dari `frontend/openapi.json`, yaitu salinan skema OpenAPI backend yang di-commit. Setelah mengubah endpoint atau skema di backend:
```bash
cd smart-poultry-backend
python scripts/export_openapi.py      # menulis ../frontend/openapi.json
cd ../frontend
npm run gen:api                       # menulis src/api/schema.d.ts
```
Commit kedua berkas. Dua pengaman: tes backend `tests/test_openapi_snapshot.py` gagal bila `openapi.json` tertinggal, dan CI frontend gagal bila `schema.d.ts` tidak sesuai `openapi.json`.

## Perilaku penting
- Aksi tulis kandang (5I): Pemilik membuat/mengubah/menghapus kandang, mendaftarkan alat (token tampil sekali dalam dialog yang dipegang komponen induk agar tidak hilang saat data dimuat ulang), mengelola wadah, siklus (mulai, ganti fase, koreksi, selesai, hapus), dan catatan populasi. Pemilik dan Pekerja yang ditugaskan boleh mengisi ulang/mengoreksi stok dan mencatat populasi; input stok dalam kg dikirim sebagai gram.
- Pekerja: Pemilik membuat akun Pekerja (kata sandi awal minimal 8 karakter, aturan di klien; server hanya mewajibkan role PEKERJA dan email unik) dan menugaskannya ke kandang. Pekerja hanya melihat kandang yang ditugaskan; menu dan tombol Pemilik disembunyikan, otorisasi sebenarnya di server.
- Master data: hapus data yang masih dipakai ditolak server (409) dan alasannya tampil di dalam dialog konfirmasi. Batas maksimum bahan diketik sebagai pecahan 0–1 (0,4 = 40%); input angka menerima koma desimal.
- Beri makan: riwayat perintah di-poll tiap 3 detik hanya selama ada perintah berstatus PENDING/DIAMBIL/BERJALAN, lalu berhenti sendiri. Tombol dinonaktifkan di UI bila alat tidak ada/offline, tidak ada formulasi aktif, atau ada perintah berjalan; aturan sebenarnya tetap dijalankan server (409).
- Formulasi: hasil hitung hanya pratinjau sampai tombol Simpan ditekan; status `TIDAK_SEMPURNA` datang sebagai respons 200 dengan `pesan` diagnosis, bukan galat. Proporsi manual diketik dalam persen dan dikirim sebagai pecahan 0–1.
- Token JWT disimpan di `localStorage`; sesi dipulihkan lewat `GET /auth/me` saat aplikasi dibuka.
- Respons 401 pada request terautentikasi (selain login) memaksa keluar dan menampilkan toast "Sesi berakhir".
- Pesan galat dipetakan di `api/errors.ts` (`pesanGalat`): 422, 403, 429 (memakai `Retry-After`), galat server, dan jaringan.
- Daftar berpaginasi memakai `skip`/`limit` dan membaca total dari header `X-Total-Count`.

## Anggaran ukuran bundle
Ditegakkan oleh `npm run check:size` (juga di CI): JS awal ≤ 200 KB gzip, CSS awal ≤ 30 KB gzip. Hanya berkas yang dimuat langsung oleh `index.html` yang dihitung; halaman dimuat malas (lazy). Pengukuran saat 5A selesai: JS awal ±116 KB, CSS ±5 KB. Tambah dependensi besar hanya bila perlu.

## Deploy hemat
Hasil build berupa berkas statis, jadi tidak butuh server aplikasi: cukup hosting statis (Netlify, Cloudflare Pages, GitHub Pages, atau Nginx kecil). Atur `VITE_API_BASE_URL` ke alamat backend publik saat build, dan tambahkan origin frontend ke CORS backend (`CORS_ORIGINS`, daftar JSON). Untuk rute SPA, hosting harus mengarahkan semua path ke `index.html`.

### Nginx dalam Docker (bila di-host sendiri)
`frontend/Dockerfile` membangun aplikasi lalu menyajikannya dengan Nginx (`frontend/nginx.conf`: fallback SPA ke `index.html`, gzip, aset ber-hash di-cache setahun, `index.html` tidak di-cache). Build gagal bila melampaui anggaran ukuran bundle.
```bash
VITE_API_BASE_URL=http://localhost:8000 docker compose --profile web up -d --build web   # buka http://localhost:8080
docker compose --profile web down
```
`WEB_PORT` mengubah port (bawaan 8080). Alamat backend ditanam saat build, jadi ubah lalu build ulang bila berpindah server. Tambahkan origin frontend ke `CORS_ORIGINS` backend (bawaan compose sudah mencakup `http://localhost:8080`).

## Satuan data
Stok dan berat per sesi dari server bersatuan **gram**; UI menampilkan gram atau kg otomatis (`formatBerat`). Kandungan nutrisi bahan dinyatakan per kg bahan, dan proporsi/batas maksimum bahan berupa pecahan 0–1.

## Uji ujung ke ujung (manual)
Backend + simulator + frontend dengan database sementara (jangan DB dev):
1. Migrasi dan seed demo ke DB uji, jalankan `uvicorn` di port bebas (mis. 18000), simulator `--interval 3`, dan `VITE_API_BASE_URL=http://localhost:18000 npm run dev`.
2. Masuk sebagai Pemilik → detail kandang → formulasi → Hitung otomatis → Simpan → Beri makan; status perintah berubah sendiri sampai Sukses, stok berkurang sebesar berat per sesi, dan notifikasi "Perintah sukses" muncul.
Hasil uji 2 Nov 2026 sesuai skenario ini.

## Catatan keamanan dependensi
`npm audit` melaporkan 3 temuan tingkat moderat pada rantai `openapi-typescript` → `@redocly/openapi-core` → `minimatch`. Paket ini hanya dipakai saat generate tipe (devDependency), tidak masuk ke bundle produksi. Perbaikan otomatis (`audit fix --force`) menurunkan versi `openapi-typescript` dan merusak generate, jadi ditunda sampai ada rilis perbaikan.
