# tests/test_analisis.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# =====================================
# 1. TEST FILM POPULER
# =====================================

def test_filmpopuler_daily():
    response = client.get("/filmpopuler/daily?day=1")
    assert response.status_code == 200
    data = response.json()

    assert "tanggal" in data
    assert "data" in data
    assert isinstance(data["data"], list)


def test_filmpopuler_weekly():
    response = client.get("/filmpopuler/weekly")
    assert response.status_code == 200
    data = response.json()

    assert "hasil" in data
    assert isinstance(data["hasil"], list)
    assert len(data["hasil"]) == 5  # 5 minggu


def test_filmpopuler_monthly():
    response = client.get("/filmpopuler/monthly?bulan=Desember")
    assert response.status_code == 200
    data = response.json()

    assert "bulan" in data
    assert "data" in data
    assert isinstance(data["data"], list)


# =====================================
# 2. TEST JAM TAYANG POPULER
# =====================================

def test_jamtayang_daily():
    response = client.get("/jamtayangpopuler/daily?day=5")
    assert response.status_code == 200

    data = response.json()
    assert "data" in data
    assert isinstance(data["data"], list)


def test_jamtayang_weekly():
    response = client.get("/jamtayangpopuler/weekly")
    assert response.status_code == 200

    data = response.json()
    assert "minggu" in data
    assert isinstance(data["minggu"], list)
    assert len(data["minggu"]) == 5


def test_jamtayang_monthly():
    response = client.get("/jamtayangpopuler/monthly?bulan=Desember")
    assert response.status_code == 200

    data = response.json()
    assert "data" in data
    assert isinstance(data["data"], list)


# =====================================
# 3. TEST VALIDASI BULAN TIDAK VALID
# =====================================

def test_invalid_month():
    response = client.get("/filmpopuler/monthly?bulan=xxx")
    assert response.status_code == 200
    data = response.json()
    assert "error" in data
