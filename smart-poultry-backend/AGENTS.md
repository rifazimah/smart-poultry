# AGENTS.md — Aturan untuk AI Coding Agent

File ini dibaca otomatis oleh Antigravity di awal setiap sesi. Tujuannya:
agent bekerja konsisten dengan keputusan tim, tidak menebak-nebak, dan tidak
membangun hal yang belum diminta.

Dokumen lain yang WAJIB dirujuk sebelum menulis kode (jangan diringkas dari
ingatan, baca ulang file aslinya tiap sesi karena bisa sudah berubah):
- @PRD-MVP.md — apa yang sedang dibangun dan kenapa, batas cakupan bulan ini
- @ARCHITECTURE.md — bentuk sistem, alur data, keputusan teknis
- @API_CONTRACT.md — bentuk endpoint yang sudah disepakati
- @CONVENTIONS.md — aturan teknis detail (hashing, LP solver, struktur kode)

## Prinsip umum

1. **KISS (Keep It Simple)** — pilih solusi paling sederhana yang memenuhi
   kebutuhan saat ini. Jangan tambahkan fleksibilitas untuk kasus yang belum
   diminta ("just in case").
2. **DRY (Don't Repeat Yourself)** — kalau ada logika yang mulai dipakai di
   2 tempat atau lebih, pindahkan ke `app/services/`. Tapi jangan
   abstraksi berlebihan untuk kode yang baru dipakai sekali.
3. **YAGNI (You Aren't Gonna Need It)** — jangan membangun fitur, tabel,
   atau endpoint yang tidak ada di PRD-MVP.md / API_CONTRACT.md, walaupun
   "kelihatan akan berguna nanti". Fase 2 sudah dicatat terpisah — biarkan
   di sana.
4. **Konsistensi di atas preferensi pribadi** — kalau pola penulisan kode
   yang sudah ada di repo berbeda dari "cara terbaik" menurutmu, ikuti pola
   yang sudah ada, kecuali diminta eksplisit untuk refactor.

## Lingkup kerja (scope boundary)

- Satu task = satu Issue/fitur yang diminta di prompt. **Jangan** sekalian
  memperbaiki/mengubah bagian lain yang terlihat "kurang rapi" tanpa diminta
  — laporkan saja temuannya di akhir, biar manusia yang putuskan.
- **Jangan** menambah dependency baru di `requirements.txt` tanpa
  menyebutkannya eksplisit di laporan akhir (nama package + alasan).
- **Jangan** mengubah skema tabel di `app/models/` di luar task yang
  eksplisit memintanya. Kalau task butuh perubahan skema, itu harus
  disebutkan jelas sebagai bagian dari task.
- **Jangan** membangun endpoint/fitur yang berkaitan dengan: Jadwal,
  SesiJadwal, PengajuanJadwal, Role/Permission dinamis, atau Super Admin.
  Ini sengaja ditunda ke Fase 2 (lihat PRD-MVP.md bagian "Tidak termasuk").
  Kalau sebuah task sepertinya butuh salah satu dari ini, STOP dan laporkan
  ke pengguna dulu, jangan diputuskan sendiri.

## Kalau ragu

- Kalau API_CONTRACT.md tidak menyebutkan endpoint yang dibutuhkan untuk
  sebuah task, **tanya dulu**, jangan menambah endpoint baru sepihak.
- Kalau ada dua cara valid untuk mengimplementasikan sesuatu dan
  CONVENTIONS.md/ARCHITECTURE.md tidak menyebutkan mana yang dipilih,
  pilih yang **lebih sederhana**, lalu sebutkan di laporan akhir bahwa ini
  sebuah keputusan yang diambil (supaya bisa dikoreksi kalau salah).
- Jangan mengasumsikan requirement yang tidak tertulis. Lebih baik tanya
  satu kalimat daripada membangun hal yang salah lalu dibongkar lagi.

## Checklist sebelum melaporkan task "selesai"

1. Kode berjalan tanpa error saat dites manual lewat `/docs` (Swagger UI).
2. Response API tidak pernah mengembalikan `kata_sandi_hash` atau
   `device_token` mentah di body manapun (cek field apa saja yang keluar).
3. Kalau ada perubahan skema: migrasi Alembic sudah dibuat & dijalankan,
   BUKAN diubah manual lewat SQL.
4. Endpoint baru sudah sesuai path, method, dan bentuk body di
   API_CONTRACT.md — kalau berbeda, jelaskan kenapa di laporan.
5. Laporan akhir **menyertakan pesan error asli** kalau ada yang gagal,
   jangan disimpulkan sendiri ("sepertinya berhasil") — tunjukkan buktinya
   (hasil curl/response JSON, bukan cuma klaim).

## Tools yang boleh dipakai

- Baca/tulis file di dalam folder project ini.
- Jalankan perintah terminal: `pip`, `alembic`, `uvicorn`, `git`, `pytest`
  (begitu test mulai ditulis).
- **Jangan** menjalankan perintah yang mengubah data di luar database lokal
  project ini (tidak ada akses ke server lain, tidak ada deploy otomatis).
- **Jangan** melakukan `git push` tanpa diminta eksplisit — biarkan
  pengguna yang review lewat Pull Request dulu.
