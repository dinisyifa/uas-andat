from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime
import uuid
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.models import Cart, Jadwal, Order, OrderSeat, Membership, Movie, StudioSeat, Studio  

router = APIRouter()

# CART
class CartAddItem(BaseModel):
    membership_code: str
    jadwal_code: str
    row: str
    col: int

class CartAddResponse(BaseModel):
    message: str
    data: CartAddItem  # Menampilkan kembali data yang diinput

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
    change: int         
    status: str
    message: str         


def check_seat_taken(db: Session, jadwal_id: int, row: str, col: int) -> bool:
    """Mengecek apakah kursi sudah ada di tabel OrderSeat (terjual)"""
    taken = db.query(OrderSeat).filter_by(
        jadwal_id=jadwal_id, 
        row=row, 
        col=col
    ).first()
    return taken is not None

# --- Routes ---

@router.post("/cart/add", response_model=CartAddResponse)
def add_to_cart(item: CartAddItem, db: Session = Depends(get_db)):
    # 1. Cari Data JADWAL Asli berdasarkan KODE yang diinput user
    jadwal = db.query(Jadwal).filter(Jadwal.code == item.jadwal_code).first()
    if not jadwal:
        raise HTTPException(404, detail=f"Jadwal dengan kode {item.jadwal_code} tidak ditemukan")

    # 2. Cari Data MEMBER Asli berdasarkan KODE yang diinput user
    member = db.query(Membership).filter(Membership.code == item.membership_code).first()
    if not member:
        raise HTTPException(404, detail=f"Member dengan kode {item.membership_code} tidak ditemukan")

    # 3. Validasi Kursi (Apakah sudah dibeli orang lain?)
    if check_seat_taken(db, jadwal.id, item.row, item.col):
        raise HTTPException(400, detail="Kursi sudah terjual")

    # 4. Validasi Duplikat (Apakah user ini sudah memasukkan kursi ini ke keranjang?)
    existing_cart = db.query(Cart).filter(
        Cart.membership_id == member.id,
        Cart.jadwal_id == jadwal.id,
        Cart.row == item.row,
        Cart.col == item.col
    ).first()
    
    if existing_cart:
        # Jika sudah ada, kembalikan saja sukses (agar tidak error di frontend)
        return {
        "message": "Tiket sudah ada di keranjang",
        "data": item
    }

    # 5. Ambil Harga Film secara Manual
    # (Kita query ke tabel Movie pakai jadwal.movie_id)
    movie = db.query(Movie).filter(Movie.id == jadwal.movie_id).first()
    movie_price = movie.price if movie else 0
    
    # 6. SIMPAN KE DATABASE (Mapping dari Code -> ID)
    new_item = Cart(
        # Data Member
        membership_id=member.id,       # Simpan ID (Integer)
        membership_code=member.code,   # Simpan Code (String) dari database, bukan input (lebih aman)
        
        # Data Jadwal
        jadwal_id=jadwal.id,           # Simpan ID Jadwal (Integer)
        
        # Data Studio & Harga (PENTING AGAR TIDAK ERROR 500)
        studio_id=jadwal.studio_id,    # Ambil dari object jadwal
        price=movie_price,             # Ambil dari object movie
        
        # Data Kursi
        row=item.row,
        col=item.col
    )
    
    db.add(new_item)
    db.commit()
    db.refresh(new_item) # Opsional: memastikan data tersimpan dan memiliki ID
    
    return {
        "message": "Tiket berhasil ditambahkan",
        "data": item
    }

# GET - Lihat isi keranjang
@router.get("/cart")
def get_all_carts(db: Session = Depends(get_db)):
    carts = db.query(Cart).all()
    return carts

# READ MEMBERSHIP CART
@router.get("/cart/{membership_code}")
def get_cart(membership_code: str, db: Session = Depends(get_db)):
    # 1. Ambil Cart Items
    items = db.query(Cart).filter(Cart.membership_code == membership_code).all()
    
    if not items:
        return {"message": "Keranjang kosong", "items": [], "total": 0}

    result = []
    total = 0
    
    for i in items:
        # 2. Query Manual Jadwal
        jadwal = db.query(Jadwal).filter(Jadwal.id == i.jadwal_id).first()
        if not jadwal: continue

        # 3. Query Manual Movie & Studio 
        # (INI YANG TADINYA ERROR KARENA 'Studio' BELUM DIIMPORT)
        movie = db.query(Movie).filter(Movie.id == jadwal.movie_id).first()
        studio = db.query(Studio).filter(Studio.id == jadwal.studio_id).first()
        
        movie_title = movie.title if movie else "Unknown Movie"
        studio_name = studio.name if studio else "Unknown Studio"
        
        dt_str = f"{jadwal.tanggal} {jadwal.jam}"
        seat_str = f"{i.row}-{i.col}"
        
        result.append({
            "cart_id": i.id,
            "movie_title": movie_title,
            "studio_name": studio_name,
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

@router.post("/checkout", response_model=OrderResponse)
def checkout_cart(payload: CheckoutRequest, db: Session = Depends(get_db)):
    # 1. Ambil cart
    cart_items = db.query(Cart).filter(Cart.membership_code == payload.membership_code).all()
    if not cart_items:
        raise HTTPException(400, "Keranjang kosong")

    # 2. Cek ketersediaan lagi
    for item in cart_items:
        if check_seat_taken(db, item.jadwal_id, item.row, item.col):
             raise HTTPException(409, detail=f"Gagal: Kursi {item.row}-{item.col} baru saja dibeli orang lain.")

    # 3. Hitung Total
    member = db.query(Membership).filter(Membership.code == payload.membership_code).first()
    
    total_price = sum(item.price for item in cart_items)
    seat_count = len(cart_items)
    
    # 4. Promo Logic
    discount = 0
    promo_name = "NO PROMO"
    if seat_count >= 5:
        promo_name = "BULK 5+"
        discount = 20 
    
    discount_amount = int(total_price * discount / 100)
    final_price = total_price - discount_amount

    # 5. Payment Logic
    change = 0
    status_message = "Menunggu Pembayaran" # Default
    custom_message = "Transaksi Berhasil"  # Default

    if payload.payment_method.upper() == "CASH":
        # Jika cash_amount null, anggap 0
        user_cash = payload.cash_amount if payload.cash_amount else 0
        
        # Cek jika uang kurang
        if user_cash < final_price:
            kurang = final_price - user_cash
            raise HTTPException(400, detail=f"Uang tunai kurang Rp {kurang}")
        
        # Hitung Kembalian
        change = user_cash - final_price
        
        # Buat Pesan Khusus Kembalian
        if change > 0:
            custom_message = f"Pembayaran Lunas. Kembalian Anda: Rp {change}"
        else:
            custom_message = "Pembayaran Lunas. Uang Pas."
            
        status_message = "PAID"

    else:
        # Non-tunai (QRIS/Debit) dianggap pas
        payload.cash_amount = final_price
        change = 0
        custom_message = f"Pembayaran {payload.payment_method} Berhasil"
        status_message = "PAID"

    # 6. Buat Order Baru
    first_item = cart_items[0]
    # Query manual Jadwal, jangan pakai first_item.jadwal
    jadwal = db.query(Jadwal).filter(Jadwal.id == first_item.jadwal_id).first()
    
    if not jadwal:
        raise HTTPException(404, "Data jadwal korup/hilang")
    
    order_code_suffix = uuid.uuid4().hex[:6].upper()
    order_code = f"ORD-{order_code_suffix}"
    
    days = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    today_day = days[datetime.now().weekday()]

    new_order = Order(
        code=order_code,
        membership_id=member.id,
        membership_code=member.code,
        
        jadwal_id=jadwal.id,
        jadwal_code=jadwal.code, # Pastikan kolom ini ada di models Order
        
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
    db.flush() # Flush untuk dapatkan new_order.id

    # 7. Pindahkan Cart -> OrderSeat
    for item in cart_items:       
        order_seat = OrderSeat(
            order_id=new_order.id,
            jadwal_id=item.jadwal_id,
            studio_id=item.studio_id, # Ambil langsung dari Cart
            row=item.row,
            col=item.col
        )
        db.add(order_seat)
    
    # 8. Hapus Cart
    for item in cart_items:
        db.delete(item)

    db.commit()

    # --- FIXED RETURN STATEMENT ---
    return {
        "order_code": order_code,
        "total_seat": seat_count,
        "final_price": final_price,
        "change": change,           # Added
        "status": status_message,   # Added
        "message": custom_message   # Added
    }

# READ KONFIRMASI CHECKOUT
@router.get("/order/{order_code}", response_model=OrderResponse)
def get_order(order_code: str, db: Session = Depends(get_db)):  
    order = db.query(Order).filter(Order.code == order_code).first()
    if not order:
        raise HTTPException(404, "Order tidak ditemukan")
    
    # Logic to recreate message since it's not stored directly in DB usually
    # Or just return a generic message
    msg = "Transaksi Berhasil"
    if order.change and order.change > 0:
        msg = f"Kembalian: Rp {order.change}"
    
    return {
        "order_code": order.code,
        "total_seat": order.seat_count,
        "final_price": order.final_price,
        "change": order.change if order.change else 0, # Ensure int
        "status": "PAID", # Assuming successful orders are paid
        "message": msg
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
