from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, extract
from typing import Optional, List
from datetime import date, datetime, timedelta # <--- Import Lengkap

from app.database import get_db
from app.models import Movie, Order, Membership, Jadwal

router = APIRouter(
    prefix="/analisis",
    tags=["Analisis Tiff"]
)

# --- 1. Pendapatan Film Terbanyak (Juara per Periode) ---
@router.get("/top-revenue-films")
def get_top_revenue_films(
    period: Optional[str] = Query(None, description="Pilih periode: 'hari', 'minggu', 'bulan'"),
    db: Session = Depends(get_db)
):
    """
    Menampilkan FILM JUARA (Pendapatan Tertinggi) untuk setiap rentang waktu di DESEMBER 2024.
    """
    
    # 1. Cek Parameter (Handling Pesan Manual)
    if not period:
        return {
            "status": "info",
            "pesan": "Tolong pilih periode dulu!",
            "instruksi": {
                "key": "period",
                "opsi": ["hari", "minggu", "bulan"],
                "contoh": "/analisis/top-revenue-films?period=minggu"
            }
        }

    # 2. menentukan Rentang Tanggal (Ranges) berdasarkan Desember 2024
    ranges = []
    
    if period == "Tiap Hari Pada Bulan Desember 2024":
        # Loop tanggal 1 sampai 31
        for d in range(1, 32):
            ranges.append((d, d, f"Tanggal {d} Des"))
            
    elif period == "minggu":
        # Manual definisi minggu
        ranges = [
            (1, 7, "Minggu 1 (1-7 Des)"),
            (8, 14, "Minggu 2 (8-14 Des)"),
            (15, 21, "Minggu 3 (15-21 Des)"),
            (22, 28, "Minggu 4 (22-28 Des)"),
            (29, 31, "Minggu 5 (29-31 Des)")
        ]
        
    elif period == "bulan":
        ranges = [(1, 31, "Bulan Desember 2024 penuh")]
        
    else:
        return {"pesan": "Periode salah. Pilih: hari, minggu, atau bulan."}

    # 3. Proses Loop Query untuk setiap Range
    output_data = []
    
    for start_day, end_day, label in ranges:
        start_date = date(2024, 12, start_day)
        end_date = date(2024, 12, end_day)
        
        # Query: Cari 1 film juara
        top_film = (
            db.query(
                Movie.title,
                func.sum(Order.final_price).label("total_revenue")
            )
            .join(Jadwal, Movie.id == Jadwal.movie_id)
            .join(Order, Jadwal.id == Order.jadwal_id)
            .filter(Order.transaction_date >= start_date)
            .filter(Order.transaction_date <= end_date)
            .group_by(Movie.id)
            .order_by(desc("total_revenue"))
            .first()
        )
        
        if top_film:
            output_data.append({
                "periode": label,
                "film_juara": top_film.title,
                "pendapatan": top_film.total_revenue
            })
        else:
            output_data.append({
                "periode": label,
                "film_juara": "Tidak ada transaksi",
                "pendapatan": 0
            })

    return {
        "request_period": period,
        "total_data": len(output_data),
        "hasil_analisis": output_data
    }





# --- 2. Perilaku Pelanggan (Top Customers) ---
@router.get("/top-customers")
def get_top_customers(
    period: Optional[str] = Query(None, description="Pilih periode: 'minggu', 'bulan'"),
    db: Session = Depends(get_db)
):
    """
    Menampilkan 'PELANGGAN TER-RAJIN' (Frekuensi Order Terbanyak) per periode di DESEMBER 2024.
    """
    
    # 1. Cek Parameter (Handling Pesan Manual)
    if not period:
        return {
            "status": "info",
            "pesan": "Tolong pilih periode dulu!",
            "instruksi": {"key": "period", "opsi": ["minggu", "bulan"]}
        }

    # 2. Tentukan Rentang Waktu (Ranges) berdasarkan Desember 2024
    ranges = []
    
    if period == "minggu":
        # Manual definisi minggu (Minggu 1: 1-7, dst)
        ranges = [
            (1, 7, "Minggu 1 (1-7 Des)"),
            (8, 14, "Minggu 2 (8-14 Des)"),
            (15, 21, "Minggu 3 (15-21 Des)"),
            (22, 28, "Minggu 4 (22-28 Des)"),
            (29, 31, "Minggu 5 (29-31 Des)")
        ]
    elif period == "bulan":
        ranges = [(1, 31, "Bulan Desember Full")]
    else:
        return {"pesan": "Periode salah. Pilih: minggu atau bulan."}

    # 3. Proses Loop Query untuk setiap Range
    output_data = []
    
    for start_day, end_day, label in ranges:
        # Konversi ke object date
        start_date = date(2024, 12, start_day)
        end_date = date(2024, 12, end_day)

        # Query: Cari member dengan frekuensi order terbanyak (count order.id)
        top_member = (
            db.query(
                Membership.id.label("member_id"),
                Membership.nama,
                func.count(Order.id).label("total_transaksi")
            )
            .join(Order, Membership.id == Order.membership_id)
            .filter(Order.transaction_date >= start_date)
            .filter(Order.transaction_date <= end_date)
            .group_by(Membership.id, Membership.nama) # Grouping berdasarkan ID dan Nama
            .order_by(desc("total_transaksi"))
            .first() # Ambil Juara 1
        )

        if top_member:
            output_data.append({
                "periode": label,
                "pelanggan_juara": top_member.nama,
                "id_pelanggan": top_member.member_id,
                "jumlah_transaksi": top_member.total_transaksi
            })
        else:
            output_data.append({
                "periode": label,
                "pelanggan_juara": "Tidak ada transaksi",
                "id_pelanggan": None,
                "jumlah_transaksi": 0
            })

    return {
        "request_period": period,
        "info": "Menampilkan pelanggan dengan order terbanyak pada periode tersebut.",
        "total_data": len(output_data),
        "hasil_analisis": output_data
    }



# --- 3. Most Busiest Day ---
# Pastikan ada import ini di paling atas file
import calendar 

# ... (kode analisis 1 dan 2 biarkan saja) ...

# ==========================================
# 3. ANALISIS TANGGAL & HARI TERAMAI (Most Busiest Date & Day)
# ==========================================
@router.get("/most-busiest-day")
def get_busiest_day(
    bulan: int = Query(12, ge=1, le=12, description="Bulan (1-12)"),
    tahun: int = Query(2024, description="Tahun"),
    db: Session = Depends(get_db)
):
    """
    Analisis Keramaian Bioskop:
    1. Mencari TANGGAL spesifik teramai (Top 5).
    2. Mencari HARI apa (Senin-Minggu) yang secara umum paling diminati penonton.
    """
    
    # --- BAGIAN A: TANGGAL TERAMAI (Specific Date) ---
    # Mencari tanggal spesifik (misal: 11 Des) dengan penjualan tertinggi
    top_dates = (
        db.query(
            Order.transaction_date,
            func.sum(Order.seat_count).label("total_tiket")
        )
        .filter(extract('month', Order.transaction_date) == bulan)
        .filter(extract('year', Order.transaction_date) == tahun)
        .group_by(Order.transaction_date)
        .order_by(desc("total_tiket"))
        .limit(5) # Cuma ambil Top 5 sesuai request
        .all()
    )

    if not top_dates:
        return {"message": "Tidak ada data transaksi di periode ini."}

    # --- BAGIAN B: HARI TERAMAI (Day of Week Analysis) ---
    # Menjumlahkan tiket berdasarkan Nama Hari (Semua Senin dijumlah, Semua Selasa dijumlah, dst)
    top_days = (
        db.query(
            func.dayname(Order.transaction_date).label("nama_hari"),
            func.sum(Order.seat_count).label("total_tiket")
        )
        .filter(extract('month', Order.transaction_date) == bulan)
        .filter(extract('year', Order.transaction_date) == tahun)
        .group_by("nama_hari")
        .order_by(desc("total_tiket")) # Ranking dari hari paling favorit
        .all()
    )

    # --- FORMATTING OUTPUT ---
    nama_bulan = calendar.month_name[bulan]
    juara_tanggal = top_dates[0] # Juara 1 Tanggal
    juara_hari = top_days[0]     # Juara 1 Hari (Secara Umum)

    # Format Detail Top 5 Tanggal
    detail_top_dates = []
    for r in top_dates:
        detail_top_dates.append({
            "tanggal": r.transaction_date.strftime("%d %B %Y"),
            "hari": r.transaction_date.strftime("%A"),
            "total_tiket": r.total_tiket
        })

    # Format Detail Ranking Hari (Senin-Minggu)
    detail_days_ranking = []
    for r in top_days:
        detail_days_ranking.append({
            "nama_hari": r.nama_hari,
            "total_akumulasi_tiket": r.total_tiket
        })

    return {
        "periode": f"{nama_bulan} {tahun}",
        "kesimpulan": {
            "judul": "Most Busiest Time Analysis",
            "tanggal_tersibuk": f"{juara_tanggal.transaction_date.strftime('%A, %d %B %Y')} (Total: {juara_tanggal.total_tiket} tiket)",
            "hari_favorit_penonton": f"Secara umum, penonton paling suka datang di hari {juara_hari.nama_hari} (Total sebulan: {juara_hari.total_tiket} tiket)"
        },
        "top_5_tanggal_teramai": detail_top_dates,
        "ranking_hari_teramai": detail_days_ranking
    }