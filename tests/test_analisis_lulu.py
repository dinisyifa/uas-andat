import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker
import datetime

# --- IMPORT DARI FOLDER APP ---
from app.main import app
from app.database import get_db
from app.models import Base, Movie, Studio, Jadwal, Membership, Order, OrderSeat

# ==============================================================================
# 1. SETUP DATABASE TESTING (SQLITE IN-MEMORY)
# ==============================================================================
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}, 
    poolclass=StaticPool 
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

# ==============================================================================
# 2. FIXTURE & SEEDING DATA
# ==============================================================================
@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        create_analytics_seed_data(db)
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)

def create_analytics_seed_data(db):
    """
    Skenario Data untuk Test:
    - 2 Film: Action (MOV1), Drama (MOV2)
    - Tanggal Transaksi: 1 Desember 2024
    """
    # Movies
    m1 = Movie(code="MOV1", title="Action Movie", genre="Action", durasi=120, director="A", rating="PG", price=50000)
    m2 = Movie(code="MOV2", title="Drama Movie", genre="Drama", durasi=100, director="B", rating="PG", price=40000)
    db.add_all([m1, m2])
    db.flush()

    # Studio
    st = Studio(code="ST1", name="Studio 1", rows=5, cols=5)
    db.add(st)
    db.flush()

    # Tanggal Test
    test_date = datetime.date(2024, 12, 1)
    
    # --- PERBAIKAN DI SINI ---
    # Gunakan datetime.time(), BUKAN string "10:00:00"
    waktu_1 = datetime.time(10, 0, 0)
    waktu_2 = datetime.time(13, 0, 0)
    
    j1 = Jadwal(code="J1", movie_id=m1.id, studio_id=st.id, tanggal=test_date, jam=waktu_1)
    j2 = Jadwal(code="J2", movie_id=m2.id, studio_id=st.id, tanggal=test_date, jam=waktu_2)
    db.add_all([j1, j2])
    db.flush()

    # Member
    mem = Membership(code="MEM1", nama="Tester")
    db.add(mem)
    db.flush()

    # Orders
    # Order 1: QRIS, Action (2 seats)
    o1 = Order(code="ORD1", membership_id=mem.id, jadwal_id=j1.id, payment_method="QRIS", seat_count=2, final_price=100000, transaction_date=test_date)
    db.add(o1)
    db.flush()
    db.add_all([
        OrderSeat(order_id=o1.id, jadwal_id=j1.id, studio_id=st.id, row="A", col=1),
        OrderSeat(order_id=o1.id, jadwal_id=j1.id, studio_id=st.id, row="A", col=2)
    ])

    # Order 2: CASH, Action (1 seat)
    o2 = Order(code="ORD2", membership_id=mem.id, jadwal_id=j1.id, payment_method="CASH", seat_count=1, final_price=50000, transaction_date=test_date)
    db.add(o2)
    db.flush()
    db.add(OrderSeat(order_id=o2.id, jadwal_id=j1.id, studio_id=st.id, row="A", col=3))

    # Order 3: QRIS, Drama (1 seat)
    o3 = Order(code="ORD3", membership_id=mem.id, jadwal_id=j2.id, payment_method="QRIS", seat_count=1, final_price=40000, transaction_date=test_date)
    db.add(o3)
    db.flush()
    db.add(OrderSeat(order_id=o3.id, jadwal_id=j2.id, studio_id=st.id, row="B", col=1))

    db.commit()

# ==============================================================================
# 3. TEST CASES
# ==============================================================================

def test_analytics_payment_methods(db_session):
    res = client.get("/api/admin/analytics/payment-methods")
    
    assert res.status_code == 200
    data = res.json()["data"]
    
    qris = next((x for x in data if x["payment_method"] == "QRIS"), None)
    assert qris is not None
    assert qris["penggunaan"] == 2
    assert 66.0 <= float(qris["persentase"]) <= 67.0 

    cash = next((x for x in data if x["payment_method"] == "CASH"), None)
    assert cash is not None
    assert cash["penggunaan"] == 1
    assert 33.0 <= float(cash["persentase"]) <= 34.0


def test_analytics_genre_popularity_global(db_session):
    res = client.get("/api/admin/analytics/genre-popularity")
    
    assert res.status_code == 200
    data = res.json()["data"]
    
    action = next((i for i in data if i["genre"] == "Action"), None)
    assert action is not None
    assert action["total_tiket_terjual"] == 3
    assert float(action["persentase_minat"]) == 75.0
    
    drama = next((i for i in data if i["genre"] == "Drama"), None)
    assert drama is not None
    assert drama["total_tiket_terjual"] == 1
    assert float(drama["persentase_minat"]) == 25.0


def test_analytics_genre_popularity_monthly(db_session):
    res = client.get("/api/admin/analytics/genre-popularity/monthly?bulan=desember")
    
    assert res.status_code == 200
    data = res.json()
    
    assert data["bulan"] == "desember"
    assert data["total_tiket_terjual"] == 4 
    
    genres = data["data"]
    action = next((i for i in genres if i["genre"] == "Action"), None)
    assert action["total_tiket"] == 3
    assert float(action["persentase_minat"]) == 75.0

def test_analytics_genre_popularity_weekly(db_session):
    """
    Test API Genre Weekly (Desember 2024).
    Data seeding kita diset tanggal 1 Des 2024 -> Masuk Minggu ke-1 (1-7 Des).
    """
    res = client.get("/api/admin/analytics/genre-popularity/weekly")
    
    assert res.status_code == 200
    json_resp = res.json()
    
    hasil = json_resp["hasil"]
    # Minggu ke-1 (index 0) harusnya ada data karena tgl transaksi = 1 Des
    minggu_1 = hasil[0]
    
    # Minggu 1 harusnya ada 4 tiket (2 Action + 1 Action + 1 Drama)
    assert minggu_1["minggu_ke"] == 1
    assert minggu_1["total_tiket_terjual"] == 4 
    
    data_m1 = minggu_1["data"]
    # Cek Action di Minggu 1
    action = next((x for x in data_m1 if x["genre"] == "Action"), None)
    assert action["total_tiket"] == 3
    assert float(action["persentase_minat"]) == 75.0