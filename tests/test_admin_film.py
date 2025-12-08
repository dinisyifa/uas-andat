from fastapi.testclient import TestClient
from app.main import app   # pastikan ini file utama FastAPI kamu

client = TestClient(app)

# ============================================================
#                        MOVIES TEST
# ============================================================

def test_get_movies():
    response = client.get("/movies")
    assert response.status_code == 200
    assert "data" in response.json()


def test_add_movie():
    payload = {
        "title": "Test Movie",
        "genre": "Action",
        "durasi": 120,
        "director": "Tester",
        "rating": "PG-13"
    }

    response = client.post("/movies", json=payload)
    assert response.status_code == 200

    data = response.json()["data"]
    assert "code" in data
    assert data["title"] == "Test Movie"


def test_update_movie():
    # ambil movie terakhir untuk di-update
    all_movies = client.get("/movies").json()["data"]
    assert len(all_movies) > 0

    code = all_movies[-1]["code"]

    payload = {
        "title": "Updated Movie",
        "genre": "Drama",
        "durasi": 100,
        "director": "Updater",
        "rating": "R"
    }

    response = client.put(f"/movies/{code}", json=payload)
    assert response.status_code == 200
    assert response.json()["data"]["title"] == "Updated Movie"


def test_delete_movie():
    # ambil movie terakhir untuk dihapus
    all_movies = client.get("/movies").json()["data"]
    assert len(all_movies) > 0

    code = all_movies[-1]["code"]

    response = client.delete(f"/movies/{code}")
    assert response.status_code == 200
    assert "berhasil dihapus" in response.json()["status"]


# ============================================================
#                        STUDIOS TEST
# ============================================================

def test_get_studios():
    r = client.get("/studios")
    assert r.status_code == 200


def test_add_studio():
    payload = {"rows": 5, "cols": 7}
    r = client.post("/studios", json=payload)

    assert r.status_code == 200
    assert r.json()["data"]["rows"] == 5


def test_update_studio():
    studios = client.get("/studios").json()["data"]
    assert len(studios) > 0

    code = studios[-1]["code"]

    payload = {"rows": 10, "cols": 20}
    r = client.put(f"/studios/{code}", json=payload)

    assert r.status_code == 200
    assert r.json()["rows"] == 10


def test_delete_studio():
    studios = client.get("/studios").json()["data"]
    assert len(studios) > 0

    code = studios[-1]["code"]

    r = client.delete(f"/studios/{code}")
    assert r.status_code == 200


# ============================================================
#                      MEMBERSHIPS TEST
# ============================================================

def test_get_members():
    r = client.get("/members")
    assert r.status_code == 200


def test_add_member():
    payload = {"nama": "Member Test"}
    r = client.post("/members", json=payload)

    assert r.status_code == 200
    assert r.json()["data"]["nama"] == "Member Test"


def test_update_member():
    members = client.get("/members").json()["data"]
    assert len(members) > 0

    code = members[-1]["code"]

    payload = {"nama": "Updated Member"}
    r = client.put(f"/members/{code}", json=payload)

    assert r.status_code == 200
    assert r.json()["nama"] == "Updated Member"


def test_delete_member():
    members = client.get("/members").json()["data"]
    assert len(members) > 0

    code = members[-1]["code"]

    r = client.delete(f"/members/{code}")
    assert r.status_code == 200
