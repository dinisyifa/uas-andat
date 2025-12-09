import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import datetime

# --- IMPORT DARI APLIKASI ---
from app.main import app
from app.database import Base, get_db
from app.models import Movie, Jadwal, Order, OrderSeat, Studio, Membership

# ==============================================================================
# 1. SETUP REAL DATABASE (MYSQL)
# ==============================================================================
# Password sesuai file Nastar Keju kamu
TEST_DB = "mysql+pymysql://root:616084RL@localhost:3306/bioskop"

engine_test = create_engine(TEST_DB)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

# Reset Database (Drop & Create)
Base.metadata.drop_all(bind=engine_test)
Base.metadata.create_all(bind=engine_test)

# Override Dependency
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

# ==============================================================================
# 2. FIXTURE: SEED DATA UMUM (Untuk Film Populer, Genre, dll)
# ==============================================================================
@pytest.fixture
def seed_data():
    db = TestingSessionLocal()
    try:
        # Bersihkan tabel
        db.query(OrderSeat).delete()
        db.query(Order).delete()
        db.query(Jadwal).delete()
        db.query(Movie).delete()
        db.query(Studio).delete()
        db.commit()
    except:
        db.rollback()

    # 1. Movies
    m1 = Movie(code="M01", title="Film A", genre="Action", durasi=120, price=50000)
    m2 = Movie(code="M02", title="Film B", genre="Comedy", durasi=100, price=50000)
    db.add_all([m1, m2])
    db.commit()

    # 2. Studio (Wajib ada biar join ga error)
    st = Studio(code="S01", name="Studio 1", rows=5, cols=5)
    db.add(st)
    db.commit()

    # 3. Jadwal (Tanggal 5 Des 2024)
    tgl = datetime.date(2024, 12, 5)
    j1 = Jadwal(code="J01", movie_id=m1.id, studio_id=st.id, tanggal=tgl, jam=datetime.time(14,0))
    j2 = Jadwal(code="J02", movie_id=m2.id, studio_id=st.id, tanggal=tgl, jam=datetime.time(16,0))
    db.add_all([j1, j2])
    db.commit()

    # 4. Orders
    o1 = Order(code="O01", jadwal_id=j1.id, payment_method="QRIS", transaction_date=tgl, final_price=100000)
    o2 = Order(code="O02", jadwal_id=j2.id, payment_method="Cash", transaction_date=tgl, final_price=50000)
    db.add_all([o1, o2])
    db.commit()

    # 5. Seats (Total 3 tiket)
    s1 = OrderSeat(order_id=o1.id, jadwal_id=j1.id, studio_id=st.id, row="A", col=1)
    s2 = OrderSeat(order_id=o1.id, jadwal_id=j1.id, studio_id=st.id, row="A", col=2)
    s3 = OrderSeat(order_id=o2.id, jadwal_id=j2.id, studio_id=st.id, row="A", col=3)
    db.add_all([s1, s2, s3])
    db.commit()
    db.close()

# ==============================================================================
# 3. FIXTURE: SEED DATA TIFF (Untuk Revenue, Customer, Busiest Day)
# ==============================================================================
@pytest.fixture
def seed_data_tiff():
    db = TestingSessionLocal()
    try:
        # Bersihkan tabel
        db.query(OrderSeat).delete()
        db.query(Order).delete()
        db.query(Jadwal).delete()
        db.query(Movie).delete()
        db.query(Studio).delete()
        db.query(Membership).delete()
        db.commit()
    except:
        db.rollback()

    # Data Khusus Analisis Tiff (1 Des 2024)
    m1 = Movie(code="MV1", title="Action Movie", genre="Action", durasi=120, price=50000)
    m2 = Movie(code="MV2", title="Drama Movie", genre="Drama", durasi=100, price=40000)
    db.add_all([m1, m2])
    db.commit()

    st = Studio(code="ST1", name="Studio 1", rows=5, cols=5)
    db.add(st)
    db.commit()

    mem = Membership(code="MM1", nama="Tester")
    db.add(mem)
    db.commit()

    tgl = datetime.date(2024, 12, 1)
    j1 = Jadwal(code="JD1", movie_id=m1.id, studio_id=st.id, tanggal=tgl, jam=datetime.time(10,0))
    j2 = Jadwal(code="JD2", movie_id=m2.id, studio_id=st.id, tanggal=tgl, jam=datetime.time(13,0))
    db.add_all([j1, j2])
    db.commit()

    # Transaksi: Action 2 tiket, Action 1 tiket, Drama 1 tiket
    # PENTING: membership_code diisi manual stringnya agar join berhasil
    o1 = Order(code="OR1", membership_id=mem.id, membership_code="MM1", jadwal_id=j1.id, payment_method="QRIS", seat_count=2, final_price=100000, transaction_date=tgl)
    o2 = Order(code="OR2", membership_id=mem.id, membership_code="MM1", jadwal_id=j1.id, payment_method="CASH", seat_count=1, final_price=50000, transaction_date=tgl)
    o3 = Order(code="OR3", membership_id=mem.id, membership_code="MM1", jadwal_id=j2.id, payment_method="QRIS", seat_count=1, final_price=40000, transaction_date=tgl)
    db.add_all([o1, o2, o3])
    db.commit()

    db.add_all([
        OrderSeat(order_id=o1.id, jadwal_id=j1.id, studio_id=st.id, row="A", col=1),
        OrderSeat(order_id=o1.id, jadwal_id=j1.id, studio_id=st.id, row="A", col=2),
        OrderSeat(order_id=o2.id, jadwal_id=j1.id, studio_id=st.id, row="A", col=3),
        OrderSeat(order_id=o3.id, jadwal_id=j2.id, studio_id=st.id, row="B", col=1)
    ])
    db.commit()
    db.close()

# ==============================================================================
# 4. TEST CASES (GROUP 1: NASTAR KEJU / UMUM)
# ==============================================================================
# URL SUDAH DIPERBAIKI menyesuaikan router 'analisis_tiff.py' kamu
# /analisis/filmpopuler?periode=...

def test_filmpopuler_daily(seed_data):
    # Dulu: /analisis/filmpopuler/daily?day=1 -> Salah (404)
    # Sekarang: /analisis/filmpopuler?periode=harian&hari=5
    response = client.get("/analisis/filmpopuler?periode=harian&hari=5")
    assert response.status_code == 200
    data = response.json()
    assert "tanggal" in data
    assert "data" in data
    assert isinstance(data["data"], list)

def test_filmpopuler_weekly(seed_data):
    # Dulu: /analisis/filmpopuler/weekly -> Salah (404)
    # Sekarang: /analisis/filmpopuler?periode=mingguan
    response = client.get("/analisis/filmpopuler?periode=mingguan")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert isinstance(data["data"], list)

def test_filmpopuler_monthly(seed_data):
    # Dulu: /analisis/filmpopuler/monthly?bulan=Desember -> Salah (404)
    # Sekarang: /analisis/filmpopuler?periode=bulanan&bulan=Desember
    response = client.get("/analisis/filmpopuler?periode=bulanan&bulan=Desember")
    assert response.status_code == 200
    data = response.json()
    assert "bulan" in data
    assert "data" in data

def test_jamtayang_daily(seed_data):
    # Dulu: /analisis/jamtayangpopuler/daily -> Salah (404)
    response = client.get("/analisis/jamtayangpopuler?periode=harian&hari=5")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data

def test_jamtayang_weekly(seed_data):
    response = client.get("/analisis/jamtayangpopuler?periode=mingguan")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data

def test_jamtayang_monthly(seed_data):
    response = client.get("/analisis/jamtayangpopuler?periode=bulanan&bulan=Desember")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data

def test_invalid_month(seed_data):
    response = client.get("/analisis/filmpopuler?periode=bulanan&bulan=xxx")
    assert response.status_code == 200
    assert "error" in response.json()

def test_metode_pembayaran(seed_data):
    response = client.get("/analisis/metodepembayaran")
    assert response.status_code == 200
    result = response.json()["data"]
    assert len(result) >= 2


# ==============================================================================
# 5. TEST CASES (GROUP 2: TIFF)
# ==============================================================================

def test_tiff_top_revenue_daily(seed_data_tiff):
    res = client.get("/analisis/top-revenue-films?period=hari")
    assert res.status_code == 200
    # Mencari hasil untuk "Tanggal 1"
    hasil = next((x for x in res.json()["hasil_analisis"] if "Tanggal 1" in x["periode"]), None)
    assert hasil is not None
    assert hasil["film_juara"] == "Action Movie"
    assert float(hasil["pendapatan"]) == 150000.0

def test_tiff_top_customers_monthly(seed_data_tiff):
    res = client.get("/analisis/top-customers?period=bulan")
    assert res.status_code == 200
    # Ambil elemen pertama dari list hasil
    bulan_des = res.json()["hasil_analisis"][0]
    
    assert bulan_des["pelanggan_juara"] == "Tester"
    assert bulan_des["jumlah_transaksi"] == 3

def test_tiff_most_busiest_day(seed_data_tiff):
    # Menggunakan MySQL asli, fungsi SQL 'dayname' akan dikenali
    res = client.get("/analisis/most-busiest-day?bulan=12&tahun=2024")
    assert res.status_code == 200
    data = res.json()
    
    assert "4 tiket" in data["kesimpulan"]["tanggal_tersibuk"]
    
    top_day = data["ranking_hari_teramai"][0]
    # Bisa 'Sunday' atau 'Minggu' tergantung locale MySQL kamu
    assert top_day["nama_hari"] in ["Sunday", "Minggu"]
    assert int(top_day["total_akumulasi_tiket"]) == 4