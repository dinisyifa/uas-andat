import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from datetime import date, time, timedelta

# Import komponen aplikasi utama
from app.main import app
from app.database import get_db

# Import model SQLAlchemy (Asumsi model berada di app.models)
from app.models import Movie, Jadwal, Studio, StudioSeat, OrderSeat, Cart 

# ======================================================
# 1. SETUP DATABASE (Mendefinisikan TestingSessionLocal)
# ======================================================
DATABASE_URL = "sqlite:///./app.db" 

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
# DEFINE TESTING SESSION
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
    # Hapus OrderSeat dan Cart terlebih dahulu karena ada FK ke Jadwal/StudioSeat
    db.query(OrderSeat).delete()
    db.query(Cart).delete()
    db.query(StudioSeat).delete()
    db.query(Jadwal).delete()
    db.query(Movie).delete()
    db.query(Studio).delete() 
    db.commit()
    db.close()


# ======================================================
# 3. HELPER FUNCTIONS KHUSUS INSERT DATA LANGSUNG KE DB
# ======================================================

def generate_code(model, prefix):
    """Generate kode sederhana berbasis ID terakhir."""
    db = TestingSessionLocal()
    last = db.query(model).order_by(model.id.desc()).first()
    next_id = (last.id + 1) if last else 1
    db.close()
    return f"{prefix}{str(next_id).zfill(3)}"

def insert_movie(db: Session, title: str, code: str, duration=120, price=50000, rating="R"):
    movie = Movie(
        id=int(code[3:]), 
        code=code, title=title, durasi=duration, price=price, 
        genre="Action", rating=rating, director="Dir A"
    )
    db.add(movie)
    db.commit()
    db.refresh(movie)
    return movie

def insert_studio(db: Session, name: str, rows: int, cols: int):
    code = generate_code(Studio, "STU")
    studio = Studio(id=int(code[3:]), code=code, name=name, rows=rows, cols=cols)
    db.add(studio)
    db.commit()
    db.refresh(studio)
    
    # Insert StudioSeat
    seats = []
    # Asumsi row adalah karakter ('A', 'B', ...)
    for r in [chr(65 + i) for i in range(rows)]: 
        for c in range(1, cols + 1):
            seats.append(StudioSeat(studio_id=studio.id, row=r, col=c))
    db.add_all(seats)
    db.commit()
    
    return studio

# PENTING: Memastikan Jadwal menggunakan ID numerik untuk FK
def insert_jadwal(db: Session, movie: Movie, studio: Studio, tanggal: date, jam: time):
    code = generate_code(Jadwal, "JAD")
    jadwal = Jadwal(
        id=int(code[3:]), code=code, 
        movie_id=movie.id,        # Menggunakan ID objek Movie
        studio_id=studio.id,      # Menggunakan ID objek Studio
        tanggal=tanggal, 
        jam=jam
    )
    db.add(jadwal)
    db.commit()
    db.refresh(jadwal)
    return jadwal

# ======================================================
# 4. TEST ENDPOINT: GET /now_playing
# ======================================================
def test_now_playing_success():
    db = TestingSessionLocal()
    # Tanggal mock sesuai dengan router (2024, 12, 1)
    today_mock = date(2024, 12, 1) 
    
    m1 = insert_movie(db, "Movie Today", "MOV001")
    s1 = insert_studio(db, "Studio 1", 5, 10)
    insert_jadwal(db, m1, s1, today_mock, time(10, 0)) # Tayang hari ini

    m2 = insert_movie(db, "Movie Tomorrow", "MOV002")
    s2 = insert_studio(db, "Studio 2", 5, 10)
    insert_jadwal(db, m2, s2, today_mock + timedelta(days=1), time(12, 0)) # Tayang besok

    m3 = insert_movie(db, "Movie Yesterday", "MOV003")
    s3 = insert_studio(db, "Studio 3", 5, 10)
    insert_jadwal(db, m3, s3, today_mock - timedelta(days=1), time(14, 0)) # Tidak akan muncul

    res = client.get("/now_playing")
    
    assert res.status_code == 200
    data = res.json()
    assert data["count"] == 2
    titles = {d["title"] for d in data["data"]}
    assert "Movie Today" in titles
    assert "Movie Tomorrow" in titles
    assert "Movie Yesterday" not in titles


def test_now_playing_empty():
    res = client.get("/now_playing")
    assert res.status_code == 404
    assert "Tidak ada film yang sedang tayang." in res.json()["detail"]


# ======================================================
# 5. TEST ENDPOINT: GET /now_playing/{movie_id}/details
# ======================================================
def test_detail_film_success():
    db = TestingSessionLocal()
    
    movie = insert_movie(db, "Detail Test Film", "MOV004")
    studio1 = insert_studio(db, "Studio Merah", 5, 5)
    studio2 = insert_studio(db, "Studio Biru", 8, 8)
    
    # Mencegah DetachedInstanceError: tidak ada db.close() di sini.
    jadwal1 = insert_jadwal(db, movie, studio1, date(2024, 12, 10), time(19, 0, 0))
    jadwal2 = insert_jadwal(db, movie, studio2, date(2024, 12, 11), time(14, 30, 0))

    res = client.get(f"/now_playing/{movie.code}/details")
    
    assert res.status_code == 200
    data = res.json()
    assert data["title"] == "Detail Test Film"
    assert len(data["schedules"]) == 2
    
    sch1 = data["schedules"][0]
    assert sch1["id_jadwal"] == jadwal1.code
    assert sch1["studio"] == "Studio Merah"
    assert sch1["tanggal"] == "2024-12-10"
    assert sch1["waktu"] == "19:00"      


def test_detail_film_not_found():
    res = client.get("/now_playing/MOVXXX/details")
    assert res.status_code == 404
    assert "Film dengan ID MOVXXX tidak ditemukan." in res.json()["detail"]


# ======================================================
# 6. TEST ENDPOINT: GET /schedules/{schedule_id}/seats
# ======================================================
def test_denah_kursi_success():
    db = TestingSessionLocal()
    
    movie = insert_movie(db, "Seat Movie", "MOV005")
    studio = insert_studio(db, "Studio Cek", 3, 5) # Rows: A, B, C. Cols: 1-5
    jadwal = insert_jadwal(db, movie, studio, date(2024, 12, 15), time(20, 0))

    # Kursi yang sudah dibooked (X)
    order_seat = OrderSeat(jadwal_id=jadwal.id, row='A', col=2)
    
    # Kursi yang ada di cart (~)
    # Menggunakan 'user_code' sebagai perbaikan untuk TypeError
    cart_item = Cart(jadwal_id=jadwal.id, row='C', col=5, membership_code="MEM001")

    db.add_all([order_seat, cart_item])
    db.commit()
    
    res = client.get(f"/schedules/{jadwal.code}/seats")
    
    assert res.status_code == 200
    data = res.json()
    assert data["movie_title"] == "Seat Movie"
    assert data["studio"] == "Studio Cek"
    
    display = data["display"]
    
    # Layout: Aisle setelah kolom 2 (karena total kolom 5 < 6)
    # A O X O   O O
    # C O O O   O ~
    
    # Verifikasi baris kolom
    assert display[1].strip() == "1 2   3 4 5" 

    # Baris A: A2 adalah X
    assert "O X O   O O" in display[2] 

    # Baris C: C5 adalah ~
    assert "O O O   O ~" in display[4] 


def test_denah_kursi_not_found():
    res = client.get("/schedules/JADXXX/seats")
    assert res.status_code == 404
    assert "Jadwal dengan ID JADXXX tidak ditemukan." in res.json()["detail"]