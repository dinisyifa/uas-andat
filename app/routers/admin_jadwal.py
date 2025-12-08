from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Jadwal, Movie, Studio
from pydantic import BaseModel
from datetime import datetime, date, time # Import time juga

router = APIRouter(prefix="/schedules")


class ScheduleInput(BaseModel):
    movie_code: str
    studio_code: str
    tanggal: str
    jam: str # Tetap string untuk input

# ScheduleOut dan generate_schedule_code tidak berubah

class ScheduleOut(BaseModel):
    code: str
    movie_code: str
    studio_code: str
    tanggal: str 
    jam: str # Tetap string untuk output JSON
    movie_title: str
    studio_name: str

    class Config:
        orm_mode = True


def generate_schedule_code(db: Session):
    last = db.query(Jadwal).order_by(Jadwal.id.desc()).first()
    next_id = (last.id + 1) if last else 1
    return f"SCH{str(next_id).zfill(3)}"

@router.get("", response_model=list[ScheduleOut])
def get_schedules(db: Session = Depends(get_db)):
    """
    Mengambil daftar semua jadwal.
    """
    schedules = db.query(Jadwal).all()
    output = []

    for s in schedules:
        movie = db.query(Movie).filter(Movie.code == s.movie_code).first()
        studio = db.query(Studio).filter(Studio.code == s.studio_code).first()

        # Konversi objek date dari DB ke string
        tanggal_str = str(s.tanggal) if isinstance(s.tanggal, date) else str(s.tanggal) if s.tanggal else "-"
        # FIX 1: Konversi objek time dari DB ke string HH:MM:SS
        jam_str = str(s.jam) if isinstance(s.jam, time) else str(s.jam) if s.jam else "-"
        
        output.append(ScheduleOut(
            code=s.code,
            movie_code=s.movie_code,
            studio_code=s.studio_code,
            tanggal=tanggal_str, 
            jam=jam_str, # Menggunakan string untuk output
            movie_title=movie.title if movie else f"Unknown ({s.movie_code})",
            studio_name=studio.name if studio else f"Unknown ({s.studio_code})"
        ))

    return output

@router.post("", response_model=ScheduleOut)
def add_schedule(item: ScheduleInput, db: Session = Depends(get_db)):

    # Cek movie dan studio
    movie = db.query(Movie).filter(Movie.code == item.movie_code).first()
    if not movie:
        raise HTTPException(404, "Movie tidak ditemukan")

    studio = db.query(Studio).filter(Studio.code == item.studio_code).first()
    if not studio:
        raise HTTPException(404, "Studio tidak ditemukan")

    new_code = generate_schedule_code(db)
    
    # Konversi string tanggal ke objek date Python
    try:
        tanggal_obj = datetime.strptime(item.tanggal, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(400, "Format tanggal harus YYYY-MM-DD")
        
    # FIX 2: Konversi string jam ke objek time Python
    try:
        # Mencoba format jam: HH:MM:SS atau HH:MM (tergantung kebutuhan DB)
        time_format = "%H:%M:%S" if len(item.jam.split(':')) == 3 else "%H:%M"
        jam_obj = datetime.strptime(item.jam, time_format).time()
    except ValueError:
        raise HTTPException(400, "Format jam harus HH:MM atau HH:MM:SS")
    
    schedule = Jadwal(
        code=new_code,
        movie_code=item.movie_code,
        studio_code=item.studio_code,
        tanggal=tanggal_obj, 
        jam=jam_obj # Menggunakan objek time yang sudah dikonversi
    )

    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    # Output dikonversi kembali ke string (sesuai ScheduleOut)
    return ScheduleOut(
        code=schedule.code,
        movie_code=schedule.movie_code,
        studio_code=schedule.studio_code,
        tanggal=str(schedule.tanggal), 
        jam=str(schedule.jam), # Menggunakan str(time object) untuk output
        movie_title=movie.title,
        studio_name=studio.name
    )

@router.put("/{code}", response_model=ScheduleOut)
def update_schedule(code: str, item: ScheduleInput, db: Session = Depends(get_db)):

    schedule = db.query(Jadwal).filter(Jadwal.code == code).first()
    if not schedule:
        raise HTTPException(404, "Jadwal tidak ditemukan")

    movie = db.query(Movie).filter(Movie.code == item.movie_code).first()
    if not movie:
        raise HTTPException(404, "Movie tidak ditemukan")

    studio = db.query(Studio).filter(Studio.code == item.studio_code).first()
    if not studio:
        raise HTTPException(404, "Studio tidak ditemukan")

    # Konversi string tanggal ke objek date Python
    try:
        tanggal_obj = datetime.strptime(item.tanggal, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(400, "Format tanggal harus YYYY-MM-DD")
        
    # FIX 3: Konversi string jam ke objek time Python
    try:
        time_format = "%H:%M:%S" if len(item.jam.split(':')) == 3 else "%H:%M"
        jam_obj = datetime.strptime(item.jam, time_format).time()
    except ValueError:
        raise HTTPException(400, "Format jam harus HH:MM atau HH:MM:SS")
    
    schedule.movie_code = item.movie_code
    schedule.studio_code = item.studio_code
    schedule.tanggal = tanggal_obj 
    schedule.jam = jam_obj # Menggunakan objek time yang sudah dikonversi

    db.commit()
    db.refresh(schedule)

    # Output dikonversi kembali ke string
    return ScheduleOut(
        code=schedule.code,
        movie_code=schedule.movie_code,
        studio_code=schedule.studio_code,
        tanggal=str(schedule.tanggal),
        jam=str(schedule.jam), # Menggunakan str(time object) untuk output
        movie_title=movie.title,
        studio_name=studio.name
    )

@router.delete("/{code}")
def delete_schedule(code: str, db: Session = Depends(get_db)):

    schedule = db.query(Jadwal).filter(Jadwal.code == code).first()
    if not schedule:
        raise HTTPException(404, "Jadwal tidak ditemukan")

    db.delete(schedule)
    db.commit()

    return {"status": f"Jadwal {code} berhasil dihapus"}