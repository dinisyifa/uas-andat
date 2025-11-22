# app/routers/user_catalog.py
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

# Import data dari admin
from app.routers.admin_film import list_film
from app.routers.admin_jadwal import list_jadwal

router = APIRouter()

# =============================================== API KATALOG ================================================

# READ - Lihat semua film yang sedang tayang
@router.get("/now_playing")
def now_playing():
    """
    Menampilkan daftar semua film yang sedang tayang.
    (Mengambil dari list_film di admin_film.py)
    """
    if not list_film:
        raise HTTPException(status_code=404, detail="Tidak ada film yang sedang tayang.")

    data_ringkas = [
        {
            "id": film["id"],
            "title": film["title"],
            "genre": film.get("genre", "-"),
            "duration": film.get("duration", "-"),
            "rating_usia": film.get("rating_usia", "-"),
            "price": film.get("price", 0)
        }
        for film in list_film
    ]
    return {
        "message": "Daftar film yang sedang tayang berhasil diambil",
        "count": len(data_ringkas),
        "data": data_ringkas
    }


# READ - Lihat detail film dan jadwalnya
@router.get("/now_playing/{movie_id}/details")
def detail_film(movie_id: str):
    """
    Menampilkan detail film dan semua jadwal tayangnya.
    """
    # cari film
    movie = next((f for f in list_film if f["id"] == movie_id or f["id"] == f"mov{movie_id}"), None)
    if not movie:
        raise HTTPException(status_code=404, detail=f"Film dengan ID {movie_id} tidak ditemukan.")

    # cari jadwal berdasarkan movie_id (cocokkan dengan atau tanpa prefix 'mov')
    movie_schedules = [
    j for j in list_jadwal
    if j["movie_id"].replace("mov", "") == movie["id"].replace("mov", "")
    ]

    return {
        "id": movie["id"],
        "title": movie["title"],
        "sutradara": movie.get("sutradara", "-"),
        "rating_usia": movie.get("rating_usia", "-"),
        "price": movie.get("price", "-"),
        "schedules": [
            {
                "id_jadwal": j["id_jadwal"],
                "studio": j["studio_name"],
                "tanggal": j["date"],
                "waktu": j["time"]
            } for j in movie_schedules
        ]
    }

# layout kursi 
ROWS = 8
COLS = 12
AISLE_AFTER_COL = 6
ROW_LETTERS = [chr(ord("A") + i) for i in range(ROWS)]

def _empty_matrix() -> List[List[str]]:
    return [["." for _ in range(COLS)] for _ in range(ROWS)]

# ---------------------------
# Seats State (in-memory)
# ---------------------------
def _sid(x: Any) -> str:
    """paksa id jadi string (aman kalau sumbernya int/str)."""
    return str(x)

SEATS_BY_SCHEDULE: Dict[str, List[List[str]]] = {}

def _ensure_matrix(schedule_id: Any) -> List[List[str]]:
    sid = _sid(schedule_id)
    if sid not in SEATS_BY_SCHEDULE:
        SEATS_BY_SCHEDULE[sid] = _empty_matrix()
    return SEATS_BY_SCHEDULE[sid]

# =============================================== API KURSI ================================================

# READ - Lihat denah kursi untuk jadwal tertentu
@router.get("/schedules/{schedule_id}/seats")
def denah_kursi(schedule_id: str):
    _ensure_matrix(schedule_id)
    mat = SEATS_BY_SCHEDULE.get(_sid(schedule_id))
    if mat is None:
        raise HTTPException(status_code=404, detail="Jadwal tidak ditemukan")

    left  = " ".join(str(i) for i in range(1, AISLE_AFTER_COL + 1))
    right = " ".join(str(i) for i in range(AISLE_AFTER_COL + 1, COLS + 1))
    lines = ["          SCREEN", f"   {left}   {right}"]
    for r in range(ROWS):
        L = " ".join(mat[r][:AISLE_AFTER_COL])
        R = " ".join(mat[r][AISLE_AFTER_COL:])
        lines.append(f"{ROW_LETTERS[r]}  {L}   {R}")

    return {
        "schedule_id": _sid(schedule_id),
        "display": lines,
    }
