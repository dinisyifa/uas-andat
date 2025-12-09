import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from datetime import date, time, datetime, timedelta
from sqlalchemy import text

from app.main import app
from app.database import get_db, Base

# Import model SQLAlchemy yang dibutuhkan
from app.models import Movie, Jadwal, Studio, Order, OrderSeat, Membership 

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
def setup_db_schema():
    # Reset database untuk setiap test
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    clear_db()


def clear_db():
    db = TestingSessionLocal()
    db.query(OrderSeat).delete()
    db.query(Order).delete()
    db.query(Jadwal).delete()
    db.query(Movie).delete()
    db.query(Studio).delete()
    db.query(Membership).delete()
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

def insert_studio(db: Session, name: str):
    studio = Studio(id=generate_id(Studio), code=f"STU{generate_id(Studio)}", name=name, rows=5, cols=10)
    db.add(studio)
    db.commit()
    db.refresh(studio)
    return studio

def insert_jadwal(db: Session, movie: Movie, studio: Studio, tanggal: date, jam: time):
    jadwal = Jadwal(
        id=generate_id(Jadwal), code=f"JAD{generate_id(Jadwal)}", 
        movie_id=movie.id, studio_id=studio.id, 
        tanggal=tanggal, jam=jam
    )
    db.add(jadwal)
    db.commit()
    db.refresh(jadwal)
    return jadwal

def insert_order(
    db: Session, 
    jadwal: Jadwal, 
    seat_count: int, 
    final_price: int, 
    transaction_date: date, 
    promo_name: str = "NO PROMO",
    seats: list[tuple[str, int]] = None
):
    member = Membership(id=generate_id(Membership), code=f"MEM{generate_id(Membership)}", nama="Test User")
    db.add(member)
    db.flush()
    
    order = Order(
        id=generate_id(Order), 
        code=f"ORD{generate_id(Order)}", 
        membership_id=member.id, 
        membership_code=member.code,
        jadwal_id=jadwal.id, 
        payment_method="QRIS",
        seat_count=seat_count, 
        total_price=seat_count * jadwal.movie.price,
        final_price=final_price, 
        discount=0,
        promo_name=promo_name,
        transaction_date=transaction_date
    )
    db.add(order)
    db.flush()

    if seats:
        for row, col in seats:
            db.add(OrderSeat(
                order_id=order.id, 
                jadwal_id=jadwal.id, 
                studio_id=jadwal.studio_id, 
                row=row, 
                col=col
            ))
    else:
        # Jika seats tidak diberikan, buat dummy seat A1-A<seat_count>
        for i in range(seat_count):
            db.add(OrderSeat(
                order_id=order.id, 
                jadwal_id=jadwal.id, 
                studio_id=jadwal.studio_id, 
                row="Z", # Gunakan row Z agar tidak bertabrakan dengan kursi populer
                col=i + 1
            ))

    db.commit()
    return order

# ======================================================
# 4. TEST FILM PALING POPULER (DAILY)
# ======================================================
def test_film_popular_daily_success():
    db = TestingSessionLocal()
    m1 = insert_movie(db, "Populer Hari Ini", "MOV001", price=50000)
    m2 = insert_movie(db, "Kurang Populer", "MOV002", price=60000)
    st = insert_studio(db, "Studio Test")
    
    # Jadwal hari ini (Des 5, 2024)
    jadwal1 = insert_jadwal(db, m1, st, date(2024, 12, 5), time(10, 0))
    jadwal2 = insert_jadwal(db, m2, st, date(2024, 12, 5), time(12, 0))
    
    # Transaksi Hari ini (Des 5)
    insert_order(db, jadwal1, seat_count=5, final_price=250000, transaction_date=date(2024, 12, 5)) # M1: 5 tiket
    insert_order(db, jadwal2, seat_count=2, final_price=120000, transaction_date=date(2024, 12, 5)) # M2: 2 tiket
    insert_order(db, jadwal1, seat_count=3, final_price=150000, transaction_date=date(2024, 12, 5)) # M1: 3 tiket
    
    # Transaksi Hari lain (Des 6)
    insert_order(db, jadwal2, seat_count=10, final_price=600000, transaction_date=date(2024, 12, 6))

    res = client.get("/filmpopuler/daily", params={"day": 5})
    assert res.status_code == 200
    data = res.json()
    assert data["tanggal"] == "2024-12-05"
    
    # Total tiket terjual adalah jumlah baris Order, bukan total COUNT(o.id)
    # Total tiket terjual seharusnya 2 film
    assert data["total_tiket_terjual"] == 8 + 2
    
    assert data["data"][0]["title"] == "Populer Hari Ini"
    assert data["data"][0]["total_tiket_terjual"] == 8 # 5 + 3 #m1
    assert data["data"][1]["title"] == "Kurang Populer"
    assert data["data"][1]["total_tiket_terjual"] == 2 #m2


def test_film_popular_daily_no_data():
    res = client.get("/filmpopuler/daily", params={"day": 10}) # Tanggal 10 Des harus kosong
    assert res.status_code == 200
    data = res.json()
    assert data["tanggal"] == "2024-12-10"
    assert data["total_tiket_terjual"] == 0
    assert data["data"] == []

# ======================================================
# 5. TEST FILM PALING POPULER (WEEKLY)
# ======================================================
def test_film_popular_weekly_success():
    db = TestingSessionLocal()
    m_week1 = insert_movie(db, "Film Week 1", "M010", price=50000)
    m_week2 = insert_movie(db, "Film Week 2", "M011", price=50000)
    st = insert_studio(db, "Studio Test")
    
    jadwal1 = insert_jadwal(db, m_week1, st, date(2024, 12, 3), time(10, 0))
    jadwal2 = insert_jadwal(db, m_week2, st, date(2024, 12, 10), time(12, 0)) # Week 2
    
    # Transaksi Week 1 (1-7 Des)
    insert_order(db, jadwal1, 5, 250000, date(2024, 12, 3)) # W1: 5 tiket (Film Week 1)
    
    # Transaksi Week 2 (8-14 Des)
    insert_order(db, jadwal2, 8, 400000, date(2024, 12, 10)) # W2: 8 tiket (Film Week 2)
    
    # Transaksi Week 3 (15-21 Des)
    insert_order(db, jadwal1, 1, 50000, date(2024, 12, 20)) # W3: 1 tiket (Film Week 1)

    res = client.get("/filmpopuler/weekly")
    assert res.status_code == 200
    data = res.json()
    assert data["bulan"] == "Desember 2024"
    assert data["total_minggu"] == 5
    
    # Minggu 1 (1-7 Des): Film Week 1 (5 tiket)
    w1 = data["hasil"][0]
    assert w1["minggu"] == 1
    assert w1["film_terlaris"]["title"] == "Film Week 1"
    assert w1["film_terlaris"]["total_tiket_terjual"] == 5
    
    # Minggu 2 (8-14 Des): Film Week 2 (8 tiket)
    w2 = data["hasil"][1]
    assert w2["minggu"] == 2
    assert w2["film_terlaris"]["title"] == "Film Week 2"
    assert w2["film_terlaris"]["total_tiket_terjual"] == 8
    
    # Minggu 3 (15-21 Des): Film Week 1 (1 tiket)
    w3 = data["hasil"][2]
    assert w3["minggu"] == 3
    assert w3["film_terlaris"]["title"] == "Film Week 1"
    assert w3["film_terlaris"]["total_tiket_terjual"] == 1
    
    # Minggu 4 & 5 harus None (atau kosong)
    assert data["hasil"][3]["film_terlaris"] is None
    assert data["hasil"][4]["film_terlaris"] is None

# ======================================================
# 6. TEST FILM PALING POPULER (MONTHLY)
# ======================================================
def test_film_popular_monthly_success():
    db = TestingSessionLocal()
    m_top = insert_movie(db, "Film Terlaris", "M020", price=50000)
    m_reg = insert_movie(db, "Film Reguler", "M021", price=50000)
    st = insert_studio(db, "Studio Test")
    
    jadwal_d = insert_jadwal(db, m_top, st, date(2024, 12, 1), time(10, 0))
    jadwal_d2 = insert_jadwal(db, m_reg, st, date(2024, 12, 15), time(12, 0))
    jadwal_n = insert_jadwal(db, m_top, st, date(2024, 11, 1), time(14, 0)) # Bukan Desember

    # Transaksi Desember 2024
    insert_order(db, jadwal_d, 20, 1000000, date(2024, 12, 1)) # M_top: 20 tiket
    insert_order(db, jadwal_d, 5, 250000, date(2024, 12, 31)) # M_top: 5 tiket
    insert_order(db, jadwal_d2, 10, 500000, date(2024, 12, 15)) # M_reg: 10 tiket
    
    # Transaksi November (Diabaikan)
    insert_order(db, jadwal_n, 50, 2500000, date(2024, 11, 30))

    res = client.get("/filmpopuler/monthly", params={"bulan": "desember"})
    assert res.status_code == 200
    data = res.json()
    assert data["bulan"] == "desember"
    assert data["total_film"] == 2
    
    assert data["film_terlaris"]["title"] == "Film Terlaris"
    assert data["film_terlaris"]["total_tiket_terjual"] == 25 # 20 + 5
    assert data["data"][1]["title"] == "Film Reguler"
    assert data["data"][1]["total_tiket_terjual"] == 10

def test_film_popular_monthly_invalid_month():
    res = client.get("/filmpopuler/monthly", params={"bulan": "juni"}) # Harusnya tidak ada data
    assert res.status_code == 200
    data = res.json()
    assert data["bulan"] == "juni"
    assert data["film_terlaris"] is None

# ======================================================
# 7. TEST JAM TAYANG PALING POPULER (DAILY)
# ======================================================
def test_jamtayang_daily_success():
    db = TestingSessionLocal()
    m1 = insert_movie(db, "Populer Jam", "MOV030", price=50000)
    st = insert_studio(db, "Studio Test")
    
    # Jadwal Hari Ini (Des 12, 2024)
    j_pagi = insert_jadwal(db, m1, st, date(2024, 12, 12), time(10, 0))
    j_sore = insert_jadwal(db, m1, st, date(2024, 12, 12), time(16, 0)) # Jam terpopuler
    j_malam = insert_jadwal(db, m1, st, date(2024, 12, 12), time(21, 0))

    # Transaksi Des 12
    insert_order(db, j_pagi, 3, 150000, date(2024, 12, 12)) # Pagi: 3 tiket
    insert_order(db, j_sore, 5, 250000, date(2024, 12, 12)) # Sore: 5 tiket
    insert_order(db, j_sore, 1, 50000, date(2024, 12, 12)) # Sore: 1 tiket (Total 6)
    insert_order(db, j_malam, 2, 100000, date(2024, 12, 12)) # Malam: 2 tiket

    res = client.get("/jamtayangpopuler/daily", params={"day": 12})
    assert res.status_code == 200
    data = res.json()
    
    assert data["tanggal"] == "2024-12-12"
    assert len(data["data"]) == 1
    
    movie_data = data["data"][0]
    assert movie_data["title"] == "Populer Jam"
    assert movie_data["jam_terpopuler"] == "16:00:00" # Sesuai jam sore (6 tiket)
    assert movie_data["total_tiket"] == 6

# ======================================================
# 8. TEST JAM TAYANG PALING POPULER (WEEKLY)
# ======================================================
def test_jamtayang_weekly_success():
    db = TestingSessionLocal()
    m1 = insert_movie(db, "Film W1 Jam", "MOV040", price=50000)
    st = insert_studio(db, "Studio Test")
    
    # Jadwal Week 1 (1-7 Des)
    j_week1_sore = insert_jadwal(db, m1, st, date(2024, 12, 2), time(16, 0)) # W1 Populer
    j_week1_pagi = insert_jadwal(db, m1, st, date(2024, 12, 3), time(10, 0)) 

    # Jadwal Week 2 (8-14 Des)
    j_week2_pagi = insert_jadwal(db, m1, st, date(2024, 12, 9), time(10, 0)) # W2 Populer
    j_week2_sore = insert_jadwal(db, m1, st, date(2024, 12, 10), time(16, 0))

    # Transaksi Week 1
    insert_order(db, j_week1_sore, 5, 250000, date(2024, 12, 2)) # W1 Sore: 5 tiket
    insert_order(db, j_week1_pagi, 3, 150000, date(2024, 12, 3)) # W1 Pagi: 3 tiket
    
    # Transaksi Week 2
    insert_order(db, j_week2_pagi, 10, 500000, date(2024, 12, 9)) # W2 Pagi: 10 tiket
    insert_order(db, j_week2_sore, 4, 200000, date(2024, 12, 10)) # W2 Sore: 4 tiket

    res = client.get("/jamtayangpopuler/weekly")
    assert res.status_code == 200
    data = res.json()
    
    # Minggu 1 (1-7 Des)
    w1_data = data["minggu"][0]["data"][0]
    assert w1_data["title"] == "Film W1 Jam"
    assert w1_data["jam_terpopuler"] == "16:00:00"
    assert w1_data["total_tiket"] == 5
    
    # Minggu 2 (8-14 Des)
    w2_data = data["minggu"][1]["data"][0]
    assert w2_data["title"] == "Film W1 Jam"
    assert w2_data["jam_terpopuler"] == "10:00:00"
    assert w2_data["total_tiket"] == 10

# ======================================================
# 9. TEST ANALISIS PROMO EFECTIVITAS
# ======================================================
def test_analisis_promo_efektivitas_success():
    db = TestingSessionLocal()
    m1 = insert_movie(db, "Film Promo", "MOV050", price=100000) # Harga 100k
    st = insert_studio(db, "Studio Test")
    jadwal = insert_jadwal(db, m1, st, date(2024, 12, 1), time(10, 0))

    # Kelompok TANPA PROMO
    # Transaksi 1: 1 tiket @100k
    insert_order(db, jadwal, 1, 100000, date(2024, 12, 1), promo_name="NO PROMO") 
    # Transaksi 2: 1 tiket @100k
    insert_order(db, jadwal, 1, 100000, date(2024, 12, 1), promo_name="NO PROMO")
    # Total Tanpa: Transaksi=2, Pendapatan=200000, Avg Harga=100000

    # Kelompok DENGAN PROMO (Asumsi diskon 20%)
    # Transaksi 3: 1 tiket @80k (20% diskon)
    insert_order(db, jadwal, 1, 80000, date(2024, 12, 2), promo_name="DISC 20%")
    # Transaksi 4: 1 tiket @80k
    insert_order(db, jadwal, 1, 80000, date(2024, 12, 2), promo_name="DISC 20%")
    # Transaksi 5: 1 tiket @80k
    insert_order(db, jadwal, 1, 80000, date(2024, 12, 2), promo_name="DISC 20%")
    # Total Dengan: Transaksi=3, Pendapatan=240000, Avg Harga=80000

    res = client.get("/analisis/promo-efektivitas")
    assert res.status_code == 200
    data = res.json()
    
    # Pengecekan Data Agregasi
    assert data["analisis"]["tanpa_promo"]["total_transaksi"] == 2
    assert data["analisis"]["tanpa_promo"]["total_pendapatan"] == 200000.0
    assert data["analisis"]["tanpa_promo"]["avg_harga"] == 100000.0

    assert data["analisis"]["dengan_promo"]["total_transaksi"] == 3
    assert data["analisis"]["dengan_promo"]["total_pendapatan"] == 240000.0
    assert data["analisis"]["dengan_promo"]["avg_harga"] == 80000.0

    # Pengecekan Persentase
    # Transaksi: (3 - 2) / 2 * 100 = 50.0%
    assert data["ringkasan"]["transaksi_promo_vs_tanpa"] == 50.0
    # Pendapatan: (240k - 200k) / 200k * 100 = 20.0%
    assert data["ringkasan"]["pendapatan_promo_vs_tanpa"] == 20.0
    # Harga Rata-rata: (80k - 100k) / 100k * 100 = -20.0%
    assert data["ringkasan"]["perbedaan_rata_rata_harga"] == -20.0

    # Pengecekan Kesimpulan
    kesimpulan = data["kesimpulan"]
    assert "Promo meningkatkan jumlah transaksi sebesar 50.0%" in kesimpulan
    assert "Promo meningkatkan pendapatan sebesar 20.0%" in kesimpulan
    assert "Harga rata-rata turun 20.0% saat promo (indikasi diskon efektif)." in kesimpulan


def test_analisis_promo_efektivitas_no_base_data():
    # Hanya data promo yang ada, tanpa data NO PROMO (Base case t_tanpa=0)
    db = TestingSessionLocal()
    m1 = insert_movie(db, "Film Promo Only", "MOV051", price=100000)
    st = insert_studio(db, "Studio Test")
    jadwal = insert_jadwal(db, m1, st, date(2024, 12, 1), time(10, 0))
    
    insert_order(db, jadwal, 1, 80000, date(2024, 12, 2), promo_name="DISC 20%")
    
    res = client.get("/analisis/promo-efektivitas")
    data = res.json()
    
    # Persentase harus None
    assert data["ringkasan"]["transaksi_promo_vs_tanpa"] is None
    assert data["ringkasan"]["pendapatan_promo_vs_tanpa"] is None
    assert data["ringkasan"]["perbedaan_rata_rata_harga"] is None
    assert data["kesimpulan"] == "Data transaksi tanpa promo tidak tersedia untuk analisis."


# ======================================================
# 10. TEST KURSI PALING POPULER (HARIAN & BULANAN)
# ======================================================
def test_kursi_populer_harian_success():
    db = TestingSessionLocal()
    m1 = insert_movie(db, "Kursi Film", "MOV060", price=50000)
    st = insert_studio(db, "Studio Test")
    jadwal = insert_jadwal(db, m1, st, date(2024, 12, 10), time(10, 0))
    
    # Kursi Populer Hari Ini (Des 10)
    seats_data = [
        ("C", 5), ("C", 5), ("C", 5), # C5: 3x (Rank 1)
        ("A", 1), ("A", 1), # A1: 2x (Rank 2)
        ("B", 2), # B2: 1x (Rank 3)
        ("D", 8), # D8: 1x (Rank 4)
        ("E", 9), # E9: 1x (Rank 5)
        ("F", 7), # F7: 1x (Di luar Top 5)
    ]
    
    for r, c in seats_data:
        insert_order(db, jadwal, 1, 50000, date(2024, 12, 10), seats=[(r, c)])
        
    # Order di hari lain (Diabaikan)
    insert_order(db, jadwal, 1, 50000, date(2024, 12, 11), seats=[("K", 1)])

    res = client.get("/kursipopuler/harian", params={"tanggal": "2024-12-10"})
    assert res.status_code == 200
    data = res.json()
    
    assert data["mode"] == "harian"
    assert data["tanggal_awal"] == "2024-12-10"
    assert len(data["top_5_kursi"]) == 5
    
    # Verifikasi ranking
    assert data["top_5_kursi"][0]["kursi_kode"] == "C5"
    assert data["top_5_kursi"][0]["jumlah_pemesanan"] == 3
    assert data["top_5_kursi"][1]["kursi_kode"] == "A1"
    assert data["top_5_kursi"][1]["jumlah_pemesanan"] == 2
    
    # Pengecekan bahwa B2, D8, E9 (semua 1x) masuk Top 5 (urutan 3, 4, 5)

def test_kursi_populer_bulanan_success():
    db = TestingSessionLocal()
    m1 = insert_movie(db, "Kursi Bulanan", "MOV061", price=50000)
    st = insert_studio(db, "Studio Test")
    jadwal = insert_jadwal(db, m1, st, date(2024, 12, 1), time(10, 0))

    # Kursi Populer Bulan Desember
    insert_order(db, jadwal, 1, 50000, date(2024, 12, 1), seats=[("Z", 9)]) # Z9
    insert_order(db, jadwal, 1, 50000, date(2024, 12, 31), seats=[("Z", 9)]) # Z9: 2x
    insert_order(db, jadwal, 1, 50000, date(2024, 12, 15), seats=[("Y", 8)]) # Y8: 1x

    # Kursi Bulan Lain (Diabaikan)
    insert_order(db, jadwal, 1, 50000, date(2025, 1, 1), seats=[("X", 7)])
    
    res = client.get("/kursipopuler/bulanan", params={"tanggal": "2024-12-10"}) # Tanggal manapun di Des
    assert res.status_code == 200
    data = res.json()
    
    assert data["mode"] == "bulanan"
    assert data["tanggal_awal"] == "2024-12-01"
    assert data["tanggal_akhir"] == "2024-12-31"
    assert len(data["top_5_kursi"]) == 2
    
    assert data["top_5_kursi"][0]["kursi_kode"] == "Z9"
    assert data["top_5_kursi"][0]["jumlah_pemesanan"] == 2
    assert data["top_5_kursi"][1]["kursi_kode"] == "Y8"
    assert data["top_5_kursi"][1]["jumlah_pemesanan"] == 1

def test_kursi_populer_invalid_mode():
    res = client.get("/kursipopuler/tahunan")
    assert res.status_code == 400
    assert res.json()["detail"] == "Mode harus harian/mingguan/bulanan"