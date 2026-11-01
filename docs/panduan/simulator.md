# Simulator Alat IoT

Pengganti alat fisik untuk pengujian dan demo. Berada di folder [`simulator/`](../../simulator/) di root repo — **terpisah** dari backend
dan tidak mengimpor kode backend; hanya berbicara lewat endpoint `/device/*` ([API_CONTRACT bagian 8](../spesifikasi/API_CONTRACT.md)).

## Cara kerja

```
loop tiap `heartbeat_interval_seconds` (dari server, default 10 dtk):
  POST /device/heartbeat {"status":"ONLINE"}   -> alat ONLINE, terima perintah PENDING (bila ada)
  bila ada perintah:
    BERI_MAKAN   : ambil -> jeda -> mulai -> jeda proses fisik -> log (SUKSES / GAGAL / SKIPPED_STOCK)
    STOP_DARURAT : ambil -> log SUKSES (langsung)
  selama jeda, heartbeat tetap dikirim; bila ada STOP_DARURAT, proses dihentikan dan stop didahulukan
```
`id_eksekusi_unik` dibuat sekali per perintah. Bila jaringan putus saat mengirim log, simulator mengirim ulang dengan id yang sama
(idempoten: server membalas 200 dengan log yang sama, stok tidak berkurang dua kali).

## Menjalankan

```bash
pip install -r simulator/requirements.txt     # hanya httpx
python simulator/run.py --device-token <TOKEN>
```
Token didapat saat `POST /kandang/{id}/alat` (tampil sekali) atau buat ulang lewat `POST /alat/{id}/rotasi-token`.
Alternatif: `set DEVICE_TOKEN=<TOKEN>` (Windows) / `export DEVICE_TOKEN=<TOKEN>`.

| Opsi | Default | Fungsi |
|---|---|---|
| `--base-url` | `http://localhost:8000` | Alamat backend (atau env `SIMULATOR_BASE_URL`) |
| `--interval` | dari server | Paksa interval heartbeat (detik); mis. `2` agar demo cepat |
| `--ambil-delay` | `1` | Jeda `ambil` → `mulai` |
| `--proses-delay` | `5` | Durasi proses fisik (detik) |
| `--fail-rate` | `0` | Peluang log `GAGAL` (0–1) |
| `--skip-stock-rate` | `0` | Peluang log `SKIPPED_STOCK` |
| `--berat-dasar` | `1000` | Berat aktual rata-rata yang dilaporkan (gram, ±3%) |
| `--offline-after` / `--offline-for` | — | Berhenti heartbeat setelah N detik selama M detik (menguji deteksi OFFLINE, ambang 3× interval) |
| `--once` | — | Berhenti setelah satu perintah selesai |
| `--seed` | acak | Seed acak agar hasil dapat diulang |

Hentikan dengan `Ctrl+C`. Token ditolak → keluar dengan kode 1 dan pesan jelas.

## Skenario demo

Siapkan dengan [data demo](setup-backend.md#data-demo), lalu:

1. Jalankan backend (`uvicorn app.main:app --reload`) dan simulator: `python simulator/run.py --device-token <TOKEN> --interval 3`.
2. Di Swagger (sebagai admin): `POST /siklus/{siklus}/formulasi/otomatis` → `POST /formulasi` → `POST /kandang/{kandang}/perintah/beri-makan`.
3. Pantau `GET /perintah/{id}` (PENDING → DIAMBIL → BERJALAN → SUKSES), lalu `GET /kandang/{kandang}/stok` dan `GET /notifikasi`.
4. Variasi: `--fail-rate 1` (GAGAL, stok tetap), `--skip-stock-rate 1`, kirim `POST /kandang/{kandang}/perintah/stop-darurat` saat `BERJALAN` (perintah lama menjadi `GAGAL`, stop `SUKSES`),
   `--offline-after 5 --offline-for 60` lalu cek `GET /kandang/{kandang}` → `OFFLINE` dan notifikasi `ALAT_OFFLINE`.

Simulator ini juga menggantikan langkah manual `/device/*` pada [skenario smoke test](smoke-test-fase-1.md) bagian C–G.

## Batasan

- Simulator selalu menganggap dirinya terhubung kecuali dikonfigurasi `--offline-*`; tidak ada buffer lokal/sinkronisasi (Fase 2 produk).
- Berat aktual hanya simulasi; backend mengurangi stok menurut `berat_per_sesi` formulasi, bukan `berat_aktual` (lihat catatan T-10 di [review kode](../analisis/03-review-kode.md)).
- Satu simulator = satu alat (satu token). Untuk beberapa kandang, jalankan beberapa proses.

## Pengujian

`smart-poultry-backend/tests/test_simulator.py` menjalankan kelas `Simulator` terhadap API melalui `TestClient` (sukses, gagal, skipped, stop darurat,
stop saat memproses, kirim ulang log, simulasi offline). Uji nyata (uvicorn + simulator sebagai proses CLI) dilakukan 1 Nov 2026: perintah `SUKSES`, stok berkurang 1250 g, notifikasi terbentuk.
