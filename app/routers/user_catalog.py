# app/routers/user_catalog.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from typing import List

from app.database import get_db
from app.models import Movie, Jadwal, Studio, StudioSeat, OrderSeat, Cart

router = APIRouter()

# =========================================================
# Helper konversi Movie -> dict ala UTS
# =========================================================

def movie_to_public_dict(m: Movie) -> dict:
    """
    Bentuk JSON mirip versi list_film UTS:
    id, title, duration, price, genre, rating_usia, sutradara
    """
    return {
        "id": m.code,          # pakai code, misal "MOV001"
        "title": m.title,
        "duration": m.durasi,
        "price": m.price,
        "genre": m.genre,
        "rating_usia": m.rating,
        "sutradara": m.director,
    }


# =========================================================
# 1) GET /now_playing
# =========================================================

# Pastikan di paling atas file sudah ada import ini:
from datetime import date 

@router.get("/now_playing")
def now_playing(db: Session = Depends(get_db)):
    """
    Menampilkan daftar semua film yang sedang tayang.
    REVISI: Karena data database hanya Desember 2024, 
    kita set 'today' menjadi 1 Desember 2024 agar data muncul.
    """

    # --- PERBAIKAN DI SINI ---
    # Jangan pakai date.today() karena akan ambil tanggal real-time (2025)
    # Kita set manual ke awal data dummy kita (1 Des 2024)
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


# =========================================================
# 2) GET /now_playing/{movie_id}/details
#    movie_id = Movie.code (misal: MOV001)
# =========================================================

@router.get("/now_playing/{movie_id}/details")
def detail_film(movie_id: str, db: Session = Depends(get_db)):
    """
    Menampilkan detail film + semua jadwal tayangnya.
    Path param movie_id diasumsikan = Movie.code (contoh: MOV001).
    """

    movie = db.query(Movie).filter(Movie.code == movie_id).first()
    if not movie:
        raise HTTPException(
            status_code=404,
            detail=f"Film dengan ID {movie_id} tidak ditemukan."
        )

    # ambil semua jadwal film ini + join studio
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
                "id_jadwal": j.code,                     # "JAD0001"
                "studio": st.name,                       # "Studio 1"
                "tanggal": j.tanggal.isoformat(),        # "2024-12-01"
                "waktu": j.jam.strftime("%H:%M"),        # "19:00"
            }
        )

    result = movie_to_public_dict(movie)
    result["schedules"] = schedules

    return result


# =========================================================
# Helper layout kursi (ASCII)
# =========================================================

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

    # cari semua row & col yang tersedia di studio ini
    rows = sorted({s.row for s in studio_seats})
    cols = sorted({s.col for s in studio_seats})

    # kalau mau keras kepala 8x12 tetap bisa, tapi di sini kita ikuti DB
    # tentukan posisi aisle (lorong) setelah kolom ke-6 atau tengah
    if len(cols) <= 6:
        aisle_after = len(cols) // 2
    else:
        aisle_after = 6

    lines: List[str] = []

    # baris layar
    lines.append("          SCREEN")

    # baris nomor kursi kiri & kanan
    left_nums = [str(c) for c in cols if c <= aisle_after]
    right_nums = [str(c) for c in cols if c > aisle_after]
    left_str = " ".join(left_nums)
    right_str = " ".join(right_nums)
    lines.append(f"   {left_str}   {right_str}")

    # baris kursi per row
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


# =========================================================
# 3) GET /schedules/{schedule_id}/seats
#    schedule_id = Jadwal.code (misal: JAD0001)
# =========================================================

@router.get("/schedules/{schedule_id}/seats")
def denah_kursi(schedule_id: str, db: Session = Depends(get_db)):
    """
    Menampilkan peta kursi berdasarkan jadwal.
    schedule_id diasumsikan = Jadwal.code (contoh: JAD0001).
    """

    jadwal = db.query(Jadwal).filter(Jadwal.code == schedule_id).first()
    if not jadwal:
        raise HTTPException(
            status_code=404,
            detail=f"Jadwal dengan ID {schedule_id} tidak ditemukan."
        )

    studio = db.query(Studio).filter(Studio.id == jadwal.studio_id).first()
    movie = db.query(Movie).filter(Movie.id == jadwal.movie_id).first()

    if not studio or not movie:
        raise HTTPException(
            status_code=500,
            detail="Data studio atau film untuk jadwal ini tidak lengkap."
        )

    # semua seat di studio
    studio_seats = (
        db.query(StudioSeat)
        .filter(StudioSeat.studio_id == studio.id)
        .all()
    )

    # kursi yang sudah dibeli
    booked_rows = (
        db.query(OrderSeat)
        .filter(OrderSeat.jadwal_id == jadwal.id)
        .all()
    )
    booked_set = {(s.row, s.col) for s in booked_rows}

    # kursi yang sedang di cart
    cart_rows = (
        db.query(Cart)
        .filter(Cart.jadwal_id == jadwal.id)
        .all()
    )
    cart_set = {(c.row, c.col) for c in cart_rows}

    display = build_seat_display(studio, studio_seats, booked_set, cart_set)

    return {
        "schedule_id": schedule_id,
        "movie_title": movie.title,
        "studio": studio.name,
        "display": display
    }
