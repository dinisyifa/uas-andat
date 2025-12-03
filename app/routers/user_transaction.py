from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime
import uuid
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.models import Cart, Jadwal, Order, OrderSeat, Membership, Movie    

router = APIRouter()

# CART
class CartAddItem(BaseModel):
    membership_code: str
    jadwal_id: int
    row: str
    col: int

class CartItemResponse(BaseModel):
    cart_id: int
    movie_title: str
    studio_name: str
    date_time: str
    seat: str
    price: int

# CHECKOUT
class CheckoutRequest(BaseModel):
    membership_code: str
    payment_method: str # "QRIS", "Debit", "Cash", "ShopeePay", etc.
    cash_amount: Optional[int] = None

class OrderResponse(BaseModel):
    order_code: str
    total_seat: int
    final_price: int
    status: str


def check_seat_taken(db: Session, jadwal_id: int, row: str, col: int) -> bool:
    """Mengecek apakah kursi sudah ada di tabel OrderSeat (terjual)"""
    taken = db.query(OrderSeat).filter_by(
        jadwal_id=jadwal_id, 
        row=row, 
        col=col
    ).first()
    return taken is not None

# --- Routes ---

# CREATE CART
@router.post("/cart/add", response_model=CartAddItem)
def add_to_cart(item: CartAddItem, db: Session = Depends(get_db)):
    # 1. Validasi Jadwal
    jadwal = db.query(Jadwal).filter(Jadwal.id == item.jadwal_id).first()
    if not jadwal:
        raise HTTPException(404, "Jadwal tidak ditemukan")

    # 2. Validasi Member
    member = db.query(Membership).filter(Membership.code == item.membership_code).first()
    if not member:
        raise HTTPException(404, "Member tidak ditemukan")

    # 3. Cek apakah kursi sudah TERJUAL di OrderSeat
    if check_seat_taken(db, item.jadwal_id, item.row, item.col):
        raise HTTPException(400, "Kursi sudah terjual")

    # 4. Cek apakah kursi sudah ada di CART user sendiri (duplikat)
    existing_cart = db.query(Cart).filter_by(
        membership_code=item.membership_code,
        jadwal_id=item.jadwal_id,
        row=item.row,
        col=item.col
    ).first()
    
    if existing_cart:
        return {"message": "Kursi sudah ada di keranjang"}

    # 5. Tambah ke Cart
    # Ambil harga dari Movie
    movie_price = jadwal.movie.price
    
    new_item = Cart(
        membership_code=item.membership_code,
        jadwal_id=item.jadwal_id,
        row=item.row,
        col=item.col,
        price=movie_price
    )
    db.add(new_item)
    db.commit()
    
    return {"message": "Berhasil masuk keranjang", "seat": f"{item.row}{item.col}"}

# GET - Lihat isi keranjang
@router.get("/cart")
def get_all_carts(db: Session = Depends(get_db)):
    carts = db.query(Cart).all()
    return carts

# READ MEMBERSHIP CART
@router.get("/cart/{membership_code}")
def get_cart(membership_code: str, db: Session = Depends(get_db)):
    items = db.query(Cart).filter(Cart.membership_code == membership_code).all()
    
    if not items:
        return {"message": "Keranjang kosong", "items": [], "total": 0}

    result = []
    total = 0
    for i in items:
        # Format tanggal & jam
        dt_str = f"{i.jadwal.tanggal} {i.jadwal.jam}"
        seat_str = f"{i.row}-{i.col}"
        
        result.append({
            "cart_id": i.id,
            "movie_title": i.jadwal.movie.title,
            "studio_name": i.jadwal.studio.name,
            "date_time": dt_str,
            "seat": seat_str,
            "price": i.price
        })
        total += i.price

    return {"items": result, "total_price": total}

# DELETE CART ITEM
@router.delete("/cart/remove/{cart_id}")
def remove_cart_item(cart_id: int, db: Session = Depends(get_db)):
    item = db.query(Cart).filter(Cart.id == cart_id).first()
    if not item:
        raise HTTPException(404, "Item cart tidak ditemukan")
    
    db.delete(item)
    db.commit()
    return {"message": "Item dihapus dari keranjang"}

# CREATE CHECKOUT
@router.post("/checkout", response_model=OrderResponse)
def checkout_cart(payload: CheckoutRequest, db: Session = Depends(get_db)):
    # 1. Ambil semua item di cart user
    cart_items = db.query(Cart).filter(Cart.membership_code == payload.membership_code).all()
    if not cart_items:
        raise HTTPException(400, "Keranjang kosong")

    # 2. Validasi Ketersediaan Kursi (Last Minute Check)
    # Jika saat user memilih kursi masih kosong, tapi saat checkout sudah dibeli orang lain
    for item in cart_items:
        if check_seat_taken(db, item.jadwal_id, item.row, item.col):
             raise HTTPException(409, f"Gagal: Kursi {item.row}-{item.col} baru saja dibeli orang lain.")

    # 3. Hitung Total & Promo
    member = db.query(Membership).filter(Membership.code == payload.membership_code).first()
    
    total_price = sum(item.price for item in cart_items)
    seat_count = len(cart_items)
    
    # Logika promo sederhana (sesuai kode Anda sebelumnya)
    discount = 0
    promo_name = "NO PROMO"
    
    # Contoh promo bulk buy
    if seat_count >= 5:
        promo_name = "BULK 5+"
        discount = 20 # 20%
    
    discount_amount = int(total_price * discount / 100)
    final_price = total_price - discount_amount

    # Hitung kembalian jika Cash
    change = 0
    if payload.payment_method.upper() == "CASH":
        if not payload.cash_amount or payload.cash_amount < final_price:
            raise HTTPException(400, "Uang tunai kurang")
        change = payload.cash_amount - final_price
    else:
        payload.cash_amount = final_price # Asumsi uang pas untuk non-tunai

    # 4. Buat Order Baru
    first_item = cart_items[0]
    jadwal = first_item.jadwal
    
    # Generate Order Code
    order_code_suffix = uuid.uuid4().hex[:6].upper()
    order_code = f"ORD-{order_code_suffix}"
    
    # Mapping nama hari
    days = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    today_day = days[datetime.now().weekday()]

    new_order = Order(
        code=order_code,
        membership_id=member.id,
        membership_code=member.code,
        jadwal_id=jadwal.id,
        payment_method=payload.payment_method,
        seat_count=seat_count,
        promo_name=promo_name,
        discount=discount,
        total_price=total_price,
        final_price=final_price,
        cash=payload.cash_amount,
        change=change,
        transaction_date=datetime.now().date(),
        hari=today_day
    )
    db.add(new_order)
    db.flush() # Flush untuk mendapatkan ID Order

    # 5. Pindahkan Cart -> OrderSeat
    for item in cart_items:
        order_seat = OrderSeat(
            order_id=new_order.id,
            jadwal_id=item.jadwal_id,
            studio_id=jadwal.studio_id,
            row=item.row,
            col=item.col
        )
        db.add(order_seat)
    
    # 6. Kosongkan Cart User
    for item in cart_items:
        db.delete(item)

    db.commit()

    return {
        "order_code": order_code,
        "total_seat": seat_count,
        "final_price": final_price,
        "status": "SUCCESS"
    }

# READ KONFIRMASI CHECKOUT
@router.get("/order/{order_code}", response_model=OrderResponse)
def get_order(order_code: str, db: Session = Depends(get_db)):  
    order = db.query(Order).filter(Order.code == order_code).first()
    if not order:
        raise HTTPException(404, "Order tidak ditemukan")
    
    return {
        "order_code": order.code,
        "total_seat": order.seat_count,
        "final_price": order.final_price,
        "status": f"Pesanan `{order.code}` berhasil diproses"
    }

# DELETE CART ITEM
@router.delete("/cart/remove/{cart_id}")
def remove_cart_item(cart_id: int, db: Session = Depends(get_db)):
    item = db.query(Cart).filter(Cart.id == cart_id).first()
    if not item:
        raise HTTPException(404, "Pesanan tidak ditemukan")
    
    db.delete(item)
    db.commit()
    return {"message": "Item cart berhasil dihapus"}        

