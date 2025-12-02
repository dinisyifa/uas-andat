import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from app.routers import admin_jadwal
from app.routers.admin_film import list_film, list_studio

# =====================================================
# SETUP APLIKASI DAN DATA DUMMY
# =====================================================
app = FastAPI()
app.include_router(admin_jadwal.router)
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_data():
    list_film.clear()
    list_studio.clear()
    admin_jadwal.list_jadwal.clear()

    # Dummy film
    list_film.append({"id": "mov1", "title": "Inception"})
    # Dummy studio
    list_studio.append({"id": "st1", "name": "Studio 1"})


# =====================================================
# TEST 1 - Tambah Jadwal Berhasil
# =====================================================
def test_tambah_jadwal_berhasil():
    payload = {
        "movie_id": "mov1",
        "studio_id": "st1",
        "date": "2025-10-15",
        "time": "12.15 - 15.05"
    }
    res = client.post("/schedules", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["message"] == "Jadwal berhasil dibuat"
    assert data["data"]["movie_id"] == "mov1"
    assert data["data"]["studio_id"] == "st1"
    # layout 8 baris × (6+1 lorong +6 kolom)
    assert len(data["data"]["seats"]) == 8
    assert len(data["data"]["seats"][0]) == 13


# =====================================================
# TEST 2 - Gagal Tambah (Film Tidak Ditemukan)
# =====================================================
def test_tambah_jadwal_gagal_film_tidak_ada():
    payload = {
        "movie_id": "mov999",
        "studio_id": "st1",
        "date": "2025-10-10",
        "time": "19:00"
    }
    res = client.post("/schedules", json=payload)
    assert res.status_code == 404
    assert res.json()["detail"] == "Film tidak ditemukan"


# =====================================================
# TEST 3 - Gagal Tambah (Studio Tidak Ditemukan)
# =====================================================
def test_tambah_jadwal_gagal_studio_tidak_ada():
    payload = {
        "movie_id": "mov1",
        "studio_id": "st999",
        "date": "2025-10-10",
        "time": "19:00"
    }
    res = client.post("/schedules", json=payload)
    assert res.status_code == 404
    assert res.json()["detail"] == "Studio tidak ditemukan"


# =====================================================
# TEST 4 - Lihat Semua Jadwal
# =====================================================
def test_lihat_semua_jadwal():
    client.post("/schedules", json={
        "movie_id": "mov1",
        "studio_id": "st1",
        "date": "2025-10-15",
        "time": "10.00 - 12.00"
    })

    res = client.get("/schedules")
    assert res.status_code == 200
    data = res.json()
    assert data["message"] == "Daftar jadwal berhasil diambil!"
    assert len(data["data"]) == 1


# =====================================================
# TEST 5 - Update Jadwal
# =====================================================
def test_update_jadwal_berhasil():
    # Tambah dulu jadwal baru
    client.post("/schedules", json={
        "movie_id": "mov1",
        "studio_id": "st1",
        "date": "2025-10-15",
        "time": "10.00 - 12.00"
    })

    updated = {
        "movie_id": "mov1",
        "studio_id": "st1",
        "date": "2025-10-20",
        "time": "14.00 - 16.00"
    }

    # penting: gunakan param yang sesuai definisi di router → {schedule_id}
    res = client.put("/schedules/sch1", json=updated)
    assert res.status_code == 200
    data = res.json()
    assert "berhasil diperbarui" in data["message"]
    assert data["data"]["date"] == "2025-10-20"
    assert data["data"]["time"] == "14.00 - 16.00"


# =====================================================
# TEST 6 - Hapus Jadwal
# =====================================================
def test_hapus_jadwal_berhasil():
    client.post("/schedules", json={
        "movie_id": "mov1",
        "studio_id": "st1",
        "date": "2025-10-15",
        "time": "12.00 - 14.00"
    })

    res = client.delete("/schedules/sch1")
    assert res.status_code == 200
    assert "berhasil dihapus" in res.json()["message"]


# =====================================================
# TEST 7 - Gagal Hapus (Tidak Ditemukan)
# =====================================================
def test_hapus_jadwal_tidak_ditemukan():
    res = client.delete("/schedules/sch999")
    assert res.status_code == 404
    assert res.json()["detail"] == "Jadwal tidak ditemukan"
