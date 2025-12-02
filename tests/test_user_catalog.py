import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from app.routers import user_catalog
from app.routers.admin_film import list_film
from app.routers.admin_jadwal import list_jadwal

# Setup aplikasi FastAPI sementara untuk pengujian
app = FastAPI()
app.include_router(user_catalog.router)
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_dummy_data():
    """Reset semua data sebelum tiap test"""
    list_film.clear()
    list_jadwal.clear()
    user_catalog.SEATS_BY_SCHEDULE.clear()

    # Tambahkan 1 film dan 1 jadwal
    list_film.append({
        "id": "mov1",
        "title": "Inception",
        "duration": 120,
        "price": 50000,
        "genre": "Sci-Fi",
        "rating_usia": "13+",
        "sutradara": "Christopher Nolan",
    })
    list_jadwal.append({
        "id_jadwal": "sch1",
        "movie_id": "mov1",
        "movie_title": "Inception",
        "studio_name": "Studio 1",
        "date": "2025-10-10",
        "time": "19:00"
    })


# ================================================================
# TEST 1 - now_playing()
# ================================================================
def test_now_playing_success():
    """Menampilkan daftar film yang sedang tayang"""
    res = client.get("/now_playing")
    assert res.status_code == 200
    data = res.json()
    assert data["count"] == 1
    assert data["data"][0]["title"] == "Inception"
    assert data["message"] == "Daftar film yang sedang tayang berhasil diambil"


def test_now_playing_no_movies():
    """Menangani kondisi ketika tidak ada film"""
    list_film.clear()
    res = client.get("/now_playing")
    assert res.status_code == 404
    assert res.json()["detail"] == "Tidak ada film yang sedang tayang."


# ================================================================
# TEST 2 - detail_film()
# ================================================================
def test_detail_film_success():
    """Menampilkan detail film dan daftar jadwalnya"""
    res = client.get("/now_playing/mov1/details")
    assert res.status_code == 200
    data = res.json()
    assert data["title"] == "Inception"
    assert data["schedules"][0]["studio"] == "Studio 1"
    assert data["schedules"][0]["waktu"] == "19:00"


def test_detail_film_not_found():
    """Menangani film dengan ID yang tidak ada"""
    res = client.get("/now_playing/mov999/details")
    assert res.status_code == 404
    assert res.json()["detail"] == "Film dengan ID mov999 tidak ditemukan."


# ================================================================
# TEST 3 - denah_kursi()
# ================================================================
def test_denah_kursi_success():
    """Menampilkan peta kursi berdasarkan jadwal"""
    res = client.get("/schedules/sch1/seats")
    assert res.status_code == 200
    data = res.json()
    assert data["schedule_id"] == "sch1"
    assert "display" in data
    # Baris pertama adalah layar
    assert "SCREEN" in data["display"][0]
    # Baris kedua ada nomor kursi kiri dan kanan
    assert "1" in data["display"][1]
    assert "12" in data["display"][1]


def test_denah_kursi_auto_initialize():
    """Jika jadwal belum punya data kursi, sistem membuat denah baru otomatis"""
    res = client.get("/schedules/unknown_id/seats")
    assert res.status_code == 200
    data = res.json()
    assert data["schedule_id"] == "unknown_id"
    assert len(data["display"]) == 10  # 8 baris kursi + header + nomor kursi
