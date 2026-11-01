"""Builder data demo (sama dengan docs/panduan/smoke-test-swagger.md)."""
from types import SimpleNamespace

API = "/api/v1"


def post(client, h, path, json=None, ok=(200, 201)):
    r = client.post(API + path, json=json if json is not None else {}, headers=h)
    assert r.status_code in ok, f"POST {path} -> {r.status_code}: {r.text}"
    return r.json() if r.content else None


def put(client, h, path, json):
    r = client.put(API + path, json=json, headers=h)
    assert r.status_code == 200, f"PUT {path} -> {r.status_code}: {r.text}"
    return r.json()


def get(client, h, path, ok=(200,)):
    r = client.get(API + path, headers=h)
    assert r.status_code in ok, f"GET {path} -> {r.status_code}: {r.text}"
    return r.json()


def buat_master(client, h) -> SimpleNamespace:
    d = SimpleNamespace()
    d.protein = post(client, h, "/nutrisi", {"nama": "Protein", "satuan": "%", "tipe_batas": "MIN_MAKS"})["id"]
    d.energi = post(client, h, "/nutrisi", {"nama": "Energi Metabolis", "satuan": "kkal/kg", "tipe_batas": "MINIMUM"})["id"]
    d.kalsium = post(client, h, "/nutrisi", {"nama": "Kalsium", "satuan": "%", "tipe_batas": "MIN_MAKS"})["id"]

    def bahan(nama, harga, protein, energi, kalsium, batas=None):
        body = {"nama": nama, "harga": harga}
        if batas is not None:
            body["batas_maksimum"] = batas
        bid = post(client, h, "/bahan-pakan", body)["id"]
        put(client, h, f"/bahan-pakan/{bid}/nutrisi", [
            {"nutrisi_id": d.protein, "nilai_per_kg": protein},
            {"nutrisi_id": d.energi, "nilai_per_kg": energi},
            {"nutrisi_id": d.kalsium, "nilai_per_kg": kalsium},
        ])
        return bid

    d.jagung = bahan("Jagung", 5000, 8.5, 3350, 0.02)
    d.kedelai = bahan("Bungkil Kedelai", 9000, 44, 2400, 0.3)
    d.dedak = bahan("Dedak", 3000, 12, 1800, 0.1)
    d.kapur = bahan("Tepung Batu", 1000, 0, 0, 38, batas=0.05)

    d.jenis_ayam = post(client, h, "/jenis-ayam", {"nama": "Broiler"})["id"]
    d.fase_starter = post(client, h, f"/jenis-ayam/{d.jenis_ayam}/fase",
                          {"nama": "Starter", "umur_min_hari": 0, "umur_max_hari": 14})["id"]
    d.fase_grower = post(client, h, f"/jenis-ayam/{d.jenis_ayam}/fase",
                         {"nama": "Grower", "umur_min_hari": 15, "umur_max_hari": 28})["id"]
    put(client, h, f"/fase/{d.fase_starter}/kebutuhan-nutrisi", [
        {"nutrisi_id": d.protein, "batas_min": 20, "batas_max": 23},
        {"nutrisi_id": d.energi, "batas_min": 2900},
        {"nutrisi_id": d.kalsium, "batas_min": 0.9, "batas_max": 1.2},
    ])
    put(client, h, f"/fase/{d.fase_starter}/standar-konsumsi",
        {"gram_per_ekor_per_hari": 50, "frekuensi_makan": 4, "durasi_aduk": 30, "volume_air": 200})
    put(client, h, f"/fase/{d.fase_grower}/kebutuhan-nutrisi", [
        {"nutrisi_id": d.protein, "batas_min": 18, "batas_max": 21},
    ])
    put(client, h, f"/fase/{d.fase_grower}/standar-konsumsi",
        {"gram_per_ekor_per_hari": 90, "frekuensi_makan": 3, "durasi_aduk": 30, "volume_air": 300})
    return d


def buat_kandang(client, h, d, nama="Kandang A", isi_stok=True, jumlah_ayam=100) -> SimpleNamespace:
    """Kandang + alat + 4 wadah (+ isi ulang stok) + siklus aktif."""
    k = SimpleNamespace()
    k.id = post(client, h, "/kandang", {"nama": nama, "lokasi": "Blok 1"})["id"]
    alat = post(client, h, f"/kandang/{k.id}/alat")
    k.alat_id, k.device_token = alat["id"], alat["device_token"]
    k.wadah = {}
    for no, (nama_b, bid) in enumerate(
        [("jagung", d.jagung), ("kedelai", d.kedelai), ("dedak", d.dedak), ("kapur", d.kapur)], start=1
    ):
        k.wadah[nama_b] = post(client, h, f"/alat/{k.alat_id}/wadah",
                               {"nomor_wadah": no, "bahan_pakan_id": bid})["id"]
    if isi_stok:
        for nama_b, jumlah in [("jagung", 20000), ("kedelai", 10000), ("dedak", 10000), ("kapur", 2000)]:
            post(client, h, f"/wadah/{k.wadah[nama_b]}/stok/isi-ulang", {"jumlah": jumlah})
    k.siklus_id = post(client, h, f"/kandang/{k.id}/siklus", {
        "jenis_ayam_id": d.jenis_ayam, "fase_id": d.fase_starter,
        "jumlah_ayam": jumlah_ayam, "tanggal_mulai": "2026-11-01",
    })["id"]
    return k


def device_h(k) -> dict:
    return {"X-Device-Token": k.device_token}


def heartbeat(client, k, status="ONLINE"):
    r = client.post(API + "/device/heartbeat", json={"status": status}, headers=device_h(k))
    assert r.status_code == 200, r.text
    return r.json()


def formulasi_manual_valid(d) -> dict:
    return {"item": [
        {"bahan_pakan_id": d.jagung, "proporsi": 0.64},
        {"bahan_pakan_id": d.kedelai, "proporsi": 0.33},
        {"bahan_pakan_id": d.kapur, "proporsi": 0.025},
        {"bahan_pakan_id": d.dedak, "proporsi": 0.005},
    ]}


def simpan_formulasi_otomatis(client, h, k) -> str:
    preview = post(client, h, f"/siklus/{k.siklus_id}/formulasi/otomatis")
    assert preview["status"] == "VALID", preview
    return post(client, h, "/formulasi", preview)["id"]
