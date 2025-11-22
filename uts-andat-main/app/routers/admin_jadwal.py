# app/routers/admin_jadwal.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from typing import List, Dict, Any
from app.routers.admin_film import list_film, list_studio
from app.models import Schedule

router = APIRouter()

# Layout kursi 8x(6+6) dengan lorong tengah
def init_seats() -> List[List[Dict[str, Any]]]:
    rows = 8
    cols_per_side = 6
    seat_layout: List[List[Dict[str, Any]]] = []
    for r in range(rows):
        row_letter = chr(65 + r)  # A..H
        row_seats: List[Dict[str, Any]] = []
        # kiri
        for c in range(1, cols_per_side + 1):
            row_seats.append({"seat": f"{row_letter}{c}", "available": True})
        # lorong
        row_seats.append({"seat": " ", "available": None})
        # kanan
        for c in range(cols_per_side + 1, cols_per_side * 2 + 1):
            row_seats.append({"seat": f"{row_letter}{c}", "available": True})
        seat_layout.append(row_seats)
    return seat_layout


# helper cari film / studio pada admin_film lists (tidak membuat entitas baru)
def find_film(movie_id: str):
    return next((f for f in list_film if str(f.get("id")) == str(movie_id)), None)


def find_studio(studio_id: str):
    return next((s for s in list_studio if str(s.get("id")) == str(studio_id)), None)


# Database Jadwal
raw_jadwal_template = [
    # Avengers (mov1)
    {"id": "sch1",  "movie_id": "mov1", "studio_id": "st1", "date": "2025-10-15", "time": "12.15 - 15.05"},
    {"id": "sch2",  "movie_id": "mov1", "studio_id": "st2", "date": "2025-10-15", "time": "14.45 - 17.10"},
    {"id": "sch3",  "movie_id": "mov1", "studio_id": "st3", "date": "2025-10-15", "time": "14.50 - 17.15"},
    {"id": "sch4",  "movie_id": "mov1", "studio_id": "st4", "date": "2025-10-15", "time": "13.20 - 16.40"},
    {"id": "sch5",  "movie_id": "mov1", "studio_id": "st5", "date": "2025-10-15", "time": "19.40 - 23.00"},

    # The Conjuring (mov2)
    {"id": "sch6",  "movie_id": "mov2", "studio_id": "st2", "date": "2025-10-15", "time": "12.15 - 14.15"},
    {"id": "sch7",  "movie_id": "mov2", "studio_id": "st3", "date": "2025-10-15", "time": "17.30 - 19.30"},
    {"id": "sch8",  "movie_id": "mov2", "studio_id": "st4", "date": "2025-10-15", "time": "17.00 - 19.00"},
    {"id": "sch9",  "movie_id": "mov2", "studio_id": "st5", "date": "2025-10-15", "time": "10.00 - 12.10"},
    {"id": "sch10", "movie_id": "mov2", "studio_id": "st1", "date": "2025-10-15", "time": "12.10 - 14.10"},

    # Frozen (mov3)
    {"id": "sch11", "movie_id": "mov3", "studio_id": "st3", "date": "2025-10-15", "time": "10.00 - 12.10"},
    {"id": "sch12", "movie_id": "mov3", "studio_id": "st4", "date": "2025-10-15", "time": "19.20 - 20.30"},
    {"id": "sch13", "movie_id": "mov3", "studio_id": "st5", "date": "2025-10-15", "time": "16.55 - 19.15"},
    {"id": "sch14", "movie_id": "mov3", "studio_id": "st1", "date": "2025-10-15", "time": "17.00 - 19.10"},
    {"id": "sch15", "movie_id": "mov3", "studio_id": "st2", "date": "2025-10-15", "time": "17.40 - 20.00"},

    # Komang (mov4)
    {"id": "sch16", "movie_id": "mov4", "studio_id": "st4", "date": "2025-10-15", "time": "11.00 - 13.10"},
    {"id": "sch17", "movie_id": "mov4", "studio_id": "st5", "date": "2025-10-15", "time": "14.45 - 16.55"},
    {"id": "sch18", "movie_id": "mov4", "studio_id": "st1", "date": "2025-10-15", "time": "10.00 - 12.10"},
    {"id": "sch19", "movie_id": "mov4", "studio_id": "st2", "date": "2025-10-15", "time": "20.30 - 22.40"},
    {"id": "sch20", "movie_id": "mov4", "studio_id": "st3", "date": "2025-10-15", "time": "20.00 - 22.10"},

    # Detective Conan: One-eyed Flashback (mov5)
    {"id": "sch21", "movie_id": "mov5", "studio_id": "st1", "date": "2025-10-15", "time": "14.30 - 16.35"},
    {"id": "sch22", "movie_id": "mov5", "studio_id": "st2", "date": "2025-10-15", "time": "10.00 - 12.05"},
    {"id": "sch23", "movie_id": "mov5", "studio_id": "st3", "date": "2025-10-15", "time": "12.15 - 14.10"},
    {"id": "sch24", "movie_id": "mov5", "studio_id": "st4", "date": "2025-10-15", "time": "20.40 - 22.45"},
]

# bangun list_jadwal final (hanya memasukkan jadwal yang referensi film & studio ada)
list_jadwal: List[Dict[str, Any]] = []
for r in raw_jadwal_template:
    film = find_film(r["movie_id"])
    studio = find_studio(r["studio_id"])
    if not film:
        film = {"title": r["movie_id"]}
    if not studio:
        studio = {"name": r["studio_id"]}
    jadwal = {
        "id_jadwal": r["id"],
        "movie_id": r["movie_id"],
        "movie_title": film.get("title"),
        "studio_id": r["studio_id"],
        "studio_name": studio.get("name") or studio.get("title") or r["studio_id"],
        "date": r["date"],
        "time": r["time"],
        "seats": init_seats()
    }
    list_jadwal.append(jadwal)

# schedule_counter untuk penambahan jadwal baru
schedule_counter = len(list_jadwal) + 1

# =============================================== API JADWAL ================================================

# READ - Lihat semua jadwal
@router.get("/schedules")
def lihat_semua_jadwal():
    data_ringkas = [
        {
            "id_jadwal": j["id_jadwal"],
            "movie_title": j["movie_title"],
            "studio_name": j["studio_name"],
            "date": j["date"],
            "time": j["time"],
            "seats": j["seats"],
        }
        for j in list_jadwal
    ]
    return {"message": "Daftar jadwal berhasil diambil!", "data": data_ringkas}


# CREATE - Tambah jadwal baru
@router.post("/schedules")
def tambah_jadwal(payload: Schedule):
    """
    Admin dapat menambahkan jadwal tayang.
    """
    movie_id = str(payload.movie_id or "").strip()
    studio_id = str(payload.studio_id or "").strip()
    date_val = payload.date or ""
    time_val = payload.time or ""

    if not movie_id or not studio_id:
        raise HTTPException(status_code=400, detail="movie_id dan studio_id wajib diisi")

    film = find_film(movie_id)
    studio = find_studio(studio_id)
    if not film:
        raise HTTPException(status_code=404, detail="Film tidak ditemukan")
    if not studio:
        raise HTTPException(status_code=404, detail="Studio tidak ditemukan")

    new_id = f"sch{len(list_jadwal) + 1}"
    new_schedule = {
        "id_jadwal": new_id,
        "movie_id": movie_id,
        "movie_title": film.get("title"),
        "studio_id": studio_id,
        "studio_name": studio.get("name") or studio.get("title") or studio_id,
        "date": date_val,
        "time": time_val,
        "seats": init_seats()
    }
    list_jadwal.append(new_schedule)
    return {"message": "Jadwal berhasil dibuat", "data": new_schedule}

# UPDATE - Perbarui jadwal
@router.put("/schedules/{schedule_id}")
def update_jadwal(schedule_id: str, updated_data: Schedule):
    """
    Memperbarui data jadwal berdasarkan id_jadwal.
    """
    # Cari jadwal yang sesuai
    jadwal = next((j for j in list_jadwal if j["id_jadwal"] == schedule_id), None)
    if not jadwal:
        raise HTTPException(status_code=404, detail="Jadwal tidak ditemukan")

    # Validasi: cek apakah movie_id valid
    film = next((f for f in list_film if f["id"] == updated_data.movie_id), None)
    if not film:
        raise HTTPException(status_code=404, detail="Film tidak ditemukan")

    # Validasi: cek apakah studio_id valid
    studio = next((s for s in list_studio if s["id"] == updated_data.studio_id), None)
    if not studio:
        raise HTTPException(status_code=404, detail="Studio tidak ditemukan")

    # Update data jadwal
    jadwal["movie_id"] = updated_data.movie_id
    jadwal["movie_title"] = film["title"]
    jadwal["studio_id"] = updated_data.studio_id
    jadwal["studio_name"] = studio["name"]
    jadwal["date"] = updated_data.date
    jadwal["time"] = updated_data.time

    return {
        "message": f"Jadwal {schedule_id} berhasil diperbarui",
        "data": jadwal
    }

# DELETE - Hapus jadwal
@router.delete("/schedules/{schedule_id}")
def hapus_jadwal(schedule_id: str):
    for j in list_jadwal:
        if j.get("id_jadwal") == schedule_id:
            list_jadwal.remove(j)
            return {"message": f"Jadwal {schedule_id} berhasil dihapus"}
    raise HTTPException(status_code=404, detail="Jadwal tidak ditemukan")