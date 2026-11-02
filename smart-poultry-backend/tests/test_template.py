"""BR-13: template referensi jenis ayam (daftar + salin)."""
import uuid

from sqlalchemy import func
from sqlmodel import Session, select

from app.database import engine
from app.models.akses import AuditLog
from app.models.masterdata import Fase, KebutuhanNutrisiFase, StandarKonsumsi
from tests.conftest import login
from tests.helpers import API, buat_master, get, post


def hitung(model, *kondisi):
    with Session(engine) as s:
        return s.exec(select(func.count()).select_from(model).where(*kondisi)).one()


def test_daftar_template(client, pemilik):
    daftar = get(client, pemilik, "/template/jenis-ayam")
    assert {t["id"] for t in daftar} == {"broiler", "petelur"}
    broiler = next(t for t in daftar if t["id"] == "broiler")
    assert [f["nama"] for f in broiler["fase"]] == ["Starter", "Grower", "Finisher"]
    assert "bukan rekomendasi gizi resmi" in broiler["deskripsi"]
    starter = broiler["fase"][0]
    assert {k["nutrisi"] for k in starter["kebutuhan"]} == {"Protein", "Energi Metabolis", "Kalsium", "Fosfor Tersedia", "Lisin"}
    assert starter["standar_konsumsi"]["gram_per_ekor_per_hari"] > 0


def test_fase_template_konsisten(client, pemilik):
    """Umur fase berurutan tanpa tumpang tindih; batas min <= max."""
    for t in get(client, pemilik, "/template/jenis-ayam"):
        sebelumnya = -1
        for f in t["fase"]:
            assert f["umur_min_hari"] == sebelumnya + 1, (t["id"], f["nama"])
            assert f["umur_max_hari"] >= f["umur_min_hari"]
            sebelumnya = f["umur_max_hari"]
            for k in f["kebutuhan"]:
                if k["batas_min"] is not None and k["batas_max"] is not None:
                    assert k["batas_min"] <= k["batas_max"], (t["id"], f["nama"], k["nutrisi"])


def test_salin_membuat_jenis_fase_kebutuhan_dan_standar(client, pemilik):
    r = client.post(f"{API}/template/jenis-ayam/broiler/salin", json={}, headers=pemilik)
    assert r.status_code == 201, r.text
    jid = r.json()["id"]
    assert r.json()["nama"] == "Broiler"

    fase = get(client, pemilik, f"/jenis-ayam/{jid}/fase")
    assert sorted(f["nama"] for f in fase) == ["Finisher", "Grower", "Starter"]
    with Session(engine) as s:
        fase_ids = [f.id for f in s.exec(select(Fase).where(Fase.jenis_ayam_id == uuid.UUID(jid))).all()]
    assert hitung(StandarKonsumsi, StandarKonsumsi.fase_id.in_(fase_ids)) == 3
    assert hitung(KebutuhanNutrisiFase, KebutuhanNutrisiFase.fase_id.in_(fase_ids)) == 15  # 3 fase x 5 nutrisi
    # nutrisi dibuat otomatis (akun masih kosong)
    assert {n["nama"] for n in get(client, pemilik, "/nutrisi")} == {"Protein", "Energi Metabolis", "Kalsium", "Fosfor Tersedia", "Lisin"}
    with Session(engine) as s:
        log = s.exec(select(AuditLog).where(AuditLog.aksi == "SALIN_TEMPLATE")).one()
        assert "nutrisi baru" in log.catatan


def test_salin_memakai_ulang_nutrisi_yang_sudah_ada_tanpa_duplikat(client, pemilik):
    d = buat_master(client, pemilik)  # sudah punya Protein, Energi Metabolis, Kalsium
    client.patch(f"{API}/nutrisi/{d.protein}", json={"nama": "PROTEIN"}, headers=pemilik)  # beda huruf
    sebelum = len(get(client, pemilik, "/nutrisi"))
    assert client.post(f"{API}/template/jenis-ayam/broiler/salin", json={"nama": "Broiler Salinan"}, headers=pemilik).status_code == 201
    sesudah = get(client, pemilik, "/nutrisi")
    assert len(sesudah) == sebelum + 2  # hanya Fosfor Tersedia dan Lisin yang baru
    assert sum(1 for n in sesudah if n["nama"].lower() == "protein") == 1


def test_salin_nama_kembar_409_dan_nama_lain_boleh(client, pemilik):
    assert client.post(f"{API}/template/jenis-ayam/petelur/salin", json={}, headers=pemilik).status_code == 201
    r = client.post(f"{API}/template/jenis-ayam/petelur/salin", json={}, headers=pemilik)
    assert r.status_code == 409 and "Ayam Petelur" in r.json()["detail"]
    r = client.post(f"{API}/template/jenis-ayam/petelur/salin", json={"nama": "Petelur Kandang B"}, headers=pemilik)
    assert r.status_code == 201 and r.json()["nama"] == "Petelur Kandang B"


def test_salin_tanpa_body_diperbolehkan(client, pemilik):
    assert client.post(f"{API}/template/jenis-ayam/broiler/salin", headers=pemilik).status_code == 201


def test_template_tidak_dikenal_404(client, pemilik):
    assert client.post(f"{API}/template/jenis-ayam/tidak-ada/salin", json={}, headers=pemilik).status_code == 404


def test_hasil_salinan_milik_pemilik_yang_menyalin_saja(client, pemilik, pemilik_lain):
    jid = client.post(f"{API}/template/jenis-ayam/broiler/salin", json={}, headers=pemilik).json()["id"]
    assert client.get(f"{API}/jenis-ayam/{jid}", headers=pemilik_lain).status_code == 404
    assert get(client, pemilik_lain, "/jenis-ayam") == []


def test_pekerja_tidak_boleh_menyalin(client, pemilik):
    post(client, pemilik, "/users", {"nama": "Budi", "email": "budi@example.com", "kata_sandi": "budi12345", "role": "PEKERJA"})
    hp = login(client, "budi@example.com", "budi12345")
    assert client.post(f"{API}/template/jenis-ayam/broiler/salin", json={}, headers=hp).status_code == 403
    assert client.get(f"{API}/template/jenis-ayam", headers=hp).status_code == 403


def test_butuh_login(client):
    assert client.get(f"{API}/template/jenis-ayam").status_code == 401
