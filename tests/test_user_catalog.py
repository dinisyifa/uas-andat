import pytest
from fastapi.testclient import TestClient
from app.main import app
from datetime import date
from app.database import SessionLocal
from app.models import Movie, Jadwal, Studio, StudioSeat, OrderSeat, Cart

client = TestClient(app)


# ============================================================
# HELPERS (untuk memastikan data ada)
# ============================================================

def ensure_minimal_data():
    db = SessionLocal()

    movie = db.query(Movie).first()
    if not movie:
        movie = Movie(
            id=1,
            code="MOV001",
            title="Film Uji",
            genre="Action",
            durasi=120,
            director="Tester",
            rating="R",
            price=50000
        )
        db.add(movie)
        db.commit()
        db.refresh(movie)

    studio = db.query(Studio).first()
    if not studio:
        studio = Studio(
            id=1,
            code="ST001",
            name="Studio 1",
            rows=3,
            cols=4
        )
        db.add(studio)
        db.commit()
        db.refresh(studio)

    seats = db.query(StudioSeat).filter(StudioSeat.studio_id == studio.id).all()
    if not seats:
        for r in ["A", "B", "C"]:
            for c in range(1, 5):
                db.add(StudioSeat(studio_id=studio.id, row=r, col=c))
        db.commit()

    jadwal = db.query(Jadwal).filter(Jadwal.movie_id == movie.id).first()
    if not jadwal:
        jadwal = Jadwal(
            id=1,
            code="JAD001",
            studio_id=studio.id,
            movie_id=movie.id,
            tanggal=date(2024, 12, 1),
            jam="19:00"
        )
        db.add(jadwal)
        db.commit()
        db.refresh(jadwal)

    db.close()
    return movie, studio, jadwal


ensure_minimal_data()

@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()



def test_now_playing(db):
    response = client.get("/now_playing")
    assert response.status_code == 200

    json = response.json()
    assert "data" in json
    assert json["count"] >= 1



def test_movie_details(db):
    movie = db.query(Movie).first()

    response = client.get(f"/now_playing/{movie.code}/details")
    assert response.status_code == 200

    json = response.json()
    assert json["code"] == movie.code
    assert "schedules" in json
    assert len(json["schedules"]) >= 1


def test_movie_details_not_found():
    response = client.get("/now_playing/MOV999/details")
    assert response.status_code == 404



def test_seat_map(db):
    jadwal = db.query(Jadwal).first()

    response = client.get(f"/schedules/{jadwal.code}/seats")
    assert response.status_code == 200

    json = response.json()
    assert json["jadwal_code"] == jadwal.code
    assert "display" in json
    assert len(json["display"]) >= 1


def test_seat_map_not_found():
    response = client.get("/schedules/JAD999/seats")
    assert response.status_code == 404



def test_seat_status_booked_and_cart(db):
    
    movie_code = "MOV100"
    studio_code = "ST100"
    jadwal_code = "JAD100"
    
    existing_jadwal = db.query(Jadwal).filter(Jadwal.code == jadwal_code).first()
    existing_studio = db.query(Studio).filter(Studio.code == studio_code).first()
    
    if existing_jadwal:
        db.query(OrderSeat).filter(OrderSeat.jadwal_id == existing_jadwal.id).delete()
        db.query(Cart).filter(Cart.jadwal_id == existing_jadwal.id).delete()
        db.delete(existing_jadwal)

    if existing_studio:
        db.query(StudioSeat).filter(StudioSeat.studio_id == existing_studio.id).delete()
        db.delete(existing_studio)
    
    existing_movie = db.query(Movie).filter(Movie.code == movie_code).first()
    if existing_movie:
        db.delete(existing_movie)

    db.commit() 

    movie = Movie(
        code=movie_code,
        title="Test Film",
        durasi=120,
        price=50000,
        genre="Action",
        rating="13+",
        director="John"
    )
    db.add(movie)
    db.commit()
    db.refresh(movie)

    studio = Studio(code=studio_code, name="Studio 1", rows=1, cols=2)
    db.add(studio)
    db.commit()
    db.refresh(studio)

    jadwal = Jadwal(
        code=jadwal_code,
        movie_id=movie.id,
        studio_id=studio.id,
        tanggal=date(2024, 12, 1),
        jam="19:00"
    )
    db.add(jadwal)
    db.commit()
    db.refresh(jadwal)

    s1 = StudioSeat(studio_id=studio.id, row="A", col=1)
    s2 = StudioSeat(studio_id=studio.id, row="A", col=2)
    db.add_all([s1, s2])
    db.commit()

    order_seat = OrderSeat(jadwal_id=jadwal.id, row="A", col=1) 
    cart_item = Cart(jadwal_id=jadwal.id, row="A", col=2) 
    db.add_all([order_seat, cart_item])
    db.commit()


    response = client.get(f"/schedules/{jadwal.code}/seats")
    assert response.status_code == 200

    data = response.json()
    disp = "\n".join(data["display"])

    assert "X" in disp 
    assert "~" in disp


    db.delete(order_seat)
    db.delete(cart_item)
    db.delete(s1) 
    db.delete(s2) 
    db.delete(jadwal)
    db.delete(studio)
    db.delete(movie)
    db.commit()