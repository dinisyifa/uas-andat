from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.models import Movie, Studio, Membership, Session, engine

router = APIRouter()
session = Session()


# pydantic schemas
class MovieInput(BaseModel):
    code: str
    title: str
    genre: str
    durasi: int
    director: str
    rating: str
    price: int

class StudioInput(BaseModel):
    code: str
    name: str
    rows: int
    cols: int

class MembershipInput(BaseModel):
    code: str
    nama: str


# film
@router.get("/movies")
def get_movies():
    data = session.query(Movie).all()
    return data

@router.post("/movies")
def add_movie(item: MovieInput):
    m = Movie(**item.dict())
    session.add(m)
    try:
        session.commit()
        return {"status": "Movie ditambahkan", "movie": item}
    except:
        session.rollback()
        raise HTTPException(status_code=400, detail="Gagal menambahkan movie (kode mungkin sudah ada)")

@router.put("/movies/{movie_id}")
def update_movie(movie_id: int, item: MovieInput):
    m = session.query(Movie).filter_by(id=movie_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Movie tidak ditemukan")

    for key, val in item.dict().items():
        setattr(m, key, val)

    session.commit()
    return {"status": "Movie berhasil diupdate"}

@router.delete("/movies/{movie_id}")
def delete_movie(movie_id: int):
    m = session.query(Movie).filter_by(id=movie_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Movie tidak ditemukan")

    session.delete(m)
    session.commit()
    return {"status": "Movie berhasil dihapus"}




# studio
@router.get("/studios")
def get_studios():
    return session.query(Studio).all()

@router.post("/studios")
def add_studio(item: StudioInput):
    s = Studio(**item.dict())
    session.add(s)
    try:
        session.commit()
        return {"status": "Studio ditambahkan"}
    except:
        session.rollback()
        raise HTTPException(status_code=400, detail="Gagal menambahkan studio")

@router.put("/studios/{studio_id}")
def update_studio(studio_id: int, item: StudioInput):
    s = session.query(Studio).filter_by(id=studio_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Studio tidak ditemukan")

    for key, val in item.dict().items():
        setattr(s, key, val)

    session.commit()
    return {"status": "Studio berhasil diupdate"}

@router.delete("/studios/{studio_id}")
def delete_studio(studio_id: int):
    s = session.query(Studio).filter_by(id=studio_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Studio tidak ditemukan")

    session.delete(s)
    session.commit()
    return {"status": "Studio berhasil dihapus"}




# memberships
@router.get("/memberships")
def get_memberships():
    return session.query(Membership).all()

@router.post("/memberships")
def add_member(item: MembershipInput):
    m = Membership(**item.dict())
    session.add(m)
    try:
        session.commit()
        return {"status": "Membership ditambahkan"}
    except:
        session.rollback()
        raise HTTPException(status_code=400, detail="Gagal menambahkan membership")

@router.put("/memberships/{member_id}")
def update_member(member_id: int, item: MembershipInput):
    m = session.query(Membership).filter_by(id=member_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Membership tidak ditemukan")

    for key, val in item.dict().items():
        setattr(m, key, val)

    session.commit()
    return {"status": "Membership berhasil diupdate"}

@router.delete("/memberships/{member_id}")
def delete_member(member_id: int):
    m = session.query(Membership).filter_by(id=member_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Membership tidak ditemukan")

    session.delete(m)
    session.commit()
    return {"status": "Membership berhasil dihapus"}
