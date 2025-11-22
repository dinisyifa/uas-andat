from fastapi.testclient import TestClient
from app.main import app 

client = TestClient(app)


# ============================
# TEST CRUD MOVIES
# ============================

def test_get_all_movies():
    response = client.get("/movies")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert isinstance(data["data"], list)


def test_get_single_movie():
    response = client.get("/movies/mov1")
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["id"] == "mov1"


def test_create_movie_success():
    new_movie = {
        "id": "mov99",
        "title": "Testing The Movie",
        "duration": "123 menit",
        "genre": "Sci-Fi",
        "sutradara": "John Doe",
        "rating_usia": "13+",
        "price": "Rp50.000"
    }
    response = client.post("/movies", json=new_movie)
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["id"] == "mov99"


def test_create_movie_duplicate_id():
    new_movie = {
        "id": "mov99",
        "title": "Duplicate Test",
        "duration": "120 menit",
        "genre": "Action",
        "sutradara": "Jane Doe",
        "rating_usia": "PG-13",
        "price": "Rp45.000"
    }
    response = client.post("/movies", json=new_movie)
    assert response.status_code == 400
    assert response.json()["detail"] == "ID film sudah ada"


def test_update_movie():
    updated_data = {
        "id": "mov99",
        "title": "Updated Movie",
        "duration": "150 menit",
        "genre": "Drama",
        "sutradara": "Tester",
        "rating_usia": "17+",
        "price": "Rp60.000"
    }
    response = client.put("/movies/mov99", json=updated_data)
    assert response.status_code == 200
    assert response.json()["data"]["title"] == "Updated Movie"


def test_delete_movie():
    response = client.delete("/movies/mov99")
    assert response.status_code == 200
    assert "berhasil dihapus" in response.json()["message"]


def test_get_deleted_movie_should_fail():
    response = client.get("/movies/mov99")
    assert response.status_code == 404
    assert response.json()["detail"] == "Film tidak ditemukan"

# ============================
# TEST CRUD STUDIOS
# ============================

def test_get_all_studios():
    response = client.get("/studios")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert isinstance(data["data"], list)


def test_create_studio_success():
    new_studio = {
        "id": "st99",
        "name": "Studio 99",
        "capacity" : 96
    }
    response = client.post("/studios", json=new_studio)
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["id"] == "st99"
    assert data["data"]["name"] == "Studio 99"


def test_create_studio_duplicate_id():
    new_studio = {
        "id": "st99",
        "name": "Studio 99",
        "capacity" : 96
    }
    response = client.post("/studios", json=new_studio)
    assert response.status_code == 400
    assert response.json()["detail"] == "ID studio sudah ada"


def test_update_studio():
    updated_studio = {
        "id": "st99",
        "name": "Studio 99",
        "capacity" : 96
    }
    response = client.put("/studios/st99", json=updated_studio)
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["capacity"] == 96


def test_delete_studio():
    response = client.delete("/studios/st99")
    assert response.status_code == 200
    assert "berhasil dihapus" in response.json()["message"]