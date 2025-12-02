from fastapi import APIRouter, HTTPException
from app.models import Movie, Studio

router = APIRouter()

# Database film
list_film = [{"id": "mov1", "title": "Avengers: Endgame", "duration": "200 menit", "genre": "Action, Fantasy", "sutradara": "Anthony Russo, Joe Russo", "rating_usia": "PG-13", "price": "Rp40.000"},
{"id": "mov2", "title": "The Conjuring", "duration": "120 menit", "genre": "Horror, Mystery", "sutradara": "James Wan", "rating_usia": "17+", "price": "Rp40.000"},
{"id": "mov3", "title": "Frozen", "duration": "130 menit", "genre": "Family, Musical", "sutradara": "Jennifer Lee, Chris Buck", "rating_usia": "PG", "price": "Rp40.000"},
{"id": "mov4", "title": "Komang", "duration": "130 menit", "genre": "Drama, Romance", "sutradara": "Naya Anindita", "rating_usia": "13+", "price": "Rp40.000"}
]

# =============================================== API FILM ================================================

# CREATE - Tambah Film
@router.post("/movies")
def tambah_film(movie: Movie):
    # Cek apakah ID film sudah ada
    for f in list_film:
        if f["id"] == movie.id:
            raise HTTPException(status_code=400, detail="ID film sudah ada")
    list_film.append(movie.dict())
    return {"message": "Film berhasil ditambahkan", "data": movie}

# READ - Lihat semua film
@router.get("/movies")
def lihat_semua_film():
    if not list_film:
        raise HTTPException(status_code=404, detail="Belum ada film yang terdaftar")
    return {"message": "Daftar semua film berhasil diambil", "data": list_film}

# READ - Lihat satu film
@router.get("/movies/{movie_id}")
def lihat_detail_film(movie_id: str):
    for film in list_film:
        if film["id"] == movie_id:
            return {"message": "Detail film ditemukan", "data": film}
    raise HTTPException(status_code=404, detail="Film tidak ditemukan")

# UPDATE - Perbarui film
@router.put("/movies/{movie_id}")
def perbarui_film(movie_id: str, movie: Movie):
    for idx, film in enumerate(list_film):
        if film["id"] == movie_id:
            list_film[idx] = movie.dict()
            return {"message": "Data film berhasil diperbarui", "data": movie}
    raise HTTPException(status_code=404, detail="Film tidak ditemukan")

# DELETE - Hapus film
@router.delete("/movies/{movie_id}")
def hapus_film(movie_id: str):
    for idx, film in enumerate(list_film):
        if film["id"] == movie_id:
            del list_film[idx]
            return {"message": f"Film dengan ID {movie_id} berhasil dihapus"}
    raise HTTPException(status_code=404, detail="Film tidak ditemukan")


# =============================================== API STUDIO ================================================

# Database Studio
list_studio = [
    {"id": "st1", "name": "Studio 1", "capacity": 96},
    {"id": "st2", "name": "Studio 2", "capacity": 96},
    {"id": "st3", "name": "Studio 3", "capacity": 96},
    {"id": "st4", "name": "Studio 4", "capacity": 96},
]


# CREATE - Tambah Studio
@router.post("/studios")
def tambah_studio(studio: Studio):
    # Cek apakah ID sudah ada
    for st in list_studio:
        if st["id"] == studio.id:
            raise HTTPException(status_code=400, detail="ID studio sudah ada")

    list_studio.append(studio.dict())
    return {"message": "Studio berhasil ditambahkan", "data": studio}

# READ - Lihat semua Studio
@router.get("/studios")
def lihat_semua_studio():
    if not list_studio:
        raise HTTPException(status_code=404, detail="Belum ada studio yang terdaftar")
    return {"message": "Daftar semua studio berhasil diambil", "data": list_studio}

# READ - Lihat satu Studio
@router.get("/studios/{studio_id}")
def lihat_detail_studio(studio_id: str):
    for st in list_studio:
        if st["id"] == studio_id:
            return {"message": "Detail studio ditemukan", "data": st}
    raise HTTPException(status_code=404, detail="Studio tidak ditemukan")

# UPDATE - Perbarui Studio
@router.put("/studios/{studio_id}")
def perbarui_studio(studio_id: str, studio: Studio):
    for idx, st in enumerate(list_studio):
        if st["id"] == studio_id:
            list_studio[idx] = studio.dict()
            return {"message": "Data studio berhasil diperbarui", "data": studio}
    raise HTTPException(status_code=404, detail="Studio tidak ditemukan")

# DELETE - Hapus Studio
@router.delete("/studios/{studio_id}")
def hapus_studio(studio_id: str):
    for idx, st in enumerate(list_studio):
        if st["id"] == studio_id:
            del list_studio[idx]
            return {"message": f"Studio dengan ID {studio_id} berhasil dihapus"}
    raise HTTPException(status_code=404, detail="Studio tidak ditemukan")