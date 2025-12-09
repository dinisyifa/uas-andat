from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from typing import List
from app.database import get_db
from app.models import Movie, Jadwal, Studio, StudioSeat, OrderSeat, Cart

router = APIRouter()

def movie_to_public_dict(m: Movie) -> dict:
    return {
        "code": m.code,         
        "title": m.title,
        "duration": m.durasi,
        "price": m.price,
        "genre": m.genre,
        "rating_usia": m.rating,
        "sutradara": m.director,
    }


# now playing
@router.get("/now_playing")
def now_playing(db: Session = Depends(get_db)):
    """Menampilkan seluruh daftar film yang sedang tayang."""
    today = date(2024, 12, 1) 

    movies = (
        db.query(Movie)
        .join(Jadwal, Jadwal.movie_id == Movie.id)
        .filter(Jadwal.tanggal >= today) 
        .distinct()
        .all()
    )

    if not movies:
        raise HTTPException(
            status_code=404,
            detail="Tidak ada film yang sedang tayang."
        )

    data_ringkas = [movie_to_public_dict(m) for m in movies]

    return {
        "message": "Daftar film yang sedang tayang berhasil diambil",
        "count": len(data_ringkas),
        "data": data_ringkas
    }



# now playing/{movie_code}/details
@router.get("/now_playing/{movie_code}/details")
def detail_film(movie_code: str, db: Session = Depends(get_db)):
    """
    Menampilkan detail film + semua jadwal tayangnya.
    Parameter diisi dengan movie code: MOVXXX (contoh: MOV001).
    """

    movie = db.query(Movie).filter(Movie.code == movie_code).first()
    if not movie:
        raise HTTPException(
            status_code=404,
            detail=f"Film dengan kode {movie_code} tidak ditemukan."
        )

    rows = (
        db.query(Jadwal, Studio)
        .join(Studio, Studio.id == Jadwal.studio_id)
        .filter(Jadwal.movie_id == movie.id)
        .order_by(Jadwal.tanggal, Jadwal.jam)
        .all()
    )

    schedules: List[dict] = []
    for j, st in rows:
        schedules.append(
            {
                "jadwal_code": j.code,                   
                "studio": st.name,                       
                "tanggal": j.tanggal.isoformat(),        
                "waktu": j.jam.strftime("%H:%M"),        
            }
        )

    result = movie_to_public_dict(movie)
    result["schedules"] = schedules

    return result



def build_seat_display(
    studio: Studio,
    studio_seats: List[StudioSeat],
    booked: set[tuple[str, int]],
    in_cart: set[tuple[str, int]],
) -> List[str]:
    """
    Bikin list string tampilan kursi:
      baris 0: "SCREEN"
      baris 1: nomor kursi kiri & kanan
      baris berikutnya: A/B/C... dengan simbol kursi

      O = available
      X = sudah dibeli (OrderSeat)
      ~ = ada di cart
    """

    if not studio_seats:
        return ["NO SEATS"]

    rows = sorted({s.row for s in studio_seats})
    cols = sorted({s.col for s in studio_seats})

    if len(cols) <= 6:
        aisle_after = len(cols) // 2
    else:
        aisle_after = 6

    lines: List[str] = []

    lines.append("          SCREEN")

    left_nums = [str(c) for c in cols if c <= aisle_after]
    right_nums = [str(c) for c in cols if c > aisle_after]
    left_str = " ".join(left_nums)
    right_str = " ".join(right_nums)
    lines.append(f"   {left_str}   {right_str}")

    for r in rows:
        left_syms = []
        right_syms = []
        for c in cols:
            key = (r, c)
            if key in booked:
                sym = "X"
            elif key in in_cart:
                sym = "~"
            else:
                sym = "O"

            if c <= aisle_after:
                left_syms.append(sym)
            else:
                right_syms.append(sym)

        L = " ".join(left_syms)
        R = " ".join(right_syms)
        lines.append(f"{r}  {L}   {R}")

    return lines



@router.get("/schedules/{jadwal_code}/seats")
def denah_kursi(jadwal_code: str, db: Session = Depends(get_db)):
    """
    Menampilkan peta kursi berdasarkan jadwal.
    Parameter diisi dengan jadwal code: JAD0XXX (contoh: JAD0001).
    """

    jadwal = db.query(Jadwal).filter(Jadwal.code == jadwal_code).first()
    if not jadwal:
        raise HTTPException(
            status_code=404,
            detail=f"Jadwal dengan kode {jadwal_code} tidak ditemukan."
        )

    studio = db.query(Studio).filter(Studio.id == jadwal.studio_id).first()
    movie = db.query(Movie).filter(Movie.id == jadwal.movie_id).first()

    if not studio or not movie:
        raise HTTPException(
            status_code=500,
            detail="Data studio atau film untuk jadwal ini tidak lengkap."
        )

    studio_seats = (
        db.query(StudioSeat)
        .filter(StudioSeat.studio_id == studio.id)
        .all()
    )

    booked_rows = (
        db.query(OrderSeat)
        .filter(OrderSeat.jadwal_id == jadwal.id)
        .all()
    )
    booked_set = {(s.row, s.col) for s in booked_rows}

    cart_rows = (
        db.query(Cart)
        .filter(Cart.jadwal_id == jadwal.id)
        .all()
    )
    cart_set = {(c.row, c.col) for c in cart_rows}

    display = build_seat_display(studio, studio_seats, booked_set, cart_set)

    return {
        "jadwal_code": jadwal_code,
        "movie_title": movie.title,
        "studio": studio.name,
        "display": display
    }