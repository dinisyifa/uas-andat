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
    data: CartAddItem  

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
    payment_method: str 
    cash_amount: Optional[int] = None

class OrderResponse(BaseModel):
    order_code: str
    total_seat: int
    final_price: int
    change: int         
    status: str
    message: str         


def check_seat_taken(db: Session, jadwal_id: int, row: str, col: int) -> bool:
    taken = db.query(OrderSeat).filter_by(
        jadwal_id=jadwal_id, 
        row=row, 
        col=col
    ).first()
    return taken is not None


@router.post("/cart/add", response_model=CartAddResponse)
def add_to_cart(item: CartAddItem, db: Session = Depends(get_db)):

    jadwal = db.query(Jadwal).filter(Jadwal.code == item.jadwal_code).first()
    if not jadwal:
        raise HTTPException(404, detail=f"Jadwal dengan kode {item.jadwal_code} tidak ditemukan")

    member = db.query(Membership).filter(Membership.code == item.membership_code).first()
    if not member:
        raise HTTPException(404, detail=f"Member dengan kode {item.membership_code} tidak ditemukan")

    if check_seat_taken(db, jadwal.id, item.row, item.col):
        raise HTTPException(400, detail="Kursi sudah terjual")

    existing_cart = db.query(Cart).filter(
        Cart.membership_id == member.id,
        Cart.jadwal_id == jadwal.id,
        Cart.row == item.row,
        Cart.col == item.col
    ).first()
    
    if existing_cart:
        return {
        "message": "Tiket sudah ada di keranjang",
        "data": item
    }

    movie = db.query(Movie).filter(Movie.id == jadwal.movie_id).first()
    movie_price = movie.price if movie else 0
    

    new_item = Cart(
        membership_id=member.id,       
        membership_code=member.code,   
        
        jadwal_id=jadwal.id,           
        
        studio_id=jadwal.studio_id,    
        price=movie_price,             
        
        row=item.row,
        col=item.col
    )
    
    db.add(new_item)
    db.commit()
    db.refresh(new_item) 
    
    return {
        "message": "Tiket berhasil ditambahkan",
        "data": item
    }

# READ MEMBERSHIP CART
@router.get("/cart/{membership_code}")
def get_cart(membership_code: str, db: Session = Depends(get_db)):
    items = db.query(Cart).filter(Cart.membership_code == membership_code).all()
    
    if not items:
        return {"message": "Keranjang kosong", "items": [], "total": 0}

    result = []
    total = 0
    
    for i in items:

        jadwal = db.query(Jadwal).filter(Jadwal.id == i.jadwal_id).first()
        if not jadwal: continue

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

    cart_items = db.query(Cart).filter(Cart.membership_code == payload.membership_code).all()
    if not cart_items:
        raise HTTPException(400, "Keranjang kosong")

    for item in cart_items:
        if check_seat_taken(db, item.jadwal_id, item.row, item.col):
             raise HTTPException(409, detail=f"Gagal: Kursi {item.row}-{item.col} baru saja dibeli orang lain.")

    member = db.query(Membership).filter(Membership.code == payload.membership_code).first()
    
    total_price = sum(item.price for item in cart_items)
    seat_count = len(cart_items)
    
    discount = 0
    promo_name = "NO PROMO"
    if seat_count >= 5:
        promo_name = "BULK 5+"
        discount = 20 
    
    discount_amount = int(total_price * discount / 100)
    final_price = total_price - discount_amount

    change = 0
    status_message = "Menunggu Pembayaran" 
    custom_message = "Transaksi Berhasil"  

    if payload.payment_method.upper() == "CASH":
        user_cash = payload.cash_amount if payload.cash_amount else 0
        
        if user_cash < final_price:
            kurang = final_price - user_cash
            raise HTTPException(400, detail=f"Uang tunai kurang Rp {kurang}")
        
        change = user_cash - final_price
        
        if change > 0:
            custom_message = f"Pembayaran Lunas. Kembalian Anda: Rp {change}"
        else:
            custom_message = "Pembayaran Lunas. Uang Pas."
            
        status_message = "PAID"

    else:

        payload.cash_amount = final_price
        change = 0
        custom_message = f"Pembayaran {payload.payment_method} Berhasil"
        status_message = "PAID"

    first_item = cart_items[0]

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
        jadwal_code=jadwal.code, 
        
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
    db.flush() 

    for item in cart_items:       
        order_seat = OrderSeat(
            order_id=new_order.id,
            jadwal_id=item.jadwal_id,
            studio_id=item.studio_id, 
            row=item.row,
            col=item.col
        )
        db.add(order_seat)
    
    for item in cart_items:
        db.delete(item)

    db.commit()

    return {
        "order_code": order_code,
        "total_seat": seat_count,
        "final_price": final_price,
        "change": change,           
        "status": status_message,   
        "message": custom_message   
    }

@router.get("/order/{order_code}", response_model=OrderResponse)
def get_order(order_code: str, db: Session = Depends(get_db)):  
    order = db.query(Order).filter(Order.code == order_code).first()
    if not order:
        raise HTTPException(404, "Order tidak ditemukan")
    
    msg = "Transaksi Berhasil"
    if order.change and order.change > 0:
        msg = f"Kembalian: Rp {order.change}"
    
    return {
        "order_code": order.code,
        "total_seat": order.seat_count,
        "final_price": order.final_price,
        "change": order.change if order.change else 0, 
        "status": "PAID", 
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
