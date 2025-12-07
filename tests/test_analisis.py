import pytest
from fastapi.testclient import TestClient
from app.database import SessionLocal
from app.routers.analisis import get_db
from datetime import date

from app.main import app
from app.database import get_db

client = TestClient(app)

# ------- MOCK DATABASE SESSION -------- #

@pytest.fixture
def mock_db():
    """Mock session SQLAlchemy."""
    db = MagicMock()
    yield db


# override dependency FastAPI → get_db → mock_db
app.dependency_overrides[get_db] = lambda: MagicMock()


# ==========================================================
# 1. TEST /filmpopuler/daily
# ==========================================================

def test_filmpopuler_daily():
    mock_data = [
        {"id": 1, "title": "Film A", "total_tiket_terjual": 10},
        {"id": 2, "title": "Film B", "total_tiket_terjual": 7},
    ]

    mock_db = MagicMock()
    mock_db.execute().mappings().all.return_value = mock_data

    app.dependency_overrides[get_db] = lambda: mock_db

    response = client.get("/filmpopuler/daily?day=5")

    assert response.status_code == 200
    json = response.json()

    assert json["tanggal"] == "2024-12-05"
    assert json["total_tiket_terjual"] == 2
    assert len(json["data"]) == 2
    assert json["data"][0]["title"] == "Film A"


# ==========================================================
# 2. TEST /filmpopuler/weekly
# ==========================================================

def test_filmpopuler_weekly():
    mock_rows = [
        {"id": 1, "title": "Film A", "total_tiket_terjual": 20},
        {"id": 2, "title": "Film B", "total_tiket_terjual": 8},
    ]

    mock_db = MagicMock()
    mock_db.execute().mappings().all.return_value = mock_rows

    app.dependency_overrides[get_db] = lambda: mock_db

    response = client.get("/filmpopuler/weekly")

    assert response.status_code == 200
    json = response.json()

    assert json["bulan"] == "Desember 2024"
    assert json["total_minggu"] == 5

    # cek minggu pertama
    minggu1 = json["hasil"][0]
    assert minggu1["film_terlaris"]["title"] == "Film A"


# ==========================================================
# 3. TEST /filmpopuler/monthly
# ==========================================================

def test_filmpopuler_monthly():
    mock_data = [
        {"id": 3, "title": "Film C", "total_tiket_terjual": 30},
        {"id": 5, "title": "Film D", "total_tiket_terjual": 12},
    ]

    mock_db = MagicMock()
    mock_db.execute().mappings().all.return_value = mock_data
    app.dependency_overrides[get_db] = lambda: mock_db

    response = client.get("/filmpopuler/monthly?bulan=desember")

    assert response.status_code == 200
    json = response.json()

    assert json["bulan"] == "desember"
    assert json["total_film"] == 2
    assert json["film_terlaris"]["title"] == "Film C"


# ==========================================================
# 4. TEST jam tayang daily
# ==========================================================

def test_jamtayang_daily():
    mock_rows = [
        {"movie_id": 1, "title": "Film A", "jam": "14:00", "total_tiket": 10},
        {"movie_id": 1, "title": "Film A", "jam": "18:00", "total_tiket": 15},
    ]

    mock_db = MagicMock()
    mock_db.execute().mappings().all.return_value = mock_rows
    app.dependency_overrides[get_db] = lambda: mock_db

    response = client.get("/jamtayangpopuler/daily?day=3")

    assert response.status_code == 200
    json = response.json()

    assert json["tanggal"] == "2024-12-03"
    assert len(json["data"]) == 1
    assert json["data"][0]["jam_terpopuler"] == "18:00"


# ==========================================================
# 5. TEST jam tayang weekly
# ==========================================================

def test_jamtayang_weekly():
    mock_rows = [
        {"movie_id": 1, "title": "Film A", "jam": "14:00", "total_tiket": 5},
        {"movie_id": 1, "title": "Film A", "jam": "18:00", "total_tiket": 9},
    ]

    mock_db = MagicMock()
    mock_db.execute().mappings().all.return_value = mock_rows
    app.dependency_overrides[get_db] = lambda: mock_db

    response = client.get("/jamtayangpopuler/weekly")

    assert response.status_code == 200
    json = response.json()

    minggu1 = json["minggu"][0]
    assert minggu1["data"][0]["jam_terpopuler"] == "18:00"


# ==========================================================
# 6. TEST jam tayang monthly
# ==========================================================

def test_jamtayang_monthly():
    mock_rows = [
        {"movie_id": 2, "title": "Film B", "jam": "12:00", "total_tiket": 7},
        {"movie_id": 2, "title": "Film B", "jam": "15:00", "total_tiket": 11},
    ]

    mock_db = MagicMock()
    mock_db.execute().mappings().all.return_value = mock_rows
    app.dependency_overrides[get_db] = lambda: mock_db

    response = client.get("/jamtayangpopuler/monthly?bulan=desember")

    assert response.status_code == 200
    json = response.json()

    assert json["data"][0]["jam_terpopuler"] == "15:00"
