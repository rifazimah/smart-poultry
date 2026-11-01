# PRD — Smart Poultry (MVP, 1 Bulan)

> Ini versi **ringkas, khusus cakupan bulan ini**. Visi lengkap aplikasi
> (termasuk fitur Fase 2) ada di riwayat diskusi tim, tidak diulang di sini
> supaya tidak membingungkan AI agent yang membaca file ini. Kalau butuh
> konteks visi penuh, tanya ke pengguna, jangan diasumsikan dari luar file
> ini.

## Masalah yang diselesaikan

Peternak ayam harus menghitung sendiri komposisi pakan (jenis bahan +
takaran) yang memenuhi kebutuhan nutrisi ayam sesuai fase pertumbuhannya,
lalu memberi pakan tersebut secara manual. Ini memakan waktu, rawan salah
hitung, dan tidak efisien biaya. Smart Poultry mengotomasi **perhitungan
formulasi pakan berbasis nutrisi** dan **pengeluaran pakan lewat alat**,
sehingga peternak tinggal input data ayam dan menekan tombol.

## Pengguna

- **Pemilik** — peternak, pemilik kandang. Mengelola master data, kandang,
  akun pekerja, dan menjalankan formulasi.
- **Pekerja** — petugas kandang harian. Mengakses kandang yang ditugaskan,
  bisa memberi makan manual dan mencatat populasi/stok.

## Cakupan MVP (yang SEDANG dibangun)

1. Akun & autentikasi (Pemilik, Pekerja — role tetap, bukan dinamis)
2. Kandang, Alat (direpresentasikan simulator untuk sekarang), Wadah
3. Master data: Jenis Ayam, Fase, Nutrisi, Bahan Pakan, kandungan nutrisi
   bahan, kebutuhan nutrisi per fase, standar konsumsi
4. Siklus kandang & pencatatan populasi (mortalitas/panen/penambahan)
5. **Formulasi pakan** — mode otomatis (linear programming, biaya
   termurest) dan manual (validasi nutrisi) — ini fitur inti, prioritas
   tertinggi
6. **Beri makan manual** — tombol kirim perintah ke alat, status
   PENDING→DIAMBIL→BERJALAN→SUKSES/GAGAL/TIMEOUT, lewat simulator alat
7. Stok pakan (estimasi dari log pengeluaran, isi ulang & koreksi manual)
8. Notifikasi dasar di dalam aplikasi

## TIDAK termasuk di MVP ini (sengaja ditunda ke Fase 2)

Kalau sebuah permintaan menyentuh salah satu dari daftar ini, STOP dan
konfirmasi ke pengguna dulu — jangan diasumsikan harus dibangun:

- Penjadwalan otomatis pemberian pakan (tabel Jadwal, SesiJadwal)
- Alur pengajuan jadwal oleh Pekerja + persetujuan Pemilik
  (PengajuanJadwal)
- Role & Permission dinamis yang bisa diatur lewat UI (role saat ini:
  enum tetap PEMILIK/PEKERJA di kode)
- Super Admin
- Ketahanan alat saat offline (buffer lokal, sinkronisasi otomatis) —
  simulator alat untuk MVP selalu dianggap online/terhubung
- Sensor stok fisik — stok murni dihitung dari catatan transaksi
- Notifikasi di luar aplikasi (email/WhatsApp)

## Definisi "selesai" untuk MVP

Demo end-to-end berhasil: Pemilik login → buat kandang & alat (simulator)
→ isi master data nutrisi → mulai siklus kandang dengan jenis & jumlah
ayam → jalankan formulasi otomatis → hasil formulasi memenuhi kebutuhan
nutrisi dengan biaya ditampilkan → tekan beri makan → simulator alat
menjalankan & melapor → stok berkurang, riwayat & notifikasi tercatat.

## Alat IoT fisik

Belum ada / di luar cakupan tim ini. Semua testing dan demo memakai
**simulator alat** (skrip Python terpisah, lihat ARCHITECTURE.md) yang
meniru perilaku alat sungguhan lewat endpoint `/device/*` di
API_CONTRACT.md.
