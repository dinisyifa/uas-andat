import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.routers.admin_film import get_db

client = TestClient(app)

def override_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_db


# ==============================
# TEST CRUD FILM
# ==============================

def test_movie_create():
    payload = {
        "judul": "Film Test",
        "genre": "Horror",
        "tahun": 2024,
        "rating": 8.5
    }

    res = client.post("/admin/film", json=payload)
    assert res.status_code == 201
    assert res.json()["judul"] == "Film Test"


def test_movie_get_list():
    res = client.get("/admin/film")
    assert res.status_code == 200
    assert type(res.json()) is list


def test_movie_get_by_id():
    # ambil id pertama
    list_res = client.get("/admin/film").json()
    first_id = list_res[0]["id"]

    res = client.get(f"/admin/film/{first_id}")
    assert res.status_code == 200
    assert res.json()["id"] == first_id


def test_movie_update():
    list_res = client.get("/admin/film").json()
    first_id = list_res[0]["id"]

    payload = { "rating": 9.0 }

    res = client.patch(f"/admin/film/{first_id}", json=payload)
    assert res.status_code == 200
    assert res.json()["rating"] == 9.0


def test_movie_delete():
    list_res = client.get("/admin/film").json()
    first_id = list_res[0]["id"]

    res = client.delete(f"/admin/film/{first_id}")
    assert res.status_code == 200
