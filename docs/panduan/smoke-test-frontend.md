# Smoke Test Frontend (Fase 2–5 dari sisi UI)

Menguji aplikasi web (`frontend/`) bersama backend, simulator alat, dan data demo. Skenario ini juga menyentuh perilaku Fase 3 (simulator) dan Fase 4 (login NONAKTIF, rate-limit, health) yang terlihat dari UI.
Perilaku API Fase 2 (template, paginasi, kode error) punya panduan tersendiri: [smoke-test-fase-2.md](smoke-test-fase-2.md). Waktu total ±60–75 menit.

> **Status:** kode diuji otomatis (194 test backend, 90 test frontend) dan satu alur ujung ke ujung (login → formulasi otomatis → simpan → beri makan lewat simulator → stok turun → notifikasi) pernah dijalankan di browser nyata.
> Skenario di bawah **belum pernah dijalankan manusia secara lengkap**. Catat setiap baris yang tidak sesuai di [lembar temuan](#lembar-temuan) pada akhir dokumen.

## 0. Persiapan

Prasyarat: setup backend selesai ([setup-backend.md](setup-backend.md)), Node.js 22+ dan npm ([frontend.md](frontend.md)), database lokal menyala (`docker compose up -d`), dan data demo ada.

Gunakan **database milikmu sendiri** (bukan database tim lain). Skenario ini menambah dan mengubah data; bila ingin mengulang dari awal, lihat [bagian K](#k-membersihkan-dan-mengulang).

Buka tiga terminal:

```bash
# Terminal 1 — backend (dari smart-poultry-backend, venv aktif)
python seed_demo.py            # aman diulang; CATAT X-Device-Token yang tercetak (hanya tampil sekali)
uvicorn app.main:app --reload  # port 8000; bila terpakai: --port 8001
```
```bash
# Terminal 2 — frontend (dari frontend)
cp .env.example .env           # PowerShell: Copy-Item .env.example .env
npm ci
npm run dev                    # buka http://localhost:5173
```
```bash
# Terminal 3 — simulator alat (dari root repo); jalankan setelah bagian A selesai
python simulator/run.py --device-token <TOKEN> --interval 3
```

- Backend di port lain (mis. 8001): ubah `VITE_API_BASE_URL=http://localhost:8001` di `frontend/.env` (hanya origin, tanpa `/api/v1`), restart `npm run dev`, dan tambahkan `--base-url http://localhost:8001` pada simulator.
- Token alat hilang: Swagger `POST /alat/{id}/rotasi-token` (ID alat tercetak di output seed).
- Akun: Pemilik `admin@smartpoultry.com` / `admin123`; Pekerja `budi@example.com` / `budi12345` (belum ditugaskan).
- Gunakan jendela browser biasa; DevTools (F12) tetap terbuka di tab **Console** untuk melihat galat merah.

**Data awal yang diharapkan dari seed:** satu kandang (**Kandang A**, Blok 1), alat dengan 4 wadah (Jagung 20.000 g, Bungkil Kedelai 10.000 g, Dedak 10.000 g, Tepung Batu 2.000 g), siklus aktif Broiler fase Starter 100 ekor (standar konsumsi 50 g/ekor/hari, 4 kali makan → **1.250 g per sesi**), belum ada formulasi.

## A. Masuk, sesi, dan keluar

| # | Aksi | Harapan |
|---|---|---|
| A.1 | Buka `http://localhost:5173/` tanpa login | Diarahkan ke `/masuk`; judul **Smart Poultry**; tombol **Masuk** nonaktif |
| A.2 | Isi email benar dan sandi salah → **Masuk** | Kotak galat merah: `Email atau kata sandi salah`; tidak berpindah halaman |
| A.3 | Klik ikon mata pada kolom sandi | Sandi terlihat/tersembunyi bergantian |
| A.4 | Masuk sebagai `admin@smartpoultry.com` / `admin123` | Masuk ke dashboard: **Halo, Pemilik Pertama**; menu samping: Dashboard, Pekerja, Master data, Notifikasi; nama dan peran **Pemilik** di kanan atas |
| A.5 | Muat ulang halaman (F5) | Tetap masuk (sesi dipulihkan), tidak kembali ke halaman masuk |
| A.6 | Buka tab baru ke `http://localhost:5173/kandang/xyz` | Pesan **Kandang tidak ditemukan** dengan tautan kembali (bukan layar kosong/galat merah di Console) |
| A.7 | Klik **Keluar** | Kembali ke `/masuk`; menekan tombol Back browser tidak memperlihatkan halaman yang butuh login |
| A.8 | Masuk lagi; di DevTools → Application → Local Storage ubah nilai `sp_token` menjadi `rusak`, lalu muat ulang | Kembali ke halaman masuk (token ditolak dan dibersihkan) |
| A.9 | Masuk lagi; ubah `sp_token` menjadi `rusak` **tanpa** memuat ulang, lalu klik menu Notifikasi | Diarahkan ke halaman masuk dan muncul toast **Sesi berakhir** |

## B. Dashboard dan detail kandang

| # | Aksi | Harapan |
|---|---|---|
| B.1 | Dashboard | Teks **1 kandang**; kartu **Kandang A**, lokasi **Blok 1**, lencana **Aktif** |
| B.2 | Klik kartu Kandang A (di mana saja pada kartu) | Pindah ke `/kandang/<id>` |
| B.3 | Bagian **Alat dan wadah** | Status alat (**Offline** bila simulator belum jalan), `Sinkron terakhir: -`, Wadah 1–4 berurutan dengan nama bahan: Jagung, Bungkil Kedelai, Dedak, Tepung Batu |
| B.4 | Bagian **Stok pakan** | `20 kg`, `10 kg`, `10 kg`, `2 kg` (stok disimpan dalam gram; tampil g atau kg otomatis) |
| B.5 | Bagian **Siklus pemeliharaan** | Jenis ayam **Broiler**, Fase **Starter**, Jumlah ayam **100**, tanggal mulai hari ini; **Riwayat populasi** `Belum ada perubahan populasi.`; tombol **Beri makan** dan **Kelola formulasi pakan** |
| B.6 | Di bagian **Siklus pemeliharaan**, klik **Catat populasi**: Jenis Mortalitas, Jumlah `3`, catatan `Uji` → **Simpan** | Toast **Perubahan populasi dicatat**; Riwayat populasi menampilkan `Mortalitas · Uji` dan `3 ekor`; jumlah ayam menjadi **97** |

> Setelah B.6, jumlah ayam 97 membuat berat per sesi menjadi 1.212,5 g; angka di bagian C–D di bawah mengikuti 100 ekor. Lewati B.6 atau sesuaikan hitungan (atau hapus catatannya di L.11).

## C. Formulasi pakan (Pemilik)

Mulai dari detail Kandang A → **Kelola formulasi pakan**.

| # | Aksi | Harapan |
|---|---|---|
| C.1 | Buka halaman | Mode **Otomatis** terpilih; **Riwayat formulasi** berisi `Belum ada formulasi tersimpan` |
| C.2 | **Hitung otomatis** | Tombol berputar sebentar, lalu kotak **Pratinjau (belum disimpan)**: lencana **Valid**, **Otomatis**, `Biaya per kg` terisi (kira-kira Rp 6.000-an); tabel **Resep** dengan 4 bahan, jumlah proporsi 100%, kolom **Per sesi** berjumlah ±1,25 kg; tabel **Evaluasi nutrisi**: Protein 20–23, Energi ≥ 2.900, Kalsium 0,9–1,2, semua **Sesuai** |
| C.3 | Muat ulang halaman | Pratinjau hilang; riwayat tetap kosong (pratinjau memang tidak tersimpan) |
| C.4 | Ulangi C.2, klik **Simpan formulasi** | Pesan **Formulasi tersimpan.**; riwayat berisi satu baris dengan lencana **Valid**, **Otomatis**, **Aktif**, waktu, dan biaya/kg |
| C.5 | Klik **Lihat** pada baris riwayat | Resep dan evaluasi nutrisi yang sama terbuka di bawah baris; tombol berubah menjadi **Tutup** |
| C.6 | Pilih mode **Manual** | Daftar semua bahan dengan kolom persen; tombol **Hitung formulasi manual** nonaktif; `Total: 0% (harus 100%)` |
| C.7 | Isi Jagung 60, Bungkil Kedelai 32, Dedak 6 | `Total: 98%`; tombol masih nonaktif |
| C.8 | Isi Tepung Batu 2 → **Hitung formulasi manual** | Pratinjau mode **Manual**. Hitungan manual: Protein ≈ 19,9 (**Kurang**), Energi ≈ 2.886 (**Kurang**), Kalsium ≈ 0,87 (**Kurang**); status keseluruhan bukan **Valid** (catat labelnya) |
| C.9 | **Simpan formulasi** pada hasil C.8 | Catat apakah server menerima (formulasi bermutu rendah tersimpan) atau menolak dengan pesan; riwayat bertambah bila diterima |
| C.10 | Kasus **tidak layak** — Master data → tab **Jenis ayam** → **Broiler** → fase **Starter** → **Nutrisi dan konsumsi**: ubah Protein minimum **40** dan maksimum **45** → **Simpan kebutuhan** | Toast **Kebutuhan nutrisi disimpan** |
| C.11 | Kembali ke halaman formulasi → mode **Otomatis** → **Hitung otomatis** | Lencana **Tidak sempurna**; kotak **Catatan sistem** menjelaskan nutrisi yang mustahil (menyebut Protein, nilai tertinggi yang mungkin); baris Protein berstatus **Kurang** dengan keterangan; **tidak** ada layar galat |
| C.12 | **Kembalikan** kebutuhan Protein Starter ke minimum **20** dan maksimum **23** | Toast tersimpan; **Hitung otomatis** lagi → **Valid** (wajib dikembalikan agar bagian D berjalan normal) |
| C.13 | Pastikan formulasi **otomatis Valid** yang tersimpan di C.4 berlabel **Aktif** di riwayat | Hanya satu formulasi berlabel **Aktif** pada satu waktu; bila C.9 menyimpan formulasi manual, catat mana yang aktif |

> Bila yang aktif pada C.13 adalah formulasi manual hasil C.8, simpan ulang formulasi otomatis (C.2 + C.4) agar formulasi aktif berkualitas baik sebelum bagian D.

## D. Beri makan, polling, dan stop darurat (Pemilik + simulator)

Detail Kandang A → **Beri makan**.

| # | Aksi | Harapan |
|---|---|---|
| D.1 | Simulator **belum** berjalan | Teks **Alat sedang offline.**; tombol **Beri makan sekarang** nonaktif; **Stop darurat** tetap aktif |
| D.2 | Jalankan simulator (Terminal 3); tunggu ±15–20 detik tanpa memuat ulang | Pesan offline hilang sendiri dan tombol menjadi aktif; di detail kandang status alat **Online** dan `Sinkron terakhir` terisi |
| D.3 | Klik **Beri makan sekarang** | Toast **Perintah beri makan dikirim**; riwayat langsung menampilkan baris **Beri makan** berstatus **Menunggu alat**; tombol nonaktif dengan teks **Alat sedang memproses perintah.** |
| D.4 | Tunggu tanpa mengklik apa pun | Status berubah sendiri: **Menunggu alat** → **Diambil alat** → **Berjalan** → **Sukses** (total ±10 detik); setelah **Sukses** tombol aktif lagi |
| D.5 | Lihat Console DevTools / tab Network | Selama perintah berjalan ada permintaan `GET .../perintah` tiap ±3 detik; setelah **Sukses** permintaan itu berhenti |
| D.6 | Buka detail Kandang A → **Stok pakan** | Setiap bahan berkurang tepat sebesar `Per sesi` di resep (mis. Jagung ±760 g; stok tampil seperti `19,24 kg`); total turun ±1.250 g |
| D.7 | Menu **Notifikasi** | Satu notifikasi **Perintah sukses**: `Perintah BERI_MAKAN telah SUKSES.`; ikon lonceng di header menampilkan angka 1 |
| D.8 | Hentikan simulator (Ctrl+C), jalankan ulang dengan `--fail-rate 1`, beri makan lagi | Status akhir **Gagal**; stok **tidak** berkurang; notifikasi **Perintah gagal** |
| D.9 | Jalankan ulang dengan `--skip-stock-rate 1`, beri makan lagi | Catat status akhir dan stok (seharusnya tidak berkurang) |
| D.10 | Jalankan ulang dengan `--proses-delay 20`, beri makan, lalu saat **Berjalan** klik **Stop darurat** → **Batal** | Dialog **Hentikan pemberian pakan?** tertutup; tidak ada perintah baru |
| D.11 | Klik **Stop darurat** → **Ya, hentikan** | Toast **Stop darurat dikirim**; perintah beri makan lama menjadi **Gagal** dan baris **Stop darurat** berstatus **Sukses** (setelah simulator memprosesnya); notifikasi stop darurat muncul |
| D.12 | Hentikan simulator dan tunggu ±45–60 detik | Status alat menjadi **Offline** di halaman beri makan (tanpa memuat ulang, pembaruan tiap 15 detik); notifikasi **Alat offline** |
| D.13 | Klik **Beri makan sekarang** saat offline | Tombol nonaktif; bila dipaksa lewat Swagger, server membalas 409 `Alat sedang OFFLINE` |

## E. Notifikasi

| # | Aksi | Harapan |
|---|---|---|
| E.1 | Menu **Notifikasi** | Daftar terbaru di atas, notifikasi baru berlatar hijau muda dengan tombol **Tandai dibaca**; lencana jenis berwarna (sukses hijau, gagal merah, offline kuning) |
| E.2 | **Tandai dibaca** pada satu notifikasi | Latar berubah normal, tombol hilang, angka di lonceng berkurang satu (maksimal ±30 detik) |
| E.3 | **Tandai semua dibaca** | Semua tombol **Tandai dibaca** hilang; tombol **Tandai semua dibaca** nonaktif; lonceng tanpa angka |
| E.4 | Notifikasi baru muncul saat halaman lain dibuka | Angka di lonceng bertambah dalam ±30 detik tanpa memuat ulang |

## F. Master data (Pemilik)

Menu **Master data** → tiga tab: **Jenis ayam**, **Bahan pakan**, **Nutrisi**.

| # | Aksi | Harapan |
|---|---|---|
| F.1 | Tab **Nutrisi** | Protein, Energi Metabolis, Kalsium dengan satuan dan lencana jenis batas |
| F.2 | **Tambah nutrisi**: Nama `Fosfor Uji`, Satuan `%`, Jenis batas `Minimum` → **Simpan** | Toast **Nutrisi disimpan**; muncul di daftar |
| F.3 | **Ubah** nutrisi itu: satuan jadi `g/kg` | Daftar menampilkan satuan baru |
| F.4 | **Hapus** `Fosfor Uji` → **Hapus** pada dialog | Toast **Nutrisi dihapus**; hilang dari daftar |
| F.5 | **Hapus** nutrisi **Protein** (dipakai bahan/fase) | Dialog **tetap terbuka** dan menampilkan alasan dari server (nutrisi masih dipakai); data tidak terhapus |
| F.6 | Tab **Bahan pakan**: **Tambah bahan** `Bahan Uji`, harga `4500`, batas maksimum `40` → **Simpan** | Pesan galat di dialog: batas maksimum harus pecahan 0 sampai 1; tidak ada permintaan ke server |
| F.7 | Ubah batas maksimum menjadi `0,4` → **Simpan** | Toast **Bahan pakan disimpan**; daftar menampilkan `Rp 4.500/kg · maks 40%` |
| F.8 | **Kandungan** pada `Bahan Uji`: isi Protein `10`, Energi `3000`, kosongkan Kalsium → **Simpan kandungan** | Toast **Kandungan nutrisi disimpan**; membuka lagi menampilkan 10 dan 3000 |
| F.9 | **Kandungan** dengan isian `abc` | Pesan galat nilai harus angka nol atau lebih; tidak terkirim |
| F.10 | **Hapus** `Bahan Uji` | Terhapus (belum dipakai formulasi/wadah) |
| F.11 | **Hapus** bahan **Jagung** (terpasang di wadah) | Ditolak server dengan alasan di dialog |
| F.12 | Tab **Jenis ayam** → **Salin dari template** | Daftar template (broiler dan petelur) dengan deskripsi dan jumlah fase |
| F.13 | Isi nama `Broiler Template`, klik **Salin** pada template broiler | Toast `Jenis ayam "Broiler Template" dibuat`; muncul di daftar; nutrisi yang belum ada dibuat otomatis (cek tab Nutrisi) |
| F.14 | Klik nama `Broiler Template` | Halaman detail: fase Starter, Grower, Finisher berurutan umur dengan rentang hari |
| F.15 | **Tambah fase** `Uji` umur awal `30`, akhir `15` | Galat: umur awal tidak boleh melebihi umur akhir; tidak terkirim |
| F.16 | Ubah umur akhir menjadi `45` → **Simpan** | Toast **Fase disimpan** |
| F.17 | **Nutrisi dan konsumsi** pada fase `Uji`: isi satu baris batas, lalu isi **Standar konsumsi** (gram 50, frekuensi 3, aduk 30, air 2,5) → simpan masing-masing | Toast **Kebutuhan nutrisi disimpan** dan **Standar konsumsi disimpan**; dibuka ulang nilainya tetap |
| F.18 | Bersihkan: hapus fase `Uji`, lalu hapus jenis ayam `Broiler Template` | Fase terhapus; jenis ayam terhapus (bila ditolak karena fase masih ada, hapus fase lain dulu atau catat pesannya) |
| F.19 | Hapus jenis ayam **Broiler** (dipakai siklus) | Ditolak dengan alasan di dialog |

## G. Pekerja dan penugasan (Pemilik)

Menu **Pekerja**.

| # | Aksi | Harapan |
|---|---|---|
| G.1 | Buka halaman | Budi tampil dengan lencana **Aktif** |
| G.2 | **Tambah pekerja**: Nama `Dewi`, Email `dewi@example.com`, sandi `pendek` | Galat: kata sandi awal minimal 8 karakter; tidak terkirim |
| G.3 | Ganti sandi menjadi `rahasia123` → **Simpan** | Toast **Pekerja ditambahkan**; Dewi muncul |
| G.4 | Tambah lagi dengan email `dewi@example.com` | Dialog menampilkan `Email sudah terdaftar` |
| G.5 | **Penugasan** pada Budi | Dialog **Penugasan: Budi**: `Belum ditugaskan ke kandang mana pun.`; pilihan Kandang berisi **Kandang A**; tanggal mulai terisi hari ini |
| G.6 | Pilih Kandang A → **Tugaskan** | Toast **Pekerja ditugaskan**; baris `Kandang A · sejak <tanggal>`; Kandang A tidak ada lagi di pilihan |
| G.7 | **Akhiri** penugasan itu, lalu tugaskan lagi (untuk bagian H) | Toast **Penugasan diakhiri**, lalu **Pekerja ditugaskan** |
| G.8 | **Nonaktifkan** Dewi | Toast **Pekerja dinonaktifkan**; lencana **Nonaktif**; tombol berubah **Aktifkan** |
| G.9 | **Aktifkan** Dewi lagi | Toast **Pekerja diaktifkan** |

## H. Sebagai Pekerja

Pastikan Budi ditugaskan ke Kandang A (G.7). **Keluar**, lalu masuk sebagai `budi@example.com` / `budi12345` (atau gunakan jendela penyamaran).

| # | Aksi | Harapan |
|---|---|---|
| H.1 | Dashboard | **Halo, Budi**, peran **Pekerja**; menu hanya **Dashboard** dan **Notifikasi** |
| H.2 | Lihat daftar kandang | Hanya Kandang A |
| H.3 | Buka detail Kandang A | Tersedia tombol **Beri makan**; **tidak ada** tombol **Kelola formulasi pakan** |
| H.4 | Ketik manual `http://localhost:5173/master-data`, `/pekerja`, dan `/kandang/<id>/formulasi` | Setiap kali dialihkan ke dashboard |
| H.5 | Dengan simulator berjalan dan formulasi aktif ada, **Beri makan** → **Beri makan sekarang** | Perintah dikirim dan selesai **Sukses** seperti bagian D |
| H.6 | Sebagai Pemilik, **akhiri** penugasan Budi; sebagai Budi muat ulang dashboard | Daftar kandang kosong: `Anda belum ditugaskan ke kandang mana pun. Hubungi Pemilik.`; membuka URL detail Kandang A langsung → pesan galat akses atau tidak ditemukan (bukan data kandang; catat teksnya) |
| H.7 | Sebagai Pemilik, **nonaktifkan** Budi lalu Budi mencoba **masuk** | Galat di halaman masuk: `User nonaktif` |
| H.8 | (Catat saja) Budi sudah masuk, lalu Pemilik menonaktifkannya; apa yang terjadi pada permintaan berikutnya Budi? | Tidak dispesifikasikan; catat perilakunya (tetap bisa memakai token lama sampai kedaluwarsa, atau ditolak) |

## I. Ketahanan dan keamanan dasar

| # | Aksi | Harapan |
|---|---|---|
| I.1 | Di halaman masuk, coba sandi salah 5 kali berturut-turut untuk email karangan `uji@example.com` (**jangan** memakai akun admin), lalu percobaan ke-6 | Galat `Terlalu banyak percobaan login yang gagal. Coba lagi dalam N detik.` (429); login sukses pada email lain tetap bisa |
| I.2 | Matikan backend (Ctrl+C) saat berada di dashboard, lalu pindah menu | Pesan `Tidak dapat terhubung ke server` dengan tombol **Coba lagi**; tidak ada layar putih |
| I.3 | Nyalakan backend lagi, klik **Coba lagi** | Data kembali tampil |
| I.4 | Buka `http://localhost:8000/health` dan `/health/db` | `{"status":"ok"}` dan `{"status":"ok","database":"ok"}` |
| I.5 | Hentikan database (`docker compose stop db`), buka `/health/db`, lalu nyalakan lagi (`docker compose start db`) | **503** saat database mati; kembali 200 setelah menyala |
| I.6 | Buka `/docs` (Swagger) tanpa Authorize, coba `GET /kandang` | 401 (tanpa token tidak bisa mengakses data) |

## J. Tampilan ponsel dan aksesibilitas ringan

DevTools → mode perangkat (lebar ±375 px) atau kecilkan jendela.

| # | Aksi | Harapan |
|---|---|---|
| J.1 | Dashboard | Menu samping hilang; ada tombol **Buka menu** (ikon hamburger); kartu kandang satu kolom; tidak ada gulir horizontal pada halaman |
| J.2 | **Buka menu** → pilih **Notifikasi** | Laci menu terbuka dan menutup sendiri setelah memilih; tombol **Tutup** dan tombol Esc juga menutup laci |
| J.3 | Halaman formulasi dengan pratinjau | Tabel resep dan nutrisi dapat digeser horizontal di dalam kartu; teks tidak terpotong |
| J.4 | Dialog (mis. Tambah nutrisi) | Muat di layar, bisa ditutup dengan Esc dan tombol **Tutup**; fokus keyboard tetap di dalam dialog |
| J.5 | Navigasi hanya dengan keyboard (Tab/Enter) di halaman masuk dan dashboard | Semua tombol dan tautan dapat dijangkau dengan indikator fokus terlihat |

## L. Membangun data dari nol lewat UI (5I)

Pemilik dapat menyiapkan kandang sampai beri makan tanpa Swagger atau `seed_demo.py`. Skenario ini paling jelas bila database hanya berisi akun Pemilik (`python seed_admin.py`) ditambah master data (nutrisi, bahan beserta kandungan, jenis ayam dengan fase Starter, kebutuhan nutrisi, dan standar konsumsi; bisa dari Master data di UI atau tombol **Salin dari template** lalu isi harga dan kandungan bahan).

| # | Aksi | Harapan |
|---|---|---|
| L.1 | Dashboard saat belum ada kandang | Teks `Klik Tambah kandang untuk membuat kandang pertama Anda.` dan tombol **Tambah kandang** (hanya untuk Pemilik) |
| L.2 | **Tambah kandang**: nama `Kandang Uji`, lokasi `Blok Uji` → **Simpan** | Toast **Kandang dibuat** dan langsung berpindah ke halaman detailnya; tombol **Ubah kandang**, **Nonaktifkan**, **Hapus kandang** tampil |
| L.3 | **Daftarkan alat** | Dialog **Token alat** dengan token panjang dan peringatan bahwa token tidak akan ditampilkan lagi; **tetap terbuka** walau daftar alat di belakangnya sudah berubah menjadi kartu alat (Offline). Catat token, klik **Sudah saya simpan** |
| L.4 | **Rotasi token** → **Batal**; ulangi → **Buat token baru** | Batal: tidak ada perubahan. Buat token baru: dialog token baru tampil; token lama tidak berlaku lagi untuk simulator |
| L.5 | **Tambah wadah**: nomor terisi otomatis (berikutnya), pilih bahan **Jagung** → **Simpan** | Toast **Wadah ditambahkan**; muncul **Wadah 1 · Jagung** dan kartu stok **Jagung 0 g** dengan tombol **Isi ulang**, **Koreksi**, **Riwayat** |
| L.6 | Tambahkan wadah 2–4 (Bungkil Kedelai, Dedak, Tepung Batu) | Wadah dan kartu stok bertambah; **Ubah bahan** pada satu wadah mengganti bahannya (toast **Bahan wadah disimpan**) |
| L.7 | **Isi ulang Jagung**: jumlah `0` → **Simpan** | Galat `Jumlah harus berupa angka lebih dari nol`; tidak terkirim |
| L.8 | Isi ulang Jagung `20` (kg) | Toast **Stok diisi ulang**; stok tampil **20 kg**. Isi ulang tiga wadah lain (10, 10, 2 kg) |
| L.9 | **Koreksi Dedak**: jumlah `9,5`, alasan dikosongkan → **Simpan** | Ditolak oleh isian wajib (alasan harus diisi); setelah alasan diisi, stok Dedak menjadi **9,5 kg** |
| L.10 | **Riwayat Jagung** | Daftar transaksi: **Isi ulang** 20 kg; setelah beri makan, **Pengeluaran** dalam gram (mis. 737,4 g) |
| L.11 | **Mulai siklus**: pilih jenis ayam → daftar **Fase** terisi (terurut umur) → pilih Starter, jumlah `100`, tanggal hari ini | Toast **Siklus dimulai**; muncul Jenis ayam, Fase, Jumlah ayam 100; tombol **Catat populasi**, **Ganti fase**, **Koreksi siklus**, **Selesaikan siklus**, **Hapus siklus** |
| L.12 | **Catat populasi**: Mortalitas, `3` | Jumlah ayam 97; baris riwayat dengan tombol **Hapus** (Pemilik) |
| L.13 | **Hapus** catatan itu → **Hapus** | Toast **Catatan populasi dihapus**; jumlah ayam kembali 100 |
| L.14 | **Ganti fase** ke Grower | Toast **Fase diganti**; pada halaman formulasi, formulasi lama berstatus **Perlu ditinjau** (bila ada). Kembalikan ke Starter |
| L.15 | **Koreksi siklus**: jumlah `98` → **Simpan** | Jumlah ayam 98 (hanya untuk membetulkan salah input) |
| L.16 | Hitung dan simpan formulasi, jalankan simulator dengan token dari L.3/L.4, lalu **Beri makan** | Seperti bagian D: status berubah sampai **Sukses**, stok berkurang, notifikasi muncul |
| L.17 | **Hapus alat** (setelah ada perintah) | Dialog menampilkan penolakan server (alat sudah punya riwayat perintah atau stok belum 0) |
| L.18 | **Selesaikan siklus** → **Batal**, lalu ulangi → **Selesaikan** | Batal: tetap aktif. Selesaikan: toast **Siklus diselesaikan**; kandang kembali **Kandang kosong** dengan tombol **Mulai siklus** |
| L.19 | **Nonaktifkan** kandang lalu **Aktifkan** lagi | Lencana berubah **Nonaktif**/**Aktif**; toast sesuai |
| L.20 | **Hapus kandang** pada kandang yang sudah punya siklus | Ditolak dengan alasan di dialog (sarannya: nonaktifkan). Kandang baru tanpa siklus/alat dapat dihapus dan kembali ke dashboard |
| L.21 | Sebagai Pekerja yang ditugaskan: buka detail kandang | Terlihat **Isi ulang/Koreksi/Riwayat** dan **Catat populasi**; **tidak** terlihat Ubah/Hapus kandang, Tambah wadah, Rotasi token, Hapus alat, Mulai siklus, Ganti fase, Koreksi/Selesaikan/Hapus siklus |

## K. Membersihkan dan mengulang

- Hanya data uji: hapus manual lewat UI (bagian F dan G sudah membersihkan sebagian) atau abaikan.
- Ulang dari awal: [reset total](setup-backend.md#reset-total) lalu `python seed_demo.py`.
- Hentikan simulator (Ctrl+C), `npm run dev` (Ctrl+C), dan uvicorn (Ctrl+C) setelah selesai.

## Lembar temuan

Salin tabel ini; isi satu baris per langkah yang tidak sesuai harapan (sertakan teks galat di Console bila ada).

| Langkah | Terjadi | Harapan | Browser/OS | Catatan |
|---|---|---|---|---|
| | | | | |

Hal yang sangat berguna untuk dilaporkan walaupun tidak "salah": teks yang membingungkan, langkah yang terasa lambat (>3 detik tanpa indikator), tombol yang tidak jelas fungsinya, dan data yang kamu butuhkan saat menguji tetapi tidak bisa dibuat dari UI.
