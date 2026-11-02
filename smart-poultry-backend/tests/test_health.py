from sqlalchemy import create_engine

import app.main as main_module


def test_health_tanpa_database(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_health_db_ok(client):
    r = client.get("/health/db")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "database": "ok"}


def test_health_db_503_bila_database_tidak_terjangkau(client, monkeypatch):
    rusak = create_engine("postgresql+psycopg://x:y@127.0.0.1:1/z", connect_args={"connect_timeout": 2})
    monkeypatch.setattr(main_module, "engine", rusak)
    r = client.get("/health/db")
    assert r.status_code == 503
    assert r.json() == {"status": "error", "database": "tidak terjangkau"}  # tanpa detail internal
