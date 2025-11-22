# app/main.py
from fastapi import FastAPI
from app.routers import admin_film, admin_jadwal, user_catalog, user_transaction

description = """
Sistem ini menyediakan serangkaian endpoint untuk mengelola seluruh alur pemesanan tiket bioskop secara digital, dengan modul utama:

* **Admin**: Mengelola data film, studio, dan jadwal tayang.
* **User**: Melihat katalog film, memesan tiket, dan melihat riwayat transaksi.
"""

app = FastAPI(
    title="Movie Booking System",
    description=description,
    version="1.2.0"
)

# Admin
app.include_router(admin_film.router,  tags=["Admin - Film & Studio"])
app.include_router(admin_jadwal.router, tags=["Admin - Jadwal"])

# User
app.include_router(user_catalog.router,     tags=["User - Katalog"])           
app.include_router(user_transaction.router, tags=["User - Cart & Checkout"])

@app.get("/")
def home():
    return {
        "message": "Movie Booking API aktif (Admin & User)",
        "info": "Cek /docs untuk Swagger UI.",
    }
