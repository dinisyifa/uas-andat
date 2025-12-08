import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from datetime import date, time, datetime, timedelta
import json

# Import komponen aplikasi utama
from app.main import app
from app.database import get_db

# Import model SQLAlchemy
from app.models import Movie, Jadwal, Studio, StudioSeat, Order, OrderSeat, Cart, Membership 

# ======================================================
# 1. SETUP DATABASE
# ======================================================
DATABASE_URL = "sqlite:///./app.db" 

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

# ======================================================
# 2. FIXTURE CLEAR TABLE
# ======================================================
@pytest.fixture(autouse=True)
def clear_db():
    """Membersihkan semua tabel yang relevan sebelum setiap test."""
    db = TestingSessionLocal()
    # Hapus OrderSeat, Cart, dan Order yang paling atas
    db.query(OrderSeat).delete()
    db.query(Order).delete()
    db.query(Cart).delete()
    db.query(StudioSeat).delete()
    db.query(Jadwal).delete()
    db.query(Movie).delete()
    db.query(Studio).delete() 
    db.query(Membership).delete() # Membersihkan Member agar UNIQUE constraint tidak terlanggar
    db.commit()
    db.close()


# ======================================================
# 3. HELPER FUNCTIONS UNTUK SETUP DATA
# ======================================================

def generate_id(model):
    """Generate ID unik berbasis ID terakhir."""
    db = TestingSessionLocal()
    last = db.query(model).order_by(model.id.desc()).first()
    next_id = (last.id + 1) if last else 1
    db.close()
    return next_id

def insert_movie(db: Session, title: str, code: str, price=50000):
    movie = Movie(
        id=generate_id(Movie), 
        code=code, title=title, durasi=120, price=price, 
        genre="Action", rating="R", director="Dir A"
    )
    db.add(movie)
    db.commit()
    db.refresh(movie)
    return movie

def insert_studio(db: Session, nama: str, rows: int, cols: int):
    studio = Studio(id=generate_id(Studio), code=f"STU{generate_id(Studio)}", nama=nama, rows=rows, cols=cols)
    db.add(studio)
    db.commit()
    db.refresh(studio)
    # Insert StudioSeat (opsional, tergantung apakah FK Cart/OrderSeat ke StudioSeat)
    return studio

def insert_jadwal(db: Session, movie: Movie, studio: Studio, tanggal: date, jam: time):
    jadwal = Jadwal(
        id=generate_id(Jadwal), code=f"JAD{generate_id(Jadwal)}", 
        movie_id=movie.id, studio_id=studio.id, 
        tanggal=tanggal, jam=jam
    )
    # Jadwal model harus punya relasi 'movie' dan 'studio' untuk diakses di router
    jadwal.movie = movie
    jadwal.studio = studio
    db.add(jadwal)
    db.commit()
    db.refresh(jadwal)
    return jadwal

def insert_member(db: Session, code: str, nama:str):
    member = Membership(id=generate_id(Membership), code=code, nama=nama)
    db.add(member)
    db.commit()
    db.refresh(member)
    return member

def insert_cart_item(db: Session, member_code: str, jadwal: Jadwal, row: str, col: int):
    cart_item = Cart(
        id=generate_id(Cart),
        membership_code=member_code,
        jadwal_id=jadwal.id,
        row=row,
        col=col,
        price=jadwal.movie.price # Harga dari Movie
    )
    db.add(cart_item)
    db.commit()
    db.refresh(cart_item)
    return cart_item

# ======================================================
# 4. TEST ENDPOINT: POST /cart/add
# ======================================================
def test_add_to_cart_success():
    db = TestingSessionLocal()
    movie = insert_movie(db, "Test Film", "MOV001", price=45000)
    studio = insert_studio(db, "Studio A", 5, 5)
    jadwal = insert_jadwal(db, movie, studio, date(2025, 12, 1), time(19, 0))
    member = insert_member(db, "MEM001", "User Test")

    payload = {
        "membership_code": "MEM001",
        "jadwal_id": jadwal.id,
        "row": "B",
        "col": 3
    }

    res = client.post("/cart/add", json=payload)
    assert res.status_code == 200
    assert "Berhasil masuk keranjang" in res.json()["message"]
    
    # Cek di database
    cart_db = db.query(Cart).filter_by(row="B", col=3).first()
    assert cart_db is not None
    assert cart_db.price == 45000


def test_add_to_cart_jadwal_not_found():
    db = TestingSessionLocal()
    insert_member(db, "MEM001", "User Test")

    payload = {
        "membership_code": "MEM001",
        "jadwal_id": 999, # ID non-existent
        "row": "B",
        "col": 3
    }
    res = client.post("/cart/add", json=payload)
    assert res.status_code == 404
    assert res.json()["detail"] == "Jadwal tidak ditemukan"

def test_add_to_cart_member_not_found():
    db = TestingSessionLocal()
    movie = insert_movie(db, "Test Film", "MOV001", price=45000)
    studio = insert_studio(db, "Studio A", 5, 5)
    jadwal = insert_jadwal(db, movie, studio, date(2025, 12, 1), time(19, 0))

    payload = {
        "membership_code": "MEMXXX", # Member non-existent
        "jadwal_id": jadwal.id,
        "row": "B",
        "col": 3
    }
    res = client.post("/cart/add", json=payload)
    assert res.status_code == 404
    assert res.json()["detail"] == "Member tidak ditemukan"


def test_add_to_cart_already_sold():
    db = TestingSessionLocal()
    movie = insert_movie(db, "Test Film", "MOV001", price=45000)
    studio = insert_studio(db, "Studio A", 5, 5)
    jadwal = insert_jadwal(db, movie, studio, date(2025, 12, 1), time(19, 0))
    member = insert_member(db, "MEM001", "User Test")
    
    # Buat OrderSeat (sudah terjual)
    order = Order(id=generate_id(Order), code="ORDTEST", membership_id=member.id, jadwal_id=jadwal.id, seat_count=1, final_price=45000, transaction_date=date.today())
    db.add(order)
    db.flush()
    db.add(OrderSeat(order_id=order.id, jadwal_id=jadwal.id, studio_id=studio.id, row="A", col=1))
    db.commit()

    payload = {
        "membership_code": "MEM001",
        "jadwal_id": jadwal.id,
        "row": "A",
        "col": 1 # Kursi A-1 sudah terjual
    }
    res = client.post("/cart/add", json=payload)
    assert res.status_code == 400
    assert res.json()["detail"] == "Kursi sudah terjual"

# ======================================================
# 5. TEST ENDPOINT: GET /cart/{membership_code}
# ======================================================
def test_get_cart_success():
    db = TestingSessionLocal()
    movie = insert_movie(db, "Film Cart", "MOV002", price=60000)
    studio = insert_studio(db, "Studio B", 5, 5)
    jadwal = insert_jadwal(db, movie, studio, date(2025, 12, 2), time(17, 0))
    member = insert_member(db, "MEM002", "Cart User")
    
    # Item 1
    insert_cart_item(db, "MEM002", jadwal, "A", 5)
    # Item 2
    insert_cart_item(db, "MEM002", jadwal, "B", 1)
    
    # Cart user lain (harus diabaikan)
    insert_member(db, "MEM003", "Other User")
    insert_cart_item(db, "MEM003", jadwal, "C", 2)
    
    res = client.get("/cart/MEM002")
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) == 2
    assert data["total_price"] == 120000 # 60000 + 60000
    assert data["items"][0]["movie_title"] == "Film Cart"
    assert data["items"][0]["seat"] == "A-5"
    assert data["items"][1]["seat"] == "B-1"


def test_get_cart_empty():
    insert_member(db=TestingSessionLocal(), code="MEM004", nama="empty User")
    res = client.get("/cart/MEM004")
    assert res.status_code == 200
    assert res.json()["message"] == "Keranjang kosong"
    assert res.json()["total"] == 0

# ======================================================
# 6. TEST ENDPOINT: DELETE /cart/remove/{cart_id}
# ======================================================
def test_remove_cart_item_success():
    db = TestingSessionLocal()
    movie = insert_movie(db, "Film Remove", "MOV003", price=50000)
    studio = insert_studio(db, "Studio C", 5, 5)
    jadwal = insert_jadwal(db, movie, studio, date(2025, 12, 3), time(15, 0))
    insert_member(db, "MEM005", "Remove User")
    
    item_to_remove = insert_cart_item(db, "MEM005", jadwal, "D", 4)
    item_to_keep = insert_cart_item(db, "MEM005", jadwal, "D", 5)
    
    res = client.delete(f"/cart/remove/{item_to_remove.id}")
    assert res.status_code == 200
    assert res.json()["message"] == "Item dihapus dari keranjang"
    
    # Cek di database
    cart_after = db.query(Cart).filter_by(membership_code="MEM005").all()
    assert len(cart_after) == 1
    assert cart_after[0].id == item_to_keep.id


def test_remove_cart_item_not_found():
    res = client.delete("/cart/remove/9999")
    assert res.status_code == 404
    assert res.json()["detail"] == "Item cart tidak ditemukan"

# ======================================================
# 7. TEST ENDPOINT: POST /checkout
# ======================================================
def test_checkout_success_qris():
    db = TestingSessionLocal()
    movie = insert_movie(db, "Film Checkout", "MOV004", price=50000)
    studio = insert_studio(db, "Studio D", 5, 5)
    jadwal = insert_jadwal(db, movie, studio, date(2025, 12, 4), time(20, 0))
    member = insert_member(db, "MEM006", "Checkout User")

    # Tambahkan 3 item ke cart
    insert_cart_item(db, "MEM006", jadwal, "E", 1)
    insert_cart_item(db, "MEM006", jadwal, "E", 2)
    insert_cart_item(db, "MEM006", jadwal, "E", 3)
    
    # Total Price = 150000. Final Price = 150000 (0% discount)
    checkout_payload = {
        "membership_code": "MEM006",
        "payment_method": "QRIS"
    }
    
    res = client.post("/checkout", json=checkout_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["total_seat"] == 3
    assert data["final_price"] == 150000
    assert data["status"] == "SUCCESS"
    assert data["order_code"].startswith("ORD-")
    
    order_code = data["order_code"]
    
    # Validasi DB: Cart kosong
    assert db.query(Cart).filter_by(membership_code="MEM006").count() == 0
    # Validasi DB: Order dibuat
    order_db = db.query(Order).filter_by(code=order_code).first()
    assert order_db is not None
    assert order_db.seat_count == 3
    assert order_db.final_price == 150000
    # Validasi DB: OrderSeat dibuat
    assert db.query(OrderSeat).filter_by(order_id=order_db.id).count() == 3

def test_checkout_success_bulk_discount():
    db = TestingSessionLocal()
    movie = insert_movie(db, "Film Promo", "MOV005", price=50000)
    studio = insert_studio(db, "Studio E", 5, 5)
    jadwal = insert_jadwal(db, movie, studio, date(2025, 12, 5), time(10, 0))
    insert_member(db, "MEM007", "Promo User")

    # Tambahkan 5 item ke cart (Trigger 20% discount)
    for i in range(1, 6):
        insert_cart_item(db, "MEM007", jadwal, "F", i)
    
    # Total Price = 5 * 50000 = 250000. Discount 20% = 50000. Final Price = 200000
    checkout_payload = {
        "membership_code": "MEM007",
        "payment_method": "Debit"
    }
    
    res = client.post("/checkout", json=checkout_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["total_seat"] == 5
    assert data["final_price"] == 200000
    
def test_checkout_success_cash_with_change():
    db = TestingSessionLocal()
    movie = insert_movie(db, "Film Cash", "MOV006", price=50000)
    studio = insert_studio(db, "Studio F", 5, 5)
    jadwal = insert_jadwal(db, movie, studio, date(2025, 12, 6), time(13, 0))
    insert_member(db, "MEM008", "Cash User")

    insert_cart_item(db, "MEM008", jadwal, "G", 1)
    
    # Final Price = 50000
    checkout_payload = {
        "membership_code": "MEM008",
        "payment_method": "Cash",
        "cash_amount": 100000 # Bayar 100.000
    }
    
    res = client.post("/checkout", json=checkout_payload)
    assert res.status_code == 200
    
    order_db = db.query(Order).filter_by(membership_code="MEM008").first()
    assert order_db.final_price == 50000
    assert order_db.cash == 100000
    assert order_db.change == 50000 # Kembalian 50.000

def test_checkout_fail_cart_empty():
    insert_member(db=TestingSessionLocal(), code="MEM009", nama= "empty User")
    checkout_payload = {
        "membership_code": "MEM009",
        "payment_method": "QRIS"
    }
    res = client.post("/checkout", json=checkout_payload)
    assert res.status_code == 400
    assert res.json()["detail"] == "Keranjang kosong"

def test_checkout_fail_seat_taken_last_minute():
    db = TestingSessionLocal()
    movie = insert_movie(db, "Film Taken", "MOV007", price=50000)
    studio = insert_studio(db, "Studio G", 5, 5)
    jadwal = insert_jadwal(db, movie, studio, date(2025, 12, 7), time(16, 0))
    member_A = insert_member(db, "MEM100", "User A")
    member_B = insert_member(db, "MEM101", "User B")

    # User B: Tambah ke cart
    insert_cart_item(db, "MEM101", jadwal, "H", 1)
    
    # SEAT H-1 TERJUAL OLEH USER A (diluar proses checkout user B)
    order_A = Order(id=generate_id(Order), code="ORDTESTA", membership_id=member_A.id, jadwal_id=jadwal.id, seat_count=1, final_price=50000, transaction_date=date.today())
    db.add(order_A)
    db.flush()
    db.add(OrderSeat(order_id=order_A.id, jadwal_id=jadwal.id, studio_id=studio.id, row="H", col=1))
    db.commit() # Kursi H-1 sudah terjual!

    # User B: Checkout (Gagal di validasi Last Minute Check)
    checkout_payload = {
        "membership_code": "MEM101",
        "payment_method": "QRIS"
    }
    res = client.post("/checkout", json=checkout_payload)
    assert res.status_code == 409
    assert "Kursi H-1 baru saja dibeli orang lain." in res.json()["detail"]

def test_checkout_fail_cash_amount_low():
    db = TestingSessionLocal()
    movie = insert_movie(db, "Film Low Cash", "MOV008", price=60000)
    studio = insert_studio(db, "Studio H", 5, 5)
    jadwal = insert_jadwal(db, movie, studio, date(2025, 12, 8), time(21, 0))
    insert_member(db, "MEM102", "Low Cash User")

    insert_cart_item(db, "MEM102", jadwal, "I", 1)
    
    # Final Price = 60000
    checkout_payload = {
        "membership_code": "MEM102",
        "payment_method": "Cash",
        "cash_amount": 50000 # Uang kurang
    }
    
    res = client.post("/checkout", json=checkout_payload)
    assert res.status_code == 400
    assert res.json()["detail"] == "Uang tunai kurang"

# ======================================================
# 8. TEST ENDPOINT: GET /order/{order_code}
# ======================================================
def test_get_order_success():
    db = TestingSessionLocal()
    member = insert_member(db, "MEM103", "Order Detail User")
    
    # Buat order manual
    order = Order(
        id=generate_id(Order), 
        code="ORD777", 
        membership_id=member.id, 
        jadwal_id=1, 
        seat_count=2, 
        final_price=100000, 
        transaction_date=date.today()
    )
    db.add(order)
    db.commit()
    
    res = client.get("/order/ORD777")
    assert res.status_code == 200
    data = res.json()
    assert data["order_code"] == "ORD777"
    assert data["total_seat"] == 2
    assert data["final_price"] == 100000
    assert data["status"].startswith("Pesanan `ORD777` berhasil diproses")


def test_get_order_not_found():
    res = client.get("/order/ORD999")
    assert res.status_code == 404
    assert res.json()["detail"] == "Order tidak ditemukan"