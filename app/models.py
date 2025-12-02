# app/models.py
# ==========================================
# Semua model data yang digunakan di sistem
# ==========================================

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ===============================
# MODEL UNTUK ADMIN FILM #ressy
# ===============================
class Movie(BaseModel):
    """
    Representasi data satu film yang dikelola oleh Admin.
    """
    id: str                 # contoh: "MOV001"
    title: str              # contoh: "Avengers: Endgame"
    duration: str           # contoh: "3h 20m"
    genre: str 
    sutradara: str
    rating_usia: str  # opsional (bisa diisi nanti)
    price: str              # contoh: 50000

# ===============================
# MODEL UNTUK STUDIO #ressy
# ===============================
class Studio(BaseModel):
    id: str          # contoh: "st1"
    name: str           # contoh: "Studio 1"
    capacity: Optional [int] = None

# ===============================
# MODEL UNTUK JADWAL PENAYANGAN #dini
# ===============================
class Seat(BaseModel):
    seat: str
    available: bool

class Schedule(BaseModel):
    """
    Representasi satu jadwal penayangan film di studio tertentu.
    """
    id_jadwal: Optional[str] = None
    movie_id: str
    studio_id: str
    date: str
    time: str
    movie_title: Optional[str] = None
    studio_name: Optional[str] = None
    seats: Optional[Any] = None


# ==================================
# MODEL UNTUK DETAIL FILM DI KATALOG (USER) #tiffany
# ==================================
class CatalogDetail(BaseModel):
    """
    Model untuk menampilkan detail film di katalog (user).
    """
    id: str
    title: str
    duration: str
    genre: str
    sutradara: str
    rating_usia: str
    price: str
    schedules: List[Schedule]  # daftar jadwal terkait film ini

# ==================================
# MODEL UNTUK DETAIL KURSI #tiffany
# ==================================
class SeatDetail(BaseModel):
    """
    Model untuk menampilkan detail kursi yang dipilih.
    """
    seat_number: str
    is_booked: bool
    user_id: Optional[str] = None

# ==================================
# MODEL UNTUK MANAJEMEN KERANJANG & TRANSAKSI (USER)
# ==================================
class CartAddItem(BaseModel):
    """
    Model untuk menambah item tiket ke keranjang.
    User cukup memasukkan informasi yang mudah diingat.
    """
    movie_title: str # = Field(..., description="Judul film yang ingin ditonton.", example="Avengers: Endgame")
    schedule_id : str   # = Field(..., description="Jam penayangan yang dipilih (format HH:MM).", example="19:00")
    seat_number: str # = Field(..., description="Nomor kursi yang dipilih.", example="A5")
# ==================================
class CartItemResponse(BaseModel):
    """
    Model untuk menampilkan item tiket di keranjang.
    """
    item_id: str          # ID unik item di keranjang (misal: "ITEM001")
    schedule_id: str
    movie_id: str
    movie_title: str
    schedule: str         # gabungan date + time (misal: "2023-10-01 19:00")
    studio: str
    seat_number: str
    price: int

# ==================================
# MODEL UNTUK DETAIL TRANSAKSI #lulu
# ==================================
class TransactionDetail(BaseModel):
    """
    Model untuk detail transaksi tiket.
    """
    transaction_id: str
    user_id: str
    schedule_id: str
    seats: List[str]
    total_price: int


# ===============================================
# MODEL BARU UNTUK ALUR CHECKOUT DUA LANGKAH
# ===============================================

class PaymentMethodRequest(BaseModel):
    """
    Model input dari user untuk memilih metode pembayaran.
    """
    payment_method: str = Field(..., description="Metode pembayaran yang dipilih", example="QRIS")

class PreTransactionResponse(BaseModel):
    """
    Model respons setelah user memilih metode pembayaran.
    Berisi ID pesanan sementara yang akan digunakan untuk konfirmasi.
    """
    order_id: str
    total_price: int
    payment_method: str
    expires_at: datetime # Menunjukkan kapan pesanan sementara ini akan batal
    tickets: List[CartItemResponse]