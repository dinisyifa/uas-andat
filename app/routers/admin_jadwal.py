from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Jadwal, Movie, Studio
from pydantic import BaseModel

router = APIRouter(prefix="/schedules")


class ScheduleInput(BaseModel):
    movie_code: str
    studio_code: str
    tanggal: str
    jam: str


class ScheduleOut(BaseModel):
    code: str
    movie_code: str
    studio_code: str
    tanggal: str
    jam: str
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
    Mengambil daftar semua jadwal dengan Query Manual yang aman (tanpa bergantung pada FK di DB).
    """
    schedules = db.query(Jadwal).all()
    output = []

    for s in schedules:
        movie = db.query(Movie).filter(Movie.code == s.movie_code).first()
        studio = db.query(Studio).filter(Studio.code == s.studio_code).first()

        tanggal_str = str(s.tanggal) if s.tanggal else "-"
        jam_str = str(s.jam) if s.jam else "-"
        
        output.append(ScheduleOut(
            code=s.code,
            movie_code=s.movie_code,
            studio_code=s.studio_code,
            tanggal=tanggal_str,
            jam=jam_str,
            movie_title=movie.title if movie else f"Unknown ({s.movie_code})",
            studio_name=studio.name if studio else f"Unknown ({s.studio_code})"
        ))

    return output


@router.post("", response_model=ScheduleOut)
def add_schedule(item: ScheduleInput, db: Session = Depends(get_db)):

    movie = db.query(Movie).filter(Movie.code == item.movie_code).first()
    if not movie:
        raise HTTPException(404, "Movie tidak ditemukan")

    studio = db.query(Studio).filter(Studio.code == item.studio_code).first()
    if not studio:
        raise HTTPException(404, "Studio tidak ditemukan")

    new_code = generate_schedule_code(db)

    schedule = Jadwal(
        code=new_code,
        movie_code=item.movie_code,
        studio_code=item.studio_code,
        tanggal=item.tanggal,
        jam=item.jam
    )

    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    return ScheduleOut(
        code=schedule.code,
        movie_code=schedule.movie_code,
        studio_code=schedule.studio_code,
        tanggal=schedule.tanggal,
        jam=schedule.jam,
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

    schedule.movie_code = item.movie_code
    schedule.studio_code = item.studio_code
    schedule.tanggal = item.tanggal
    schedule.jam = item.jam

    db.commit()
    db.refresh(schedule)

    return ScheduleOut(
        code=schedule.code,
        movie_code=schedule.movie_code,
        studio_code=schedule.studio_code,
        tanggal=schedule.tanggal,
        jam=schedule.jam,
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