import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from app.routers import user_transaction
from app.routers.admin_film import list_film
from app.routers.admin_jadwal import list_jadwal

app = FastAPI()
app.include_router(user_transaction.router)
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_data():
    """Reset semua variabel global sebelum tiap test"""
    list_film.clear()
    list_jadwal.clear()
    user_transaction.cart_items.clear()
    user_transaction.pending_orders.clear()
    user_transaction.transaction_history.clear()

    # Setup dummy film dan jadwal
    list_film.append({
        "id": "f1",
        "title": "Interstellar",
        "price": "Rp75.000"
    })

    list_jadwal.append({
        "id_jadwal": "J1",
        "movie_id": "f1",
        "studio_name": "Studio 2",
        "date": "2025-10-14",
        "time": "20:00",
        "seats": [
            [{"seat": "A1", "available": True}, {"seat": "A2", "available": True}],
            [{"seat": "B1", "available": True}, {"seat": "B2", "available": True}]
        ]
    })


# ================================================================
# TEST 1 - Tambah ke keranjang
# ================================================================
def test_add_ticket_success():
    payload = {
        "schedule_id": "J1",
        "movie_title": "Interstellar",
        "seat_number": "A1"
    }
    res = client.post("/cart/add", json=payload)
    assert res.status_code == 200
    assert res.json()["message"] == "Tiket berhasil ditambahkan ke keranjang"


def test_add_ticket_fail_schedule_not_found():
    payload = {
        "schedule_id": "INVALID",
        "movie_title": "Interstellar",
        "seat_number": "A1"
    }
    res = client.post("/cart/add", json=payload)
    assert res.status_code == 404
    assert "Jadwal tidak ditemukan" in res.json()["detail"]


def test_add_ticket_fail_seat_not_available():
    # Jadikan kursi A1 unavailable
    list_jadwal[0]["seats"][0][0]["available"] = False
    payload = {
        "schedule_id": "J1",
        "movie_title": "Interstellar",
        "seat_number": "A1"
    }
    res = client.post("/cart/add", json=payload)
    assert res.status_code == 400
    assert "Kursi tidak tersedia" in res.json()["detail"]


# ================================================================
# TEST 2 - Lihat dan hapus isi keranjang
# ================================================================
def test_view_and_remove_cart():
    # Tambahkan item
    payload = {
        "schedule_id": "J1",
        "movie_title": "Interstellar",
        "seat_number": "A1"
    }
    client.post("/cart/add", json=payload)

    # Lihat isi keranjang
    res_view = client.get("/cart")
    assert res_view.status_code == 200
    assert "items" in res_view.json()
    assert len(res_view.json()["items"]) == 1

    # Hapus item
    item_id = res_view.json()["items"][0]["item_id"]
    res_delete = client.delete(f"/cart/remove/{item_id}")
    assert res_delete.status_code == 200
    assert "berhasil dihapus" in res_delete.json()["message"]

    # Pastikan keranjang kosong
    res_empty = client.get("/cart")
    assert res_empty.status_code == 404
    assert "Keranjang kosong" in res_empty.json()["detail"]


# ================================================================
# TEST 3 - Checkout
# ================================================================
def test_checkout_success():
    # Tambahkan item ke keranjang
    payload = {
        "schedule_id": "J1",
        "movie_title": "Interstellar",
        "seat_number": "A1"
    }
    client.post("/cart/add", json=payload)

    # Pilih metode pembayaran
    res_checkout = client.post("/checkout/payment", json={"payment_method": "Transfer Bank"})
    assert res_checkout.status_code == 200
    data = res_checkout.json()
    assert data["order_id"].startswith("ORD-")
    assert data["payment_method"] == "Transfer Bank"
    assert data["total_price"] > 0

    # Pastikan keranjang dikosongkan
    assert user_transaction.cart_items == []


def test_checkout_empty_cart():
    res_checkout = client.post("/checkout/payment", json={"payment_method": "Transfer Bank"})
    assert res_checkout.status_code == 400
    assert "Keranjang belanja kosong" in res_checkout.json()["detail"]
