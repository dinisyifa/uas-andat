from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Movie, price
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

    class Config:
        orm_mode = True



def generate_movie_code(db: Session):
    last = db.query(Movie).order_by(Movie.id.desc()).first()
    next_id = (last.id + 1) if last else 1
    return f"MOV{str(next_id).zfill(3)}"


@router.get("/movies", response_model=list[MovieOut])
def get_movies(db: Session = Depends(get_db)):
    return db.query(Movie).all()


@router.post("/movies", response_model=MovieOut)
def add_movie(item: MovieInput, db: Session = Depends(get_db)):

    new_code = generate_movie_code(db)
    ticket_price = price(item.durasi)

    movie = Movie(
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
    return movie


@router.put("/movies/{code}", response_model=MovieOut)
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
    return movie


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
    name: str
    rows: int
    cols: int

    class Config:
        orm_mode = True




def generate_studio_code(db: Session):
    last = db.query(Studio).order_by(Studio.id.desc()).first()
    next_id = (last.id + 1) if last else 1
    return (
        f"ST{str(next_id).zfill(3)}",
        f"Studio {next_id}"
    )




@router.get("/studios", response_model=list[StudioOut])
def get_studios(db: Session = Depends(get_db)):
    return db.query(Studio).all()


@router.post("/studios", response_model=StudioOut)
def add_studio(item: StudioInput, db: Session = Depends(get_db)):

    code, name = generate_studio_code(db)

    studio = Studio(
        code=code,
        name=name,
        rows=item.rows,
        cols=item.cols
    )

    db.add(studio)
    db.commit()
    db.refresh(studio)
    return studio


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
    last = db.query(Membership).order_by(Membership.id.desc()).first()
    next_id = (last.id + 1) if last else 1
    return f"MEM{str(next_id).zfill(3)}"





@router.get("/members", response_model=list[MembershipOut])
def get_memberships(db: Session = Depends(get_db)):
    return db.query(Membership).all()


@router.post("/members", response_model=MembershipOut)
def add_membership(item: MembershipInput, db: Session = Depends(get_db)):

    new_code = generate_member_code(db)

    member = Membership(
        code=new_code,
        nama=item.nama
    )

    db.add(member)
    db.commit()
    db.refresh(member)
    return member


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