import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from app.main import app
from app.database import SessionLocal
from app.models import Movie, Studio, Membership

client = TestClient(app)

# Fixture: DB asli, reset tabel setiap test
@pytest.fixture
def db():
    db = SessionLocal()

    db.execute(text("SET FOREIGN_KEY_CHECKS=0;"))
    db.execute(text("TRUNCATE TABLE movies;"))
    db.execute(text("TRUNCATE TABLE studios;"))
    db.execute(text("TRUNCATE TABLE memberships;"))
    db.execute(text("SET FOREIGN_KEY_CHECKS=1;"))
    db.commit()

    yield db
    db.close()

# ======================================================
# TEST MOVIES CRUD
# ======================================================

def test_add_movie(db):
    payload = {
        "title": "Avatar",
        "genre": "Action",
        "durasi": 180,
        "director": "James Cameron",
        "rating": "PG-13"
    }

    response = client.post("/movies", json=payload)
    assert response.status_code == 200
    result = response.json()["data"]
    
    assert result["title"] == "Avatar"
    assert "MOV" in result["code"]


def test_get_movies(db):
    # insert dummy
    db.add(Movie(id=1, code="MOV001", title="Test Film", genre="Drama", durasi=120, director="Director", rating="R", price=45000))
    db.commit()

    res = client.get("/movies")
    assert res.status_code == 200
    assert len(res.json()["data"]) == 1


def test_update_movie_success(db):
    db.add(Movie(id=1, code="MOV001", title="Old", genre="Drama", durasi=100, director="Someone", rating="R", price=30000))
    db.commit()

    payload = {
        "title": "New Title",
        "genre": "Action",
        "durasi": 150,
        "director": "A",
        "rating": "PG"
    }

    res = client.put("/movies/MOV001", json=payload)
    assert res.status_code == 200
    assert res.json()["data"]["title"] == "New Title"


def test_update_movie_not_found(db):
    res = client.put("/movies/MOV999", json={
        "title": "X",
        "genre": "Y",
        "durasi": 100,
        "director": "Z",
        "rating": "R"
    })
    assert res.status_code == 404


def test_delete_movie(db):
    db.add(Movie(id=1, code="MOV001", title="T", genre="Drama", durasi=90, director="D", rating="R", price=25000))
    db.commit()

    res = client.delete("/movies/MOV001")
    assert res.status_code == 200
    assert "berhasil dihapus" in res.json()["status"]

# ======================================================
# TEST STUDIOS CRUD
# ======================================================

def test_add_studio(db):
    payload = {"rows": 8, "cols": 12}
    res = client.post("/studios", json=payload)
    assert res.status_code == 200
    assert "ST" in res.json()["data"]["code"]


def test_get_studios(db):
    db.add(Studio(id=1, code="ST001", name="Studio 1", rows=8, cols=12))
    db.commit()

    res = client.get("/studios")
    assert res.status_code == 200
    assert len(res.json()["data"]) == 1


def test_update_studio_success(db):
    db.add(Studio(id=1, code="ST001", name="Studio 1", rows=6, cols=10))
    db.commit()

    payload = {"rows": 10, "cols": 15}
    res = client.put("/studios/ST001", json=payload)
    assert res.status_code == 200
    assert res.json()["rows"] == 10


def test_update_studio_not_found(db):
    res = client.put("/studios/ST999", json={"rows": 8, "cols": 12})
    assert res.status_code == 404


def test_delete_studio(db):
    db.add(Studio(id=1, code="ST001", name="Studio 1", rows=8, cols=12))
    db.commit()

    res = client.delete("/studios/ST001")
    assert res.status_code == 200
    assert "berhasil dihapus" in res.json()["status"]

# ======================================================
# TEST MEMBERS CRUD
# ======================================================

def test_add_membership(db):
    res = client.post("/members", json={"nama": "John"})
    assert res.status_code == 200
    assert "MEM" in res.json()["data"]["code"]


def test_get_memberships(db):
    db.add(Membership(id=1, code="MEM001", nama="Test Member"))
    db.commit()

    res = client.get("/members")
    assert res.status_code == 200
    assert len(res.json()["data"]) == 1


def test_update_membership_success(db):
    db.add(Membership(id=1, code="MEM001", nama="User"))
    db.commit()

    res = client.put("/members/MEM001", json={"nama": "Updated"})
    assert res.status_code == 200
    assert res.json()["nama"] == "Updated"


def test_update_membership_not_found(db):
    res = client.put("/members/MEM999", json={"nama": "X"})
    assert res.status_code == 404


def test_delete_membership(db):
    db.add(Membership(id=1, code="MEM001", nama="User"))
    db.commit()

    res = client.delete("/members/MEM001")
    assert res.status_code == 200
    assert "berhasil dihapus" in res.json()["status"]