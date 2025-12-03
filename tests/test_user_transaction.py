# tests/test_cart_checkout.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app                 # pastikan main.py men-register router ini ke FastAPI app
from app.database import get_db
from app.models import Base, Movie, Studio, Jadwal, Membership, Cart, OrderSeat, Order

# -------------------------
# Setup in-memory test DB
# -------------------------
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# create all tables in test DB
Base.metadata.create_all(bind=engine)

# override get_db dependency to use the testing session
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


# -------------------------
# Helper: create seed data
# -------------------------
def create_seed_data(db):
    """
    Membuat:
      - 1 Movie (MOV001)
      - 1 Studio (ST001)
      - 1 Jadwal (JAD001) untuk movie+studio
      - 1 Membership (MEM001)
    Mengembalikan tuple (movie, studio, jadwal, member)
    """
    # movie
    movie = Movie(
        code="MOV001",
        title="Test Movie",
        genre="Action",
        durasi=100,
        director="Director",
        rating="PG",
        price=40000
    )
    db.add(movie)
    db.flush()  # agar movie.id ter-assign

    # studio
    studio = Studio(
        code="ST001",
        name="Studio 1",
        rows=10,
        cols=8
    )
    db.add(studio)
    db.flush()

    # jadwal (pastikan kolom movie_id, studio_id cukup; relasi di model diharapkan ada)
    jadwal = Jadwal(
        code="JAD0001",
        movie_id=movie.id,
        movie_code=movie.code,
        studio_id=studio.id,
        studio_code=studio.code,
        tanggal="2024-12-01",
        jam="11:00:00"
    )
    db.add(jadwal)
    db.flush()

    member = Membership(
        code="MEM001",
        nama="Member A"
    )
    db.add(member)
    db.commit()

    # reload to get full objects
    movie = db.query(Movie).filter_by(id=movie.id).first()
    studio = db.query(Studio).filter_by(id=studio.id).first()
    jadwal = db.query(Jadwal).filter_by(id=jadwal.id).first()
    member = db.query(Membership).filter_by(id=member.id).first()
    return movie, studio, jadwal, member


# -------------------------
# Fixtures
# -------------------------
@pytest.fixture(autouse=True)
def setup_db():
    # each test gets a fresh DB (recreate tables)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    # create seed data
    db = TestingSessionLocal()
    try:
        movie, studio, jadwal, member = create_seed_data(db)
        yield {"movie": movie, "studio": studio, "jadwal": jadwal, "member": member, "db": db}
    finally:
        db.close()


# -------------------------
# Tests
# -------------------------

def test_add_to_cart_success(setup_db):
    jadwal = setup_db["jadwal"]
    member = setup_db["member"]

    payload = {
        "membership_code": member.code,
        "jadwal_id": jadwal.id,
        "row": "A",
        "col": 1
    }
    res = client.post("/cart/add", json=payload)
    assert res.status_code == 200
    data = res.json()
    # router returns {"message": "Berhasil masuk keranjang", "seat": "A1"}
    assert "Berhasil masuk keranjang" in data.get("message", "") or data.get("message") == "Berhasil masuk keranjang"
    assert data.get("seat") == "A1"


def test_add_to_cart_seat_already_sold(setup_db):
    # simulate seat already sold by inserting an OrderSeat for that jadwal,row,col
    db = TestingSessionLocal()
    jadwal = setup_db["jadwal"]
    member = setup_db["member"]

    # create an order and orderseat directly (so seat is "sold")
    # create a minimal Order so that OrderSeat.order_id FK can reference it (Order model fields must match your actual model)
    order = Order(
        code="ORDTEST",
        membership_id=member.id,
        membership_code=member.code,
        jadwal_id=jadwal.id,
        payment_method="QRIS",
        seat_count=1,
        promo_name="NO PROMO",
        discount=0,
        total_price=40000,
        final_price=40000,
        cash=40000,
        change=0,
        transaction_date="2024-12-01",
        hari="Senin"
    )
    db.add(order)
    db.flush()

    os = OrderSeat(
        order_id=order.id,
        jadwal_id=jadwal.id,
        studio_id=setup_db["studio"].id,
        row="A",
        col=1
    )
    db.add(os)
    db.commit()
    db.close()

    # now try to add same seat to cart
    payload = {
        "membership_code": member.code,
        "jadwal_id": jadwal.id,
        "row": "A",
        "col": 1
    }
    res = client.post("/cart/add", json=payload)
    assert res.status_code == 400
    assert res.json()["detail"] == "Kursi sudah terjual"


def test_add_to_cart_duplicate_in_cart(setup_db):
    jadwal = setup_db["jadwal"]
    member = setup_db["member"]

    payload = {
        "membership_code": member.code,
        "jadwal_id": jadwal.id,
        "row": "B",
        "col": 2
    }

    # first add
    r1 = client.post("/cart/add", json=payload)
    assert r1.status_code == 200

    # duplicate add -> should return message about already in cart
    r2 = client.post("/cart/add", json=payload)
    assert r2.status_code == 200
    # router returns {"message": "Kursi sudah ada di keranjang"}
    assert r2.json().get("message") == "Kursi sudah ada di keranjang"


def test_get_cart_contents_and_total(setup_db):
    db = TestingSessionLocal()
    movie, studio, jadwal, member = setup_db["movie"], setup_db["studio"], setup_db["jadwal"], setup_db["member"]

    # add two cart items directly (or via endpoint)
    client.post("/cart/add", json={"membership_code": member.code, "jadwal_id": jadwal.id, "row": "C", "col": 1})
    client.post("/cart/add", json={"membership_code": member.code, "jadwal_id": jadwal.id, "row": "C", "col": 2})

    res = client.get(f"/cart/{member.code}")
    assert res.status_code == 200
    body = res.json()
    # expecting items list and total_price
    assert "items" in body
    assert isinstance(body["items"], list)
    assert body["total_price"] > 0
    assert len(body["items"]) == 2


def test_remove_cart_item_and_not_found(setup_db):
    db = TestingSessionLocal()
    movie, studio, jadwal, member = setup_db["movie"], setup_db["studio"], setup_db["jadwal"], setup_db["member"]

    # add a cart item
    r = client.post("/cart/add", json={"membership_code": member.code, "jadwal_id": jadwal.id, "row": "D", "col": 1})
    assert r.status_code == 200

    # get cart to find cart_id
    res = client.get(f"/cart/{member.code}")
    cart_items = res.json()["items"]
    assert len(cart_items) >= 1
    cart_id = cart_items[0]["cart_id"]

    # delete
    del_res = client.delete(f"/cart/remove/{cart_id}")
    assert del_res.status_code == 200
    assert del_res.json()["message"] in ("Item dihapus dari keranjang", "Item cart berhasil dihapus")

    # delete again -> not found
    del2 = client.delete(f"/cart/remove/{99999}")
    assert del2.status_code == 404


def test_checkout_success_non_cash_and_get_order(setup_db):
    movie, studio, jadwal, member = setup_db["movie"], setup_db["studio"], setup_db["jadwal"], setup_db["member"]

    # add two seats
    client.post("/cart/add", json={"membership_code": member.code, "jadwal_id": jadwal.id, "row": "E", "col": 1})
    client.post("/cart/add", json={"membership_code": member.code, "jadwal_id": jadwal.id, "row": "E", "col": 2})

    payload = {
        "membership_code": member.code,
        "payment_method": "QRIS"
    }
    res = client.post("/checkout", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "order_code" in data
    assert data["total_seat"] == 2
    assert data["status"] == "SUCCESS"

    # check that cart is now empty
    c_after = client.get(f"/cart/{member.code}").json()
    assert c_after["items"] == [] or c_after.get("total_price", 0) == 0

    # get order detail
    order_code = data["order_code"]
    get_order = client.get(f"/order/{order_code}")
    assert get_order.status_code == 200
    od = get_order.json()
    assert od["order_code"] == order_code
    assert od["status"].startswith("Pesanan")


def test_checkout_cash_insufficient(setup_db):
    movie, studio, jadwal, member = setup_db["movie"], setup_db["studio"], setup_db["jadwal"], setup_db["member"]

    # add one seat
    client.post("/cart/add", json={"membership_code": member.code, "jadwal_id": jadwal.id, "row": "F", "col": 1})

    # payload with cash less than final_price
    payload = {
        "membership_code": member.code,
        "payment_method": "CASH",
        "cash_amount": 100  # surely insufficient
    }
    res = client.post("/checkout", json=payload)
    assert res.status_code == 400
    assert res.json()["detail"] == "Uang tunai kurang"
