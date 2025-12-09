from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Movie, price, Membership, Studio
from pydantic import BaseModel

router = APIRouter()

# MOVIE
class MovieInput(BaseModel):
    title: str
    genre: str
    durasi: int
    director: str
    rating: str

class MovieOut(BaseModel):
    code: str
    title: str
    genre: str
    durasi: int
    director: str
    rating: str
    price: int

class MovieResponse(BaseModel):
    message: str
    data: MovieOut

    class Config:
        orm_mode = True



def generate_movie_code(db: Session):
    last_id = db.query(func.max(Movie.id)).scalar()

    next_id = (last_id + 1) if last_id else 1

    return next_id, f"MOV{str(next_id).zfill(3)}"


@router.get("/movies")
def get_movies(db: Session = Depends(get_db)):
    movies = db.query(Movie).all()
    return {
        "message": "Daftar Film yang tersedia",
        "data": movies
    }


@router.post("/movies")
def add_movie(item: MovieInput, db: Session = Depends(get_db)):

    next_id, new_code = generate_movie_code(db)
    ticket_price = price(item.durasi)

    movie = Movie(
        id=next_id,
        code=new_code,
        title=item.title,
        genre=item.genre,
        durasi=item.durasi,
        director=item.director,
        rating=item.rating,
        price=ticket_price
    )

    db.add(movie)
    db.commit()
    db.refresh(movie)

    return {
        "message": "Film berhasil ditambahkan",
        "data": movie
    }




@router.put("/movies/{code}", response_model=MovieResponse)
def update_movie(code: str, item: MovieInput, db: Session = Depends(get_db)):

    movie = db.query(Movie).filter(Movie.code == code).first()
    if not movie:
        raise HTTPException(404, "Movie tidak ditemukan")

    movie.title = item.title
    movie.genre = item.genre
    movie.durasi = item.durasi
    movie.director = item.director
    movie.rating = item.rating
    movie.price = price(item.durasi)

    db.commit()
    db.refresh(movie)
    return {
        "message": "Film berhasil diperbarui",
        "data": movie
    }


@router.delete("/movies/{code}")
def delete_movie(code: str, db: Session = Depends(get_db)):

    movie = db.query(Movie).filter(Movie.code == code).first()
    if not movie:
        raise HTTPException(404, "Movie tidak ditemukan")

    db.delete(movie)
    db.commit()
    return {"status": f"Movie {code} berhasil dihapus"}

# STUDIO
class StudioInput(BaseModel):
    rows: int
    cols: int

class StudioOut(BaseModel):
    code: str
    nama: str
    rows: int
    cols: int

    class Config:
        orm_mode = True




def generate_studio_code(db: Session):
    last_id = db.query(func.max(Studio.id)).scalar()
    next_id = (last_id + 1) if last_id else 1

    return next_id, f"ST{str(next_id).zfill(3)}", f"Studio {next_id}"



@router.get("/studios")
def get_studios(db: Session = Depends(get_db)):
    studios = db.query(Studio).all()
    return {
        "message": "Daftar Studio yang tersedia",
        "data": studios
    }


@router.post("/studios")
def add_studio(item: StudioInput, db: Session = Depends(get_db)):

    next_id, code, nama = generate_studio_code(db)

    studio = Studio(
        id=next_id,       
        code=code,
        nama=nama,
        rows=item.rows,
        cols=item.cols
    )

    db.add(studio)
    db.commit()
    db.refresh(studio)

    return {
        "message": "Studio berhasil ditambahkan",
        "data": studio
    }


@router.put("/studios/{code}", response_model=StudioOut)
def update_studio(code: str, item: StudioInput, db: Session = Depends(get_db)):

    studio = db.query(Studio).filter(Studio.code == code).first()
    if not studio:
        raise HTTPException(404, "Studio tidak ditemukan")

    studio.rows = item.rows
    studio.cols = item.cols

    db.commit()
    db.refresh(studio)
    return studio


@router.delete("/studios/{code}")
def delete_studio(code: str, db: Session = Depends(get_db)):

    studio = db.query(Studio).filter(Studio.code == code).first()
    if not studio:
        raise HTTPException(404, "Studio tidak ditemukan")

    db.delete(studio)
    db.commit()
    return {"status": f"Studio {code} berhasil dihapus"}

# MEMBERSHIPS
class MembershipInput(BaseModel):
    nama: str

class MembershipOut(BaseModel):
    code: str
    nama: str

    class Config:
        orm_mode = True




def generate_member_code(db: Session):
    last_id = db.query(func.max(Membership.id)).scalar()
    next_id = (last_id + 1) if last_id else 1
    return next_id, f"MEM{str(next_id).zfill(3)}"



@router.get("/members")
def get_memberships(db: Session = Depends(get_db)):
    members = db.query(Membership).all()
    return {
        "message": "Daftar Membership yang tersedia",
        "data": members
    }



@router.post("/members")
def add_membership(item: MembershipInput, db: Session = Depends(get_db)):

    next_id, new_code = generate_member_code(db)

    member = Membership(
        id=next_id,     
        code=new_code,
        nama=item.nama
    )

    db.add(member)
    db.commit()
    db.refresh(member)

    return {
        "message": "Membership berhasil ditambahkan",
        "data": member
    }


@router.put("/members/{code}", response_model=MembershipOut)
def update_membership(code: str, item: MembershipInput, db: Session = Depends(get_db)):

    member = db.query(Membership).filter(Membership.code == code).first()
    if not member:
        raise HTTPException(404, "Membership tidak ditemukan")

    member.nama = item.nama

    db.commit()
    db.refresh(member)
    return member


@router.delete("/members/{code}")
def delete_membership(code: str, db: Session = Depends(get_db)):

    member = db.query(Membership).filter(Membership.code == code).first()
    if not member:
        raise HTTPException(404, "Membership tidak ditemukan")

    db.delete(member)
    db.commit()
    return {"status": f"Membership {code} berhasil dihapus"}