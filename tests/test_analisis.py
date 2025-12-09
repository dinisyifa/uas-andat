import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import datetime

# --- IMPORT DARI FOLDER APP ---
from app.main import app
from app.database import get_db
from app.models import Base, Movie, Studio, Jadwal, Membership, Order, OrderSeat

# ==============================================================================
# 1. SETUP REAL DATABASE (MYSQL)
# ==============================================================================
# Menggunakan password dari file models.py kamu (616084RL)
# Pastikan XAMPP/MySQL kamu sudah nyala sebelum menjalankan test ini
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:%40Keju1234@localhost:3306/bioskop"

engine_test = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

# Override dependency get_db agar aplikasi menggunakan koneksi test ini
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

# ==============================================================================
# 2. FIXTURE: SEED DATA (MEMBERSIHKAN & MENGISI DB ASLI)
# ==============================================================================
@pytest.fixture
def seed_data():
    """
    Fixture ini akan:
    1. Menghapus data lama (Reset) agar test bersih.
    2. Mengisi data baru khusus untuk skenario Analisis.
    """
    db = TestingSessionLocal()

    # --- A. BERSIHKAN TABEL (Urutan delete penting karena Foreign Key) ---
    try:
        db.query(OrderSeat).delete()
        db.query(Order).delete()
        db.query(Jadwal).delete()
        db.query(Movie).delete()
        db.query(Studio).delete()
        db.query(Membership).delete()
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error cleaning DB: {e}")

    # --- B. INSERT DATA BARU ---
    
    # 1. Movies
    m1 = Movie(code="MOV001", title="Action Movie", genre="Action", durasi=120, director="A", rating="PG", price=50000)
    m2 = Movie(code="MOV002", title="Drama Movie", genre="Drama", durasi=100, director="B", rating="PG", price=40000)
    db.add_all([m1, m2])
    db.commit() # Commit dulu biar dapet ID

    # 2. Studio
    st = Studio(code="ST001", name="Studio 1", rows=5, cols=5)
    db.add(st)
    db.commit()

    # 3. Membership
    mem = Membership(code="MEM001", nama="Tester")
    db.add(mem)
    db.commit()

    # 4. Jadwal (Tanggal 1 Desember 2024 - Hari Minggu)
    test_date = datetime.date(2024, 12, 1)
    waktu_1 = datetime.time(10, 0, 0) # Action
    waktu_2 = datetime.time(13, 0, 0) # Drama
    
    j1 = Jadwal(code="JAD001", movie_id=m1.id, movie_code=m1.code, studio_id=st.id, studio_code=st.code, tanggal=test_date, jam=waktu_1)
    j2 = Jadwal(code="JAD002", movie_id=m2.id, movie_code=m2.code, studio_id=st.id, studio_code=st.code, tanggal=test_date, jam=waktu_2)
    db.add_all([j1, j2])
    db.commit()

    # 5. Orders
    # Order 1: Action (2 seats) -> 100k
    o1 = Order(
        code="ORD001", membership_id=mem.id, membership_code=mem.code,
        jadwal_id=j1.id, payment_method="QRIS", seat_count=2,
        final_price=100000, transaction_date=test_date, 
        hari="Minggu" # Isi manual jika perlu, atau biarkan null tergantung logika app
    )
    db.add(o1)
    db.commit()
    
    # Seats Order 1
    db.add_all([
        OrderSeat(order_id=o1.id, jadwal_id=j1.id, studio_id=st.id, row="A", col=1),
        OrderSeat(order_id=o1.id, jadwal_id=j1.id, studio_id=st.id, row="A", col=2)
    ])

    # Order 2: Action (1 seat) -> 50k
    o2 = Order(
        code="ORD002", membership_id=mem.id, membership_code=mem.code,
        jadwal_id=j1.id, payment_method="CASH", seat_count=1,
        final_price=50000, transaction_date=test_date,
        hari="Minggu"
    )
    db.add(o2)
    db.commit()
    
    # Seats Order 2
    db.add(OrderSeat(order_id=o2.id, jadwal_id=j1.id, studio_id=st.id, row="A", col=3))

    # Order 3: Drama (1 seat) -> 40k
    o3 = Order(
        code="ORD003", membership_id=mem.id, membership_code=mem.code,
        jadwal_id=j2.id, payment_method="QRIS", seat_count=1,
        final_price=40000, transaction_date=test_date,
        hari="Minggu"
    )
    db.add(o3)
    db.commit()

    # Seats Order 3
    db.add(OrderSeat(order_id=o3.id, jadwal_id=j2.id, studio_id=st.id, row="B", col=1))
    
    db.commit()
    db.close()

# ==============================================================================
# 3. TEST CASES (MENGGUNAKAN DATA REAL DI MYSQL)
# ==============================================================================

# --- A. Test Top Revenue Films (Pendapatan Terbanyak) ---
def test_top_revenue_daily(seed_data):
    # Action: 150k, Drama: 40k. Tanggal 1 Des.
    res = client.get("/analisis/top-revenue-films?period=hari")
    
    assert res.status_code == 404
    data = res.json()
    
    # Cari data tanggal 1
    hasil = next((x for x in data["hasil_analisis"] if "Tanggal 1" in x["periode"]), None)
    
    assert hasil is not None
    assert hasil["film_juara"] == "Action Movie"
    assert float(hasil["pendapatan"]) == 150000.0


# --- B. Test Top Customers (Pelanggan Ter-Rajin) ---
def test_top_customers_monthly(seed_data):
    # Member "Tester" belanja 3 kali di bulan Desember
    res = client.get("/analisis/top-customers?period=bulan")
    
    assert res.status_code == 404
    data = res.json()["hasil_analisis"]
    
    bulan_des = data[0]
    assert "Desember" in bulan_des["periode"]
    assert bulan_des["pelanggan_juara"] == "Tester"
    assert bulan_des["code_pelanggan"] == "MEM001"
    assert bulan_des["jumlah_transaksi"] == 3


# --- C. Test Most Busiest Day (Hari Teramai) ---
def test_most_busiest_day(seed_data):
    # KARENA SUDAH PAKE MYSQL ASLI, KITA GAK PERLU TRY-EXCEPT UNTUK DAYNAME!
    # MySQL asli punya fungsi dayname().
    
    res = client.get("/analisis/most-busiest-day?bulan=12&tahun=2024")
    
    assert res.status_code == 404
    data = res.json()
    
    # 1. Cek Kesimpulan
    assert "Most Busiest Time Analysis" in data["kesimpulan"]["judul"]
    assert "4 tiket" in data["kesimpulan"]["tanggal_tersibuk"]
    
    # 2. Cek Ranking Hari
    # Tanggal 1 Des 2024 adalah hari MINGGU (Sunday)
    top_day = data["ranking_hari_teramai"][0]
    
    # MySQL output dayname tergantung setting bahasa, bisa "Sunday" atau "Minggu"
    assert top_day["nama_hari"] in ["Sunday", "Minggu"] 
    assert int(top_day["total_akumulasi_tiket"]) == 4

# --- D. Test Genre Populer ---
@pytest.mark.parametrize("periode", ["harian", "mingguan", "bulanan"])
def test_genre_populer(seed_data, periode):
    res = client.get(f"/analisis/genre-populer?periode={periode}")
    
    assert res.status_code == 404
    data = res.json()
    
    assert isinstance(data, list)
    assert len(data) > 0

    top = data[0]
    assert top["genre"] == "Action"
    assert int(top["jumlah"]) == 3


# --- E. Test Film Populer ---
@pytest.mark.parametrize("periode", ["harian", "mingguan", "bulanan"])
def test_film_populer(seed_data, periode):
    res = client.get(f"/analisis/film-populer?periode={periode}")
    
    assert res.status_code == 404
    data = res.json()

    assert isinstance(data, list)
    assert len(data) > 0

    top = data[0]
    assert top["title"] == "Action Movie"
    assert int(top["jumlah"]) == 3


# --- F. Test Jam Tayang Populer ---
@pytest.mark.parametrize("periode", ["harian", "mingguan", "bulanan"])
def test_jam_tayang_populer(seed_data, periode):
    res = client.get(f"/analisis/jam-terpopuler?periode={periode}")
    
    assert res.status_code == 404
    data = res.json()

    assert isinstance(data, list)
    assert len(data) > 0

    top = data[0]
    # 10:00 yang paling ramai
    assert top["jam"] == "10:00:00"
    assert int(top["jumlah"]) == 3
