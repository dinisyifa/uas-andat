import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import komponen aplikasi utama
from app.main import app
from app.database import get_db
from app.models import Movie, Studio, Jadwal 
from datetime import datetime, time, date

# ======================================================
# SETUP DATABASE ASLI
# ======================================================
DATABASE_URL = "sqlite:///./app.db" 

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


# ======================================================
# FIXTURE CLEAR TABLE
# ======================================================
@pytest.fixture(autouse=True)
def clear_db():
    db = TestingSessionLocal()
    db.query(Jadwal).delete()
    db.query(Movie).delete()
    db.query(Studio).delete()
    db.commit()
    db.close()


# ======================================================
# HELPER FUNCTIONS
# ======================================================
def create_movie(title="Inception", duration=120):
    """Membuat Movie dan mengembalikan code (MOVXXX)."""
    res = client.post("/movies", json={
        "title": title, "genre": "Sci-Fi", "durasi": duration,
        "director": "Nolan", "rating": "PG13"
    })
    assert res.status_code == 200
    return res.json()["data"]["code"]


def create_studio(rows=5, cols=10):
    """Membuat Studio dan mengembalikan code (STXXX)."""
    res = client.post("/studios", json={"rows": rows, "cols": cols})
    assert res.status_code == 200
    return res.json()["data"]["code"]


def create_schedule(m_code, s_code, tanggal="2025-12-10", jam="19:00"):
    """Membuat Jadwal. Tanggal dan jam adalah string."""
    res = client.post("/schedules", json={
        "movie_code": m_code,
        "studio_code": s_code,
        "tanggal": tanggal,
        "jam": jam
    })
    
    assert res.status_code == 200
    data = res.json()
    assert data["code"].startswith("SCH")
    return data["code"]


# ======================================================
# TEST ENDPOINT: POST /schedules
# ======================================================
def test_add_schedule_success():
    m_code = create_movie()
    s_code = create_studio()
    tanggal_input = "2025-12-10"
    jam_input = "19:00"
    
    res = client.post("/schedules", json={
        "movie_code": m_code,
        "studio_code": s_code,
        "tanggal": tanggal_input,
        "jam": jam_input
    })

    assert res.status_code == 200
    data = res.json()
    assert data["movie_code"] == m_code
    assert data["studio_code"] == s_code
    assert data["movie_title"] == "Inception"
    # FIX: Output jam dari API akan menjadi string, seringkali dalam format HH:MM:SS
    # Kita cek apakah output jam dimulai dengan input jam (misal 19:00:00 atau 19:00)
    assert data["jam"].startswith(jam_input) 
    assert data["tanggal"] == tanggal_input # Assertion untuk tanggal string
    assert data["code"].startswith("SCH")


def test_add_schedule_movie_not_found():
    s_code = create_studio()
    
    res = client.post("/schedules", json={
        "movie_code": "MOVXXX", 
        "studio_code": s_code,
        "tanggal": "2025-12-10",
        "jam": "19:00"
    })

    assert res.status_code == 404
    assert "Movie tidak ditemukan" in res.json()["detail"]


def test_add_schedule_studio_not_found():
    m_code = create_movie()
    
    res = client.post("/schedules", json={
        "movie_code": m_code,
        "studio_code": "STXXX",
        "tanggal": "2025-12-10",
        "jam": "19:00"
    })

    assert res.status_code == 404
    assert "Studio tidak ditemukan" in res.json()["detail"]


# ======================================================
# TEST ENDPOINT: GET /schedules
# ======================================================
def test_get_schedules_empty():
    res = client.get("/schedules")
    assert res.status_code == 200
    assert len(res.json()) == 0


def test_get_schedules_multiple():
    m_code1 = create_movie(title="Movie A")
    s_code1 = create_studio(rows=1, cols=1)
    m_code2 = create_movie(title="Movie B")
    s_code2 = create_studio(rows=2, cols=2)

    create_schedule(m_code1, s_code1, "2025-12-10", "10:00")
    create_schedule(m_code2, s_code2, "2025-12-11", "14:30")

    res = client.get("/schedules")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2
    assert data[0]["movie_title"] == "Movie A"
    assert data[1]["movie_title"] == "Movie B"
    assert data[1]["tanggal"] == "2025-12-11"
    # FIX: Memastikan output jam sesuai dengan input (misal 14:30:00)
    assert data[1]["jam"].startswith("14:30")


# ======================================================
# TEST ENDPOINT: PUT /schedules/{code}
# ======================================================
def test_update_schedule_success():
    m_code_old = create_movie(title="Old Movie")
    s_code_old = create_studio(rows=5, cols=5)
    
    schedule_code = create_schedule(m_code_old, s_code_old) 

    m_code_new = create_movie(title="New Movie", duration=150)
    s_code_new = create_studio(rows=10, cols=10)
    tanggal_update = "2025-12-20"
    jam_update = "21:05"

    res = client.put(f"/schedules/{schedule_code}", json={
        "movie_code": m_code_new,
        "studio_code": s_code_new,
        "tanggal": tanggal_update, 
        "jam": jam_update
    })

    assert res.status_code == 200
    data = res.json()
    assert data["code"] == schedule_code
    assert data["movie_title"] == "New Movie"
    assert data["tanggal"] == tanggal_update
    assert data["jam"].startswith(jam_update) # Assertion untuk jam yang diupdate
    assert data["movie_code"] == m_code_new
    assert data["studio_code"] == s_code_new


def test_update_schedule_not_found():
    m_code = create_movie()
    s_code = create_studio()

    res = client.put("/schedules/SCHXXX", json={ 
        "movie_code": m_code,
        "studio_code": s_code,
        "tanggal": "2025-12-20",
        "jam": "21:00"
    })

    assert res.status_code == 404
    assert "Jadwal tidak ditemukan" in res.json()["detail"]


# ======================================================
# TEST ENDPOINT: DELETE /schedules/{code}
# ======================================================
def test_delete_schedule_success():
    m_code = create_movie()
    s_code = create_studio()
    
    schedule_code = create_schedule(m_code, s_code) 

    res = client.delete(f"/schedules/{schedule_code}")

    assert res.status_code == 200
    assert "berhasil dihapus" in res.json()["status"]

    verify_res = client.get("/schedules")
    assert len(verify_res.json()) == 0


def test_delete_schedule_not_found():
    res = client.delete("/schedules/SCHXXX") 
    assert res.status_code == 404
    assert "Jadwal tidak ditemukan" in res.json()["detail"]