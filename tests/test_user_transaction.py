import pytest
from fastapi.testclient import TestClient
from datetime import date, time
from app.main import app
from app.database import Base, get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Membership, Movie, Studio, Jadwal, StudioSeat, Cart, OrderSeat


# =============================
#  SETUP DATABASE TEST
# =============================

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_cart.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine
)

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


# =============================
#  FIXTURES DATA AWAL
# =============================
@pytest.fixture(scope="module", autouse=True)
def seed_data():
    db = TestingSessionLocal()

    member = Membership(code="MEM001", nama="Tester")
    movie = Movie(code="MOV001", title="Avatar", genre="Action",
                  durasi=120, price=50000, rating="SU", director="James")
    studio = Studio(name="Studio 1")

    db.add_all([member, movie, studio])
    db.commit()
    db.refresh(member)
    db.refresh(movie)
    db.refresh(studio)

    jadwal = Jadwal(
        code="JAD001",
        movie_id=movie.id,
        studio_id=studio.id,
        tanggal=date(2024, 12, 15),
        jam=time(19, 0)
    )
    db.add(jadwal)
    db.commit()
    db.refresh(jadwal)

    # buat kursi mock 4 seat
    seats = [
        StudioSeat(studio_id=studio.id, row="A", col=i)
        for i in range(1, 5)
    ]
    db.add_all(seats)
    db.commit()
    db.close()
    return True


# =============================
#  1️⃣ TEST ADD TO CART
# =============================
def test_add_to_cart_success():
    payload = {
        "membership_code": "MEM001",
        "jadwal_code": "JAD001",
        "row": "A",
        "col": 1
    }
    res = client.post("/cart/add", json=payload)
    assert res.status_code == 200
    assert res.json()["message"] == "Tiket berhasil ditambahkan"


# =============================
#  2️⃣ TEST GET CART MEMBERSHIP
# =============================
def test_get_cart_items():
    res = client.get("/cart/MEM001")
    data = res.json()

    assert res.status_code == 200
    assert data["final_price"] == 50000
    assert len(data["items"]) == 1
    assert data["items"][0]["movie_title"] == "Avatar"


# =============================
#  3️⃣ TEST CHECKOUT
# =============================
def test_checkout_cart_cash():
    payload = {
        "membership_code": "MEM001",
        "payment_method": "CASH",
        "cash_amount": 100000
    }
    res = client.post("/checkout", json=payload)

    assert res.status_code == 200
    body = res.json()

    assert body["total_seat"] == 1
    assert body["final_price"] == 50000
    assert body["change"] == 50000
    assert body["status"] == "PAID"

    global created_order_code
    created_order_code = body["order_code"]


# =============================
#  4️⃣ TEST CART KOSONG SETELAH CHECKOUT
# =============================
def test_cart_is_empty_after_checkout():
    res = client.get("/cart/MEM001")
    assert res.json()["total"] == 0


# =============================
#  5️⃣ ORDER SEAT BENAR2 PINDAH
# =============================
def test_order_seat_move_db():
    db = TestingSessionLocal()
    seats = db.query(OrderSeat).all()
    assert len(seats) == 1
    db.close()


# =============================
#  6️⃣ GET ORDER DETAIL BERHASIL
# =============================
def test_get_order_detail():
    res = client.get(f"/order/{OrderResponse}")
    assert res.status_code == 200
    assert res.json()["order_code"] == order_code
