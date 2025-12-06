# app/main.py
from fastapi import FastAPI
from app.routers import admin_film, user_transaction, admin_jadwal, user_catalog, user_transaction
from app.database import engine, Base
import app.models
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Movie Booking System",
    description="Proyek UAS",
    version="2.1.0"
)

# Admin
app.include_router(admin_film.router,  tags=["Admin - Film, Studio, dan Memberships"])
app.include_router(admin_jadwal.router, tags=["Admin - Jadwal"])

# User
app.include_router(user_catalog.router,     tags=["User - Katalog"])           
app.include_router(user_transaction.router, tags=["User - Cart & Checkout"])

# Analisis
app.include_router(analisis.router, tags=["Analisis Data"])

@app.get("/")
def home():
    return {
        "message": "Movie Booking API aktif (Admin & User)",
        "info": "Cek /docs untuk Swagger UI.",
    }