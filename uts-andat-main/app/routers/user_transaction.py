# app/routers/user_cart.py
from fastapi import APIRouter, HTTPException
import uuid
from typing import List, Dict, Any
from app.models import CartAddItem, CartItemResponse, TransactionDetail, PreTransactionResponse, PaymentMethodRequest
from app.routers.admin_jadwal import list_jadwal
from app.routers.admin_film import list_film
from datetime import datetime, timedelta

router = APIRouter()

# Database sementara 
cart_items: List[Dict[str, Any]] = []
transactions: List[Dict[str, Any]] = []

# =============================================== API KERANJANG ================================================

# CREATE - Tambah item ke cart
@router.post("/cart/add")
def menambahkan_ke_keranjang(item: CartAddItem):
    """
    Menambahkan tiket ke keranjang user.
    """
    # Cek validitas jadwal
    schedule = next((j for j in list_jadwal if j["id_jadwal"] == item.schedule_id), None)
    if not schedule:
        raise HTTPException(status_code=404, detail="Jadwal tidak ditemukan.")

    # Cek validitas kursi
    seat_found = False
    for row in schedule["seats"]:
        for seat in row:
            if seat["seat"] == item.seat_number and seat["available"]:
                seat_found = True
                break
    if not seat_found:
        raise HTTPException(status_code=400, detail="Kursi tidak tersedia atau sudah dipesan.")

    # Ambil data film
    film = next((f for f in list_film if f["title"].lower() == item.movie_title.lower()), None)
    if not film:
        raise HTTPException(status_code=404, detail="Film tidak ditemukan.")

    # Buat item keranjang
    item_id = str(uuid.uuid4())[:8]
    cart_item = {
        "item_id": item_id,
        "schedule_id": item.schedule_id,
        "movie_id": film["id"],
        "movie_title": film["title"],
        "schedule": f"{schedule['date']} {schedule['time']}",
        "studio": schedule["studio_name"],
        "seat_number": item.seat_number,
        "price": int(film["price"].replace("Rp", "").replace(".", ""))  # convert harga ke int
    }

    cart_items.append(cart_item)
    return {"message": "Tiket berhasil ditambahkan ke keranjang", "data": cart_item}


# GET - Lihat isi keranjang
@router.get("/cart")
def lihat_isi_keranjang():
    if not cart_items:
        raise HTTPException(status_code=404, detail="Keranjang kosong.")
    total = sum(i["price"] for i in cart_items)
    return {"message": "Isi keranjang berhasil diambil", "total_harga": total, "items": cart_items}


# DELETE - Hapus item dari cart
@router.delete("/cart/remove/{item_id}")
def hapus_dari_keranjang(item_id: str):
    for item in cart_items:
        if item["item_id"] == item_id:
            cart_items.remove(item)
            return {"message": f"Item {item_id} berhasil dihapus dari keranjang"}
    raise HTTPException(status_code=404, detail="Item tidak ditemukan di keranjang.")


# Simulasi penyimpanan pesanan sementara & riwayat transaksi
pending_orders: Dict[str, Any] = {}
transaction_history: List[Dict[str, Any]] = []

# =============================================== API CHECKOUT ================================================

# CREATE - Checkout
@router.post("/checkout/payment", response_model=PreTransactionResponse)
def metode_pembayaran(payload: PaymentMethodRequest):
    """
    Langkah 1: User memilih metode pembayaran, QRIS atau Debit/Credit Card.
    Sistem membuat pesanan sementara yang berlaku 5 menit.
    """
    if not cart_items:
        raise HTTPException(status_code=400, detail="Keranjang belanja kosong.")

    # Validasi ulang semua kursi sebelum membuat pesanan sementara
    for item in cart_items:
        schedule = next((s for s in list_jadwal if s.get("id_jadwal") == item.get("schedule_id")), None)
        if not schedule:
            raise HTTPException(status_code=404, detail=f"Jadwal {item.get('schedule_id')} tidak ditemukan.")
        
        # Cek apakah kursi masih tersedia (dalam format baris kursi list)
        seat_available = False
        for row in schedule["seats"]:
            for seat in row:
                if seat["seat"] == item["seat_number"] and seat["available"]:
                    seat_available = True
                    break
        if not seat_available:
            raise HTTPException(
                status_code=409,
                detail=f"Checkout gagal. Kursi '{item.get('seat_number')}' sudah tidak tersedia lagi."
            )

    # Buat pesanan sementara
    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    total_price = sum(item.get("price", 0) for item in cart_items)
    expires_at = datetime.utcnow() + timedelta(minutes=5)  # Berlaku 5 menit

    # Buat daftar tiket yang bersih untuk respons
    clean_tickets = [
        {
            "item_id": item["item_id"],
            "movie_title": item["movie_title"],
            "schedule": item["schedule"],
            "studio": item["studio"],
            "seat_number": item["seat_number"],
            "price": item["price"],
            "schedule_id": item["schedule_id"],
            "movie_id": item["movie_id"],   
        }
        for item in cart_items
    ]

    # Simpan pesanan sementara
    pending_orders[order_id] = {
        "total_price": total_price,
        "payment_method": payload.payment_method,
        "expires_at": expires_at,
        "tickets_full_data": list(cart_items)  # Simpan data lengkap keranjang
    }

    # Kosongkan keranjang setelah buat pesanan sementara
    cart_items.clear()

    # Kembalikan detail pesanan sementara ke user
    return PreTransactionResponse(
        order_id=order_id,
        total_price=total_price,
        payment_method=payload.payment_method,
        expires_at=expires_at,
        tickets=clean_tickets
    )

# GET - Konfirmasi checkout
@router.get("/checkout/{order_id}/confirm", response_model=TransactionDetail)
def konfirmasi_pembayaran(order_id: str):
    """
    Langkah 2: User mengonfirmasi pembayaran (finalisasi transaksi).
    """
    order = pending_orders.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Pesanan tidak ditemukan atau sudah kedaluwarsa.")
    
    # Cek masa berlaku
    if datetime.utcnow() > order["expires_at"]:
        pending_orders.pop(order_id, None)
        raise HTTPException(status_code=410, detail="Pesanan sudah kedaluwarsa.")

    # Tandai kursi sebagai booked permanen
    for item in order["tickets_full_data"]:
        schedule = next((s for s in list_jadwal if s.get("id_jadwal") == item.get("schedule_id")), None)
        if schedule:
            for row in schedule["seats"]:
                for seat in row:
                    if seat["seat"] == item["seat_number"]:
                        seat["available"] = False

    # Hasilkan kode booking final
    booking_code = f"BK-{uuid.uuid4().hex[:8].upper()}"

    # Buat data transaksi final
    final_transaction = {
        "transaction_id": booking_code,  #
        "user_id": "USER001",
        "schedule_id": order["tickets_full_data"][0]["schedule_id"] if order["tickets_full_data"] else "",
        "seats": [item["seat_number"] for item in order["tickets_full_data"]],
        "total_price": order["total_price"]
    }

    # Simpan ke riwayat transaksi dan hapus dari pending
    transaction_history.append(final_transaction)
    pending_orders.pop(order_id, None)

    return TransactionDetail(**final_transaction)