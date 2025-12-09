import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from app.main import app
from app.database import SessionLocal
from app.models import Movie, Studio, Membership, Jadwal, Order, OrderSeat

client = TestClient(app)

@pytest.fixture
def db_session():
    db = SessionLocal()

    db.execute(text("SET FOREIGN_KEY_CHECKS=0;"))
    db.execute(text("TRUNCATE TABLE order_seats;"))
    db.execute(text("TRUNCATE TABLE orders;"))
    db.execute(text("TRUNCATE TABLE Jadwal;"))
    db.execute(text("TRUNCATE TABLE movies;"))
    db.execute(text("TRUNCATE TABLE studios;"))
    db.execute(text("TRUNCATE TABLE memberships;"))
    db.execute(text("SET FOREIGN_KEY_CHECKS=1;"))
    db.commit()

    yield db
    db.close()

# ======================================================
# MOVIES CRUD TESTS
# ======================================================

def test_add_movie(db_session):
    res = client.post("/movies", json={
        "title": "Avatar",
        "genre": "Action",
        "durasi": 180,
        "director": "James Cameron",
        "rating": "PG-13"
    })
    assert res.status_code == 200
    assert "MOV" in res.json()["data"]["code"]


def test_get_movies(db_session):
    db_session.add(Movie(id=1, code="MOV001", title="Test Film", genre="Drama", 
                         durasi=120, director="Dir", rating="PG", price=45000))
    db_session.commit()

    res = client.get("/movies")
    assert res.status_code == 200
    assert len(res.json()["data"]) == 1


def test_update_movie_success(db_session):
    db_session.add(Movie(id=1, code="MOV001", title="Old", genre="Drama", 
                         durasi=100, director="Some", rating="R", price=30000))
    db_session.commit()

    res = client.put("/movies/MOV001", json={
        "title": "New Title",
        "genre": "Action",
        "durasi": 150,
        "director": "A",
        "rating": "PG"
    })

    assert res.status_code == 200
    assert res.json()["data"]["title"] == "New Title"


def test_update_movie_not_found(db_session):
    res = client.put("/movies/MOV999", json={
        "title": "X",
        "genre": "Y",
        "durasi": 90,
        "director": "Z",
        "rating": "PG"
    })
    assert res.status_code == 404


def test_delete_movie(db_session):
    client.post("/movies", json={
        "title": "Test Movie",
        "genre": "Action",
        "durasi": 120,
        "director": "Someone",
        "rating": "PG-13"
    })

    db_session.query(Jadwal).delete()
    db_session.commit()

    res = client.delete("/movies/MOV001")
    assert res.status_code == 200


# ======================================================
# STUDIOS CRUD TESTS
# ======================================================

def test_add_studio(db_session):
    res = client.post("/studios", json={"rows": 8, "cols": 12})
    assert res.status_code == 200
    assert "ST" in res.json()["data"]["code"]


def test_get_studios(db_session):
    db_session.add(Studio(id=1, code="ST001", name="Studio 1", rows=8, cols=12))
    db_session.commit()

    res = client.get("/studios")
    assert res.status_code == 200
    assert len(res.json()["data"]) == 1


def test_update_studio_success(db_session):
    db_session.add(Studio(id=1, code="ST001", name="Studio 1", rows=6, cols=10))
    db_session.commit()

    res = client.put("/studios/ST001", json={"rows": 10, "cols": 15})
    assert res.status_code == 200
    assert res.json()["rows"] == 10


def test_update_studio_not_found(db_session):
    res = client.put("/studios/ST999", json={"rows": 8, "cols": 12})
    assert res.status_code == 404


def test_delete_studio(db_session):
    db_session.add(Studio(id=1, code="ST001", name="Studio 1", rows=8, cols=12))
    db_session.commit()

    # Bersihkan FK dulu
    db_session.query(Jadwal).delete()
    db_session.commit()

    res = client.delete("/studios/ST001")
    assert res.status_code == 200


# ======================================================
# MEMBERS CRUD TESTS
# ======================================================

def test_add_membership(db_session):
    res = client.post("/members", json={"nama": "John"})
    assert res.status_code == 200
    assert "MEM" in res.json()["data"]["code"]


def test_get_memberships(db_session):
    db_session.add(Membership(id=1, code="MEM001", nama="Test Member"))
    db_session.commit()

    res = client.get("/members")
    assert res.status_code == 200
    assert len(res.json()["data"]) == 1


def test_update_membership_success(db_session):
    db_session.add(Membership(id=1, code="MEM001", nama="User"))
    db_session.commit()

    res = client.put("/members/MEM001", json={"nama": "Updated"})
    assert res.status_code == 200
    assert res.json()["nama"] == "Updated"


def test_update_membership_not_found(db_session):
    res = client.put("/members/MEM999", json={"nama": "X"})
    assert res.status_code == 404


def test_delete_membership(db_session):
    db_session.add(Membership(id=1, code="MEM001", nama="User"))
    db_session.commit()

    res = client.delete("/members/MEM001")
    assert res.status_code == 200
    assert "berhasil dihapus" in res.json()["status"]