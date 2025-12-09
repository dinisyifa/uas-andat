import pytest
from fastapi.testclient import TestClient
from datetime import date, time

from app.main import app
from app.database import get_db
from app.models import Movie, Studio, Jadwal
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# -----------------------------
# 1. Setup REAL SQLite Test DB
# -----------------------------
# Pastikan konfigurasi database Anda benar
password = "kopigulaaren30"
password = password.replace("@", "%40")
TEST_DB = f"mysql+pymysql://root:{password}@localhost:3306/bioskop"

engine_test = create_engine(TEST_DB)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

# Override dependency get_db → gunakan DB testing
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    """Reset database before each test"""
    db = TestingSessionLocal()
    db.execute(text("SET FOREIGN_KEY_CHECKS=0;"))
    db.execute(text("TRUNCATE TABLE jadwal;"))
    db.execute(text("TRUNCATE TABLE movies;"))
    db.execute(text("TRUNCATE TABLE studios;"))
    db.execute(text("SET FOREIGN_KEY_CHECKS=1;"))
    db.commit()
    db.close()


@pytest.fixture
def seed():
    """Insert movie & studio for valid references"""
    db = TestingSessionLocal()
    movie = Movie(code="MV001", title="Avatar", price=50000)
    studio = Studio(code="STD01", name="Studio 1")
    db.add_all([movie, studio])
    db.commit()
    db.close()
    return {"movie": movie, "studio": studio}


# -------- TEST ADD SCHEDULE --------

def test_add_schedule_success(seed):
    resp = client.post("/schedules", json={
        "movie_code": "MV001",
        "studio_code": "STD01",
        "tanggal": "2025-12-10",
        "jam": "14:30"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["movie_code"] == "MV001"
    assert data["studio_code"] == "STD01"
    assert data["tanggal"] == "2025-12-10"
    assert data["jam"] == "14:30:00"  # DB konversi time → HH:MM:SS


def test_add_schedule_invalid_movie(seed):
    resp = client.post("/schedules", json={
        "movie_code": "NOTFOUND",
        "studio_code": "STD01",
        "tanggal": "2025-12-10",
        "jam": "14:30"
    })
    assert resp.status_code == 404


def test_add_schedule_invalid_studio(seed):
    resp = client.post("/schedules", json={
        "movie_code": "MV001",
        "studio_code": "UNKNOWN",
        "tanggal": "2025-12-10",
        "jam": "14:30"
    })
    assert resp.status_code == 404


def test_add_schedule_invalid_date_format(seed):
    resp = client.post("/schedules", json={
        "movie_code": "MV001",
        "studio_code": "STD01",
        "tanggal": "10-12-2025",
        "jam": "14:30"
    })
    assert resp.status_code == 400


def test_add_schedule_invalid_time_format(seed):
    resp = client.post("/schedules", json={
        "movie_code": "MV001",
        "studio_code": "STD01",
        "tanggal": "2025-12-10",
        "jam": "2PM"
    })
    assert resp.status_code == 400


# -------- TEST GET ALL --------

def test_get_schedules(seed):
    # Insert 1 schedule first
    client.post("/schedules", json={
        "movie_code": "MV001",
        "studio_code": "STD01",
        "tanggal": "2025-12-10",
        "jam": "12:00"
    })
    resp = client.get("/schedules")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1


# -------- TEST UPDATE --------

def test_update_schedule_success(seed):
    client.post("/schedules", json={
        "movie_code": "MV001",
        "studio_code": "STD01",
        "tanggal": "2025-12-10",
        "jam": "12:00"
    })

    resp = client.put("/schedules/SCH001", json={
        "movie_code": "MV001",
        "studio_code": "STD01",
        "tanggal": "2025-12-11",
        "jam": "16:00"
    })
    assert resp.status_code == 200
    assert resp.json()["tanggal"] == "2025-12-11"
    assert resp.json()["jam"] == "16:00:00"


def test_update_not_found(seed):
    resp = client.put("/schedules/NONE", json={
        "movie_code": "MV001",
        "studio_code": "STD01",
        "tanggal": "2025-12-11",
        "jam": "16:00"
    })
    assert resp.status_code == 404


# -------- TEST DELETE --------

def test_delete_schedule(seed):
    client.post("/schedules", json={
        "movie_code": "MV001",
        "studio_code": "STD01",
        "tanggal": "2025-12-10",
        "jam": "12:00"
    })

    resp = client.delete("/schedules/SCH001")
    assert resp.status_code == 200
    assert "berhasil dihapus" in resp.json()["status"]
    
    # Confirm removed
    resp2 = client.get("/schedules")
    assert len(resp2.json()) == 0
