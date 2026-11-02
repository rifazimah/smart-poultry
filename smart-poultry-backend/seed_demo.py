"""
Seed data demo ke database dev (DATABASE_URL di .env). Idempoten: dilewati bila data demo sudah ada.

Membuat (untuk Pemilik admin@smartpoultry.com): 3 nutrisi, 4 bahan pakan + kandungan, jenis ayam Broiler
(fase Starter & Grower + kebutuhan + standar konsumsi), Kandang A + alat + 4 wadah (stok terisi) + siklus aktif
100 ekor, serta Pekerja budi@example.com (belum ditugaskan, agar skenario penugasan bisa diuji).

Alur formulasi, heartbeat alat, dan beri makan sengaja TIDAK dibuat: itu yang diuji di smoke test
(docs/panduan/smoke-test-swagger.md).

Pakai:  python seed_demo.py        (butuh requirements-dev.txt karena memakai TestClient)

Hanya untuk development: menolak berjalan bila ENVIRONMENT=production (data demo memakai kredensial publik).
Kredensial Pemilik mengikuti seed_admin.py (ADMIN_EMAIL / ADMIN_PASSWORD, bawaan admin@smartpoultry.com / admin123).
"""
from datetime import date

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.config import settings
from app.database import engine
from app.main import app
from app.models.akses import User
from app.models.masterdata import BahanPakan
from seed_admin import create_initial_pemilik, kredensial_admin

API = "/api/v1"


def main():
    if settings.environment == "production":
        raise SystemExit("seed_demo menolak berjalan di ENVIRONMENT=production (berisi kredensial publik).")

    create_initial_pemilik()  # no-op bila admin sudah ada
    EMAIL, SANDI, _ = kredensial_admin()

    with Session(engine) as s:
        pemilik = s.exec(select(User).where(User.email == EMAIL)).first()
        if s.exec(select(BahanPakan).where(BahanPakan.pemilik_id == pemilik.id, BahanPakan.nama == "Jagung")).first():
            print("Data demo sudah ada, dilewati.")
            return

    with TestClient(app) as c:
        r = c.post(f"{API}/auth/login", json={"email": EMAIL, "kata_sandi": SANDI})
        r.raise_for_status()
        h = {"Authorization": f"Bearer {r.json()['access_token']}"}

        def post(path, json=None):
            r = c.post(API + path, json=json if json is not None else {}, headers=h)
            assert r.status_code in (200, 201), f"POST {path} -> {r.status_code}: {r.text}"
            return r.json()

        def put(path, json):
            r = c.put(API + path, json=json, headers=h)
            assert r.status_code == 200, f"PUT {path} -> {r.status_code}: {r.text}"
            return r.json()

        protein = post("/nutrisi", {"nama": "Protein", "satuan": "%", "tipe_batas": "MIN_MAKS"})["id"]
        energi = post("/nutrisi", {"nama": "Energi Metabolis", "satuan": "kkal/kg", "tipe_batas": "MINIMUM"})["id"]
        kalsium = post("/nutrisi", {"nama": "Kalsium", "satuan": "%", "tipe_batas": "MIN_MAKS"})["id"]

        def bahan(nama, harga, p, e, k, batas=None):
            body = {"nama": nama, "harga": harga}
            if batas is not None:
                body["batas_maksimum"] = batas
            bid = post("/bahan-pakan", body)["id"]
            put(f"/bahan-pakan/{bid}/nutrisi", [
                {"nutrisi_id": protein, "nilai_per_kg": p},
                {"nutrisi_id": energi, "nilai_per_kg": e},
                {"nutrisi_id": kalsium, "nilai_per_kg": k},
            ])
            return bid

        jagung = bahan("Jagung", 5000, 8.5, 3350, 0.02)
        kedelai = bahan("Bungkil Kedelai", 9000, 44, 2400, 0.3)
        dedak = bahan("Dedak", 3000, 12, 1800, 0.1)
        kapur = bahan("Tepung Batu", 1000, 0, 0, 38, batas=0.05)

        jenis = post("/jenis-ayam", {"nama": "Broiler"})["id"]
        starter = post(f"/jenis-ayam/{jenis}/fase", {"nama": "Starter", "umur_min_hari": 0, "umur_max_hari": 14})["id"]
        grower = post(f"/jenis-ayam/{jenis}/fase", {"nama": "Grower", "umur_min_hari": 15, "umur_max_hari": 28})["id"]
        put(f"/fase/{starter}/kebutuhan-nutrisi", [
            {"nutrisi_id": protein, "batas_min": 20, "batas_max": 23},
            {"nutrisi_id": energi, "batas_min": 2900},
            {"nutrisi_id": kalsium, "batas_min": 0.9, "batas_max": 1.2},
        ])
        put(f"/fase/{starter}/standar-konsumsi",
            {"gram_per_ekor_per_hari": 50, "frekuensi_makan": 4, "durasi_aduk": 30, "volume_air": 200})
        put(f"/fase/{grower}/kebutuhan-nutrisi", [{"nutrisi_id": protein, "batas_min": 18, "batas_max": 21}])
        put(f"/fase/{grower}/standar-konsumsi",
            {"gram_per_ekor_per_hari": 90, "frekuensi_makan": 3, "durasi_aduk": 30, "volume_air": 300})

        kandang = post("/kandang", {"nama": "Kandang A", "lokasi": "Blok 1"})["id"]
        alat = post(f"/kandang/{kandang}/alat")
        wadah = {}
        for no, (nama, bid, stok) in enumerate(
            [("Jagung", jagung, 20000), ("Bungkil Kedelai", kedelai, 10000),
             ("Dedak", dedak, 10000), ("Tepung Batu", kapur, 2000)], start=1):
            wid = post(f"/alat/{alat['id']}/wadah", {"nomor_wadah": no, "bahan_pakan_id": bid})["id"]
            post(f"/wadah/{wid}/stok/isi-ulang", {"jumlah": stok})
            wadah[nama] = wid
        siklus = post(f"/kandang/{kandang}/siklus", {
            "jenis_ayam_id": jenis, "fase_id": starter, "jumlah_ayam": 100,
            "tanggal_mulai": date.today().isoformat(),
        })["id"]

        post("/users", {"nama": "Budi", "email": "budi@example.com", "kata_sandi": "budi12345", "role": "PEKERJA"})

    print("Data demo berhasil dibuat.")
    print(f"  Pemilik : {EMAIL} / {SANDI}")
    print("  Pekerja : budi@example.com / budi12345 (belum ditugaskan)")
    print(f"  Kandang : {kandang}")
    print(f"  Siklus  : {siklus}")
    print(f"  Alat    : {alat['id']}")
    print(f"  X-Device-Token (hanya tampil sekali): {alat['device_token']}")


if __name__ == "__main__":
    main()
