import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import datetime

from app.main import app
from app.database import Base, get_db
from app.models import Movie, Jadwal, Order, OrderSeat, Studio, Membership


TEST_DB = "mysql+pymysql://root:%40Keju1234@localhost:3306/bioskop"

engine_test = create_engine(TEST_DB)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


Base.metadata.drop_all(bind=engine_test)
Base.metadata.create_all(bind=engine_test)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture
def seed_data():
    db = TestingSessionLocal()
    try:

        db.query(OrderSeat).delete()
        db.query(Order).delete()
        db.query(Jadwal).delete()
        db.query(Movie).delete()
        db.query(Studio).delete()
        db.commit()
    except:
        db.rollback()


    m1 = Movie(code="M01", title="Film A", genre="Action", durasi=120, price=50000)
    m2 = Movie(code="M02", title="Film B", genre="Comedy", durasi=100, price=50000)
    db.add_all([m1, m2])
    db.commit()


    st = Studio(code="S01", name="Studio 1", rows=5, cols=5)
    db.add(st)
    db.commit()


    tgl = datetime.date(2024, 12, 5)
    j1 = Jadwal(code="J01", movie_id=m1.id, studio_id=st.id, tanggal=tgl, jam=datetime.time(14,0))
    j2 = Jadwal(code="J02", movie_id=m2.id, studio_id=st.id, tanggal=tgl, jam=datetime.time(16,0))
    db.add_all([j1, j2])
    db.commit()


    o1 = Order(code="O01", jadwal_id=j1.id, payment_method="QRIS", transaction_date=tgl, final_price=100000)
    o2 = Order(code="O02", jadwal_id=j2.id, payment_method="Cash", transaction_date=tgl, final_price=50000)
    db.add_all([o1, o2])
    db.commit()

    s1 = OrderSeat(order_id=o1.id, jadwal_id=j1.id, studio_id=st.id, row="A", col=1)
    s2 = OrderSeat(order_id=o1.id, jadwal_id=j1.id, studio_id=st.id, row="A", col=2)
    s3 = OrderSeat(order_id=o2.id, jadwal_id=j2.id, studio_id=st.id, row="A", col=3)
    db.add_all([s1, s2, s3])
    db.commit()
    db.close()

@pytest.fixture
def seed_data_tiff():
    db = TestingSessionLocal()
    try:

        db.query(OrderSeat).delete()
        db.query(Order).delete()
        db.query(Jadwal).delete()
        db.query(Movie).delete()
        db.query(Studio).delete()
        db.query(Membership).delete()
        db.commit()
    except:
        db.rollback()

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


def test_filmpopuler_daily(seed_data):
    response = client.get("/analisis/filmpopuler?periode=harian&hari=5")
    assert response.status_code == 200
    data = response.json()
    assert "tanggal" in data
    assert "data" in data
    assert isinstance(data["data"], list)

def test_filmpopuler_weekly(seed_data):
    response = client.get("/analisis/filmpopuler?periode=mingguan")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert isinstance(data["data"], list)

def test_filmpopuler_monthly(seed_data):
    response = client.get("/analisis/filmpopuler?periode=bulanan&bulan=Desember")
    assert response.status_code == 200
    data = response.json()
    assert "bulan" in data
    assert "data" in data

def test_jamtayang_daily(seed_data):
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



def test_tiff_top_revenue_daily(seed_data_tiff):
    res = client.get("/analisis/top-revenue-films?period=hari")
    assert res.status_code == 200

    hasil = next((x for x in res.json()["hasil_analisis"] if "Tanggal 1" in x["periode"]), None)
    assert hasil is not None
    assert hasil["film_juara"] == "Action Movie"
    assert float(hasil["pendapatan"]) == 150000.0

def test_tiff_top_customers_monthly(seed_data_tiff):
    res = client.get("/analisis/top-customers?period=bulan")
    assert res.status_code == 200

    bulan_des = res.json()["hasil_analisis"][0]
    
    assert bulan_des["pelanggan_juara"] == "Tester"
    assert bulan_des["jumlah_transaksi"] == 3

def test_tiff_most_busiest_day(seed_data_tiff):

    res = client.get("/analisis/most-busiest-day?bulan=12&tahun=2024")
    assert res.status_code == 200
    data = res.json()
    
    assert "4 tiket" in data["kesimpulan"]["tanggal_tersibuk"]
    
    top_day = data["ranking_hari_teramai"][0]

    assert top_day["nama_hari"] in ["Sunday", "Minggu"]
    assert int(top_day["total_akumulasi_tiket"]) == 4



def test_tiff_promo_efektivitas(seed_data): 

    response = client.get("/analisis/promo-efektivitas")
    assert response.status_code == 200
    data = response.json()
    assert "kesimpulan" in data
    assert "tanpa_promo" in data["analisis"]


def test_kursipopuler_harian(seed_data):

    response = client.get("/analisis/kursipopuler/harian?tanggal=2024-12-05")
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "harian"
    assert len(data["top_5_kursi"]) >= 1

    kursi_muncul = [k["kursi_kode"] for k in data["top_5_kursi"]]
    assert any(x in kursi_muncul for x in ["A1", "A2", "A3"])

def test_kursipopuler_bulanan(seed_data):

    response = client.get("/analisis/kursipopuler/bulanan?tanggal=2024-12-05")
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "bulanan"