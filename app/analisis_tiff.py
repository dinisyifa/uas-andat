from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, extract
from datetime import date, datetime, timedelta
from typing import Optional, List

from app.database import get_db
from sqlalchemy import text
from app.models import Movie, Order, Membership, Jadwal

router = APIRouter()

MONTH_NAMES = {
    "januari": 1, "februari": 2, "maret": 3, "april": 4, "mei": 5, "juni": 6,
    "juli": 7, "agustus": 8, "september": 9, "oktober": 10, "november": 11, "desember": 12
}


# 1. Film paling populer
@router.get("/analisis/filmpopuler")
def film_popular(
    periode: str,
    hari: int = None,
    bulan: str = None,
    db: Session = Depends(get_db)
):
    """Film yang paling populer ditunjukkan dari total penjualan tiket terbanyak.
    Pilih periode: harian, mingguan, bulanan.
    """
    
    periode = periode.lower()

    if periode not in ["harian", "mingguan", "bulanan"]:
        return {"error": "periode harus: harian | mingguan | bulanan"}

    year = 2024
    month = 12

    if periode == "harian":
        if not hari:
            return {"error": "Parameter 'hari' wajib untuk harian"}
        
        tanggal = date(year, month, hari)

        query = text("""
            SELECT m.id, m.title, COUNT(o.id) AS total
            FROM orders o
            JOIN jadwal j ON o.jadwal_id = j.id
            JOIN movies m ON j.movie_id = m.id
            WHERE o.transaction_date = :tanggal
            GROUP BY m.id, m.title
            ORDER BY total DESC;
        """)

        data = db.execute(query, {"tanggal": tanggal}).mappings().all()

        return {"periode": "harian", "tanggal": tanggal.isoformat(), "data": data}

    # MINGGUAN
    if periode == "mingguan":
        minggu_ranges = [(1,7),(8,14),(15,21),(22,28),(29,31)]
        hasil = []

        for i,(s,e) in enumerate(minggu_ranges,start=1):
            start = date(year, month, s)
            end = date(year, month, e)

            query = text("""
                SELECT m.id, m.title, COUNT(o.id) AS total
                FROM orders o
                JOIN jadwal j ON o.jadwal_id = j.id
                JOIN movies m ON j.movie_id = m.id
                WHERE o.transaction_date BETWEEN :s AND :e
                GROUP BY m.id, m.title
                ORDER BY total DESC;
            """)

            rows = db.execute(query, {"s": start, "e": end}).mappings().all()
            hasil.append({
                "minggu_ke": i,
                "periode": f"{start} s/d {end}",
                "film_terlaris": rows[0] if rows else None,
                "data": rows
            })

        return {"periode": "mingguan", "data": hasil}

    # BULANAN
    if periode == "bulanan":
        if not bulan:
            return {"error": "Parameter 'bulan' wajib untuk bulanan"}

        bln = bulan.lower()
        if bln not in MONTH_NAMES:
            return {"error": "Nama bulan tidak valid!"}

        month_number = MONTH_NAMES[bln]
        start = date(year, month_number, 1)
        end = date(year + 1, 1, 1) if month_number == 12 else date(year, month_number+1, 1)

        query = text("""
            SELECT m.id, m.title, COUNT(o.id) AS total
            FROM orders o
            JOIN jadwal j ON o.jadwal_id = j.id
            JOIN movies m ON j.movie_id = m.id
            WHERE o.transaction_date >= :start AND o.transaction_date < :end
            GROUP BY m.id, m.title
            ORDER BY total DESC;
        """)

        rows = db.execute(query, {"start": start, "end": end}).mappings().all()

        return {
            "periode": "bulanan",
            "bulan": bulan,
            "film_terlaris": rows[0] if rows else None,
            "data": rows
        }


# 2. Jam tayang paling populer
@router.get("/analisis/jamtayangpopuler")
def jam_tayang_populer(
    periode: str,
    hari: int = None,
    bulan: str = None,
    db: Session = Depends(get_db)
):

    """Jam tayang yang paling populer ditunjukkan dari total penjualan tiket terbanyak.
    Pilih periode: harian, mingguan, bulanan.
    """

    periode = periode.lower()
    year = 2024
    month = 12

    def extract(rows):
        grp = {}
        for r in rows:
            mid = r["movie_id"]
            grp.setdefault(mid,{
                "movie_id": mid,
                "title": r["title"],
                "jadwal": []
            })
            grp[mid]["jadwal"].append({"jam": str(r["jam"]), "tiket_terjual": r["total"]})

        for g in grp.values():
            g["jadwal"].sort(key=lambda x: x["tiket_terjual"], reverse=True)
            g["jam_terpopuler"] = g["jadwal"][0]["jam"]
        return list(grp.values())

    if periode == "harian":
        if not hari: return {"error": "hari wajib untuk harian"}

        tanggal = date(year, month, hari)
        query = text("""
            SELECT m.id movie_id, m.title, j.jam, COUNT(o.id) total
            FROM orders o
            JOIN jadwal j ON o.jadwal_id=j.id
            JOIN movies m ON j.movie_id=m.id
            WHERE o.transaction_date=:t
            GROUP BY m.id,m.title,j.jam;
        """)

        rows = db.execute(query, {"t": tanggal}).mappings().all()
        return {"periode":"harian","tanggal":tanggal.isoformat(),"data":extract(rows)}

    if periode == "mingguan":
        minggu_ranges=[(1,7),(8,14),(15,21),(22,28),(29,31)]
        hasil=[]
        for i,(s,e) in enumerate(minggu_ranges,1):
            start,end=date(year,month,s),date(year,month,e)
            query=text("""
                SELECT m.id movie_id,m.title,j.jam,COUNT(o.id) total
                FROM orders o
                JOIN jadwal j ON o.jadwal_id=j.id
                JOIN movies m ON j.movie_id=m.id
                WHERE o.transaction_date BETWEEN :s AND :e
                GROUP BY m.id,m.title,j.jam;
            """)
            rows=db.execute(query,{"s":start,"e":end}).mappings().all()
            hasil.append({"minggu_ke":i,"periode":f"{start}s/d{end}","data":extract(rows)})
        return {"periode":"mingguan","data":hasil}

    if periode == "bulanan":
        if not bulan: return {"error":"bulan wajib untuk bulanan"}

        bl=bulan.lower()
        if bl not in MONTH_NAMES: return {"error":"bulan tidak valid"}

        mn=MONTH_NAMES[bl]
        start=date(year,mn,1)
        end=date(year+1,1,1) if mn==12 else date(year,mn+1,1)

        query=text("""
            SELECT m.id movie_id,m.title,j.jam,COUNT(o.id) total
            FROM orders o
            JOIN jadwal j ON o.jadwal_id=j.id
            JOIN movies m ON j.movie_id=m.id
            WHERE o.transaction_date>=:s AND o.transaction_date<:e
            GROUP BY m.id,m.title,j.jam;
        """)

        rows=db.execute(query,{"s":start,"e":end}).mappings().all()
        return {"periode":"bulanan","bulan":bulan,"data":extract(rows)}

    return {"error": "periode salah"}


# 3. Pilihan kursi paling populer

# 4. Pendapatan per film

# 5. Pendapatan Film Terbanyak (Juara per Periode)
@router.get("/analisis/top-revenue-films")
def get_top_revenue_films(
    period: Optional[str] = Query(None, description="Pilih periode: 'hari', 'minggu', 'bulan'"),
    db: Session = Depends(get_db)
):
    """
    Menampilkan FILM JUARA (Pendapatan Tertinggi) untuk setiap rentang waktu di DESEMBER 2024.
    """
    
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

    ranges = []
    
    if period == "hari":
        for d in range(1, 32):
            ranges.append((d, d, f"Tanggal {d} Desember 2024"))
            
    elif period == "minggu":
        ranges = [
            (1, 7, "Minggu 1 (1-7 Desember 2024)"),
            (8, 14, "Minggu 2 (8-14 Desember 2024)"),
            (15, 21, "Minggu 3 (15-21 Desember 2024)"),
            (22, 28, "Minggu 4 (22-28 Desember 2024)"),
            (29, 31, "Minggu 5 (29-31 Desember 2024)")
        ]
        
    elif period == "bulan":
        ranges = [(1, 31, "Bulan Desember 2024 penuh")]
        
    else:
        return {"pesan": "Periode salah. Pilih: hari, minggu, atau bulan."}

    output_data = []
    
    for start_day, end_day, label in ranges:
        start_date = date(2024, 12, start_day)
        end_date = date(2024, 12, end_day)
        
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



# 6. Perilaku Pelanggan (Top Customers)
@router.get("/analisis/top-customers")
def get_top_customers(
    period: Optional[str] = Query(None, description="Pilih periode: 'minggu', 'bulan'"),
    db: Session = Depends(get_db)
):
    """
    Menampilkan 'PELANGGAN TER-RAJIN' (Frekuensi Order Terbanyak) per periode di DESEMBER 2024.
    """
    
    if not period:
        return {
            "status": "info",
            "pesan": "Tolong pilih periode dulu!",
            "instruksi": {"key": "period", "opsi": ["minggu", "bulan"]}
        }

    ranges = []
    
    if period == "minggu":

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

    output_data = []
    
    for start_day, end_day, label in ranges:
        start_date = date(2024, 12, start_day)
        end_date = date(2024, 12, end_day)


        top_member = (
            db.query(
                Membership.code.label("member_code"),
                Membership.nama,
                func.count(Order.id).label("total_transaksi")
            )
            .join(Order, Membership.code == Order.membership_code)
            .filter(Order.transaction_date >= start_date)
            .filter(Order.transaction_date <= end_date)
            .group_by(Membership.code, Membership.nama) 
            .order_by(desc("total_transaksi"))
            .first() 
        )

        if top_member:
            output_data.append({
                "periode": label,
                "pelanggan_juara": top_member.nama,
                "code_pelanggan": top_member.member_code,
                "jumlah_transaksi": top_member.total_transaksi
            })
        else:
            output_data.append({
                "periode": label,
                "pelanggan_juara": "Tidak ada transaksi",
                "code_pelanggan": None,
                "jumlah_transaksi": 0
            })

    return {
        "request_period": period,
        "info": "Menampilkan pelanggan dengan order terbanyak pada periode tersebut.",
        "total_data": len(output_data),
        "hasil_analisis": output_data
    }


# 7. Hari dan tanggal teramai
import calendar 
@router.get("/analisis/most-busiest-day")
def get_busiest_day(
    bulan: int = Query(12, description="Bulan (1-12)"),
    tahun: int = Query(2024, description="Tahun"),
    db: Session = Depends(get_db)
):
    
    if bulan != 12 or tahun != 2024:
        return {
            "message": f"Tidak ada data transaksi di periode yang diminta. Untuk saat ini, hanya ada data bulan Desember 2024."
        }

    top_dates = (
        db.query(
            Order.transaction_date,
            func.sum(Order.seat_count).label("total_tiket")
        )
        .filter(extract('month', Order.transaction_date) == bulan)
        .filter(extract('year', Order.transaction_date) == tahun)
        .group_by(Order.transaction_date)
        .order_by(desc("total_tiket"))
        .limit(5)
        .all()
    )


    top_days = (
        db.query(
            func.dayname(Order.transaction_date).label("nama_hari"),
            func.sum(Order.seat_count).label("total_tiket")
        )
        .filter(extract('month', Order.transaction_date) == bulan)
        .filter(extract('year', Order.transaction_date) == tahun)
        .group_by("nama_hari")
        .order_by(desc("total_tiket")) 
        .all()
    )

    nama_bulan = calendar.month_name[bulan]
    juara_tanggal = top_dates[0] 
    juara_hari = top_days[0]     

    detail_top_dates = []
    for r in top_dates:
        detail_top_dates.append({
            "tanggal": r.transaction_date.strftime("%d %B %Y"),
            "hari": r.transaction_date.strftime("%A"),
            "total_tiket": r.total_tiket
        })

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



# 8. Genre paling populer 
@router.get("/analisis/genrepopuler")
def genre_populer(
    periode: str,
    hari: int = None,
    bulan: str = None,
    db: Session = Depends(get_db)
):

    """Genre yang paling populer ditunjukkan dari total penjualan tiket terbanyak.
    Pilih periode: harian, mingguan, bulanan.
    """


    periode = periode.lower()
    year = 2024
    month = 12

    def persen(rows):
        total = sum(r["total"] for r in rows)
        for r in rows:
            r["persentase"] = round((r["total"] / total * 100),1) if total>0 else 0
        return rows

    if periode == "harian":
        if not hari: return {"error":"hari wajib"}
        tanggal=date(year,month,hari)

        q=text("""
            SELECT m.genre,COUNT(os.id) total
            FROM order_seats os
            JOIN orders o ON os.order_id=o.id
            JOIN jadwal j ON o.jadwal_id=j.id
            JOIN movies m ON j.movie_id=m.id
            WHERE o.transaction_date=:t
            GROUP BY m.genre
            ORDER BY total DESC;
        """)
        rows=db.execute(q,{"t":tanggal}).mappings().all()
        return {"periode":"harian","tanggal":tanggal.isoformat(),"data":persen(rows)}

    if periode == "mingguan":
        minggu_ranges=[(1,7),(8,14),(15,21),(22,28),(29,31)]
        hasil=[]
        for i,(s,e) in enumerate(minggu_ranges,1):
            start,end=date(year,month,s),date(year,month,e)
            q=text("""
                SELECT m.genre,COUNT(os.id) total
                FROM order_seats os
                JOIN orders o ON os.order_id=o.id
                JOIN jadwal j ON o.jadwal_id=j.id
                JOIN movies m ON j.movie_id=m.id
                WHERE o.transaction_date BETWEEN :s AND :e
                GROUP BY m.genre
                ORDER BY total DESC;
            """)
            rows=db.execute(q,{"s":start,"e":end}).mappings().all()
            hasil.append({
                "minggu_ke":i,
                "periode":f"{start}s/d{end}",
                "data":persen(rows)
            })
        return {"periode":"mingguan","data":hasil}

    if periode == "bulanan":
        if not bulan: return {"error":"bulan wajib"}
        bl=bulan.lower()
        if bl not in MONTH_NAMES: return {"error":"bulan invalid"}
        mn=MONTH_NAMES[bl]
        start=date(year,mn,1)
        end=date(year+1,1,1) if mn==12 else date(year,mn+1,1)

        q=text("""
            SELECT m.genre,COUNT(os.id) total
            FROM order_seats os
            JOIN orders o ON os.order_id=o.id
            JOIN jadwal j ON o.jadwal_id=j.id
            JOIN movies m ON j.movie_id=m.id
            WHERE o.transaction_date>=:s AND o.transaction_date<:e
            GROUP BY m.genre
            ORDER BY total DESC;
        """)

        rows=db.execute(q,{"s":start,"e":end}).mappings().all()
        return {"periode":"bulanan","bulan":bulan,"data":persen(rows)}

    return {"error":"periode salah"}


# 9. metode pembayaran paling populer(Payment Preference)
@router.get("/analisis/metodepembayaran")
def metode_pembayaran(db: Session = Depends(get_db)):
    """Metode pembayaran yang paling populer ditunjukkan dari total jenis pembayaran terbanyak di Order.
    """

    query = text("""
        SELECT 
            payment_method,
            COUNT(id) AS penggunaan,
            ROUND(COUNT(id) * 100.0 / (SELECT COUNT(*) FROM orders), 1) AS persentase
        FROM orders
        GROUP BY payment_method
        ORDER BY penggunaan DESC;
    """)
    
    result = db.execute(query).mappings().all()
    return {"data": result}