from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date, datetime

from app.database import get_db
from sqlalchemy import text

router = APIRouter()

MONTH_NAMES = {
    "januari": 1, "februari": 2, "maret": 3, "april": 4, "mei": 5, "juni": 6,
    "juli": 7, "agustus": 8, "september": 9, "oktober": 10, "november": 11, "desember": 12
}


# 1. Film paling populer
@router.get("/filmpopuler/daily")
def film_popular_daily(day: int, db: Session = Depends(get_db)):

    # Semua data kamu ada di bulan Desember 2024
    tanggal = date(2024, 12, day)

    query = text("""
        SELECT 
            m.id,
            m.title,
            COUNT(o.id) AS total_tiket_terjual
        FROM orders o
        JOIN jadwal j ON o.jadwal_id = j.id
        JOIN movies m ON j.movie_id = m.id
        WHERE o.transaction_date = :tanggal
        GROUP BY m.id, m.title
        ORDER BY total_tiket_terjual DESC;
    """)

    result = db.execute(query, {"tanggal": tanggal}).mappings().all()

    return {
        "tanggal": tanggal.isoformat(),
        "total_tiket_terjual": len(result),
        "data": result
    }


@router.get("/filmpopuler/weekly")
def film_popular_weekly(db: Session = Depends(get_db)):

    year = 2024
    month = 12
    results = []

    # pembagian minggu bulanan: 1–7, 8–14, 15–21, 22–28, 29–31
    minggu_ranges = [
        (1, 7),
        (8, 14),
        (15, 21),
        (22, 28),
        (29, 31),
    ]

    for i, (start_day, end_day) in enumerate(minggu_ranges, start=1):
        start_date = date(year, month, start_day)
        end_date = date(year, month, end_day)

        query = text("""
            SELECT 
                m.id,
                m.title,
                COUNT(o.id) AS total_tiket_terjual
            FROM orders o
            JOIN jadwal j ON o.jadwal_id = j.id
            JOIN movies m ON j.movie_id = m.id
            WHERE o.transaction_date BETWEEN :start_date AND :end_date
            GROUP BY m.id, m.title
            ORDER BY total_tiket_terjual DESC;
        """)

        films = db.execute(query, {
            "start_date": start_date,
            "end_date": end_date
        }).mappings().all()

        hasil_mingguan = {
            "minggu": i,
            "range_tanggal": f"{start_date.isoformat()} s/d {end_date.isoformat()}",
            "film_terlaris": films[0] if films else None,
            "data": films
        }

        results.append(hasil_mingguan)

    return {
        "bulan": "Desember 2024",
        "total_minggu": len(results),
        "hasil": results
    }


@router.get("/filmpopuler/monthly")
def film_popular_monthly(bulan: str, db: Session = Depends(get_db)):

    bulan_lower = bulan.lower()

    if bulan_lower not in MONTH_NAMES:
        return {"error": "Nama bulan tidak valid!"}

    month_number = MONTH_NAMES[bulan_lower]
    year = 2024     # data kamu fix ada di 2024

    start_date = date(year, month_number, 1)

    # tentukan akhir bulan
    if month_number == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month_number + 1, 1)

    query = text("""
        SELECT 
            m.id,
            m.title,
            COUNT(o.id) AS total_tiket_terjual
        FROM orders o
        JOIN jadwal j ON o.jadwal_id = j.id
        JOIN movies m ON j.movie_id = m.id
        WHERE o.transaction_date >= :start_date
        AND o.transaction_date < :end_date
        GROUP BY m.id, m.title
        ORDER BY total_tiket_terjual DESC;
    """)

    result = db.execute(query, {
        "start_date": start_date,
        "end_date": end_date
    }).mappings().all()

    return {
        "bulan": bulan,
        "total_film": len(result),
        "film_terlaris": result[0] if result else None,
        "data": result
    }


# 2. Jam tayang paling populer
@router.get("/jamtayangpopuler/daily")
def jamtayang_daily(day: int, db: Session = Depends(get_db)):

    tanggal = date(2024, 12, day)

    query = text("""
        SELECT
            m.id AS movie_id,
            m.title,
            j.jam,
            COUNT(o.id) AS total_tiket
        FROM orders o
        JOIN jadwal j ON o.jadwal_id = j.id
        JOIN movies m ON j.movie_id = m.id
        WHERE o.transaction_date = :tanggal
        GROUP BY m.id, m.title, j.jam
        ORDER BY m.id, total_tiket DESC;
    """)

    rows = db.execute(query, {"tanggal": tanggal}).mappings().all()

    output = {}
    for r in rows:
        mid = r["movie_id"]
        if mid not in output:
            output[mid] = {
                "movie_id": mid,
                "title": r["title"],
                "list_jadwal": [],
            }
        output[mid]["list_jadwal"].append({
            "jam": str(r["jam"]),
            "tiket": r["total_tiket"]
        })

    # cari jam paling populer
    for mv in output.values():
        sorted_jam = sorted(mv["list_jadwal"], key=lambda x: x["tiket"], reverse=True)
        mv["jam_terpopuler"] = sorted_jam[0]["jam"]
        mv["total_tiket"] = sorted_jam[0]["tiket"]

    return {
        "tanggal": tanggal.isoformat(),
        "data": list(output.values())
    }

@router.get("/jamtayangpopuler/weekly")
def jamtayang_weekly(db: Session = Depends(get_db)):

    year = 2024
    month = 12

    minggu_ranges = [
        (1, 7),
        (8, 14),
        (15, 21),
        (22, 28),
        (29, 31),
    ]

    hasil_minggu = []

    for i, (start, end) in enumerate(minggu_ranges, start=1):

        start_date = date(year, month, start)
        end_date = date(year, month, end)

        query = text("""
            SELECT
                m.id AS movie_id,
                m.title,
                j.jam,
                COUNT(o.id) AS total_tiket
            FROM orders o
            JOIN jadwal j ON o.jadwal_id = j.id
            JOIN movies m ON j.movie_id = m.id
            WHERE o.transaction_date BETWEEN :start_date AND :end_date
            GROUP BY m.id, m.title, j.jam
        """)

        rows = db.execute(query, {
            "start_date": start_date,
            "end_date": end_date
        }).mappings().all()

        per_film = {}
        for r in rows:
            mid = r["movie_id"]
            if mid not in per_film:
                per_film[mid] = {
                    "title": r["title"],
                    "list_jam": []
                }
            per_film[mid]["list_jam"].append({
                "jam": str(r["jam"]),
                "tiket": r["total_tiket"]
            })

        # tentukan jam tayang terpopuler
        data_film = []
        for mv in per_film.values():
            sorted_jam = sorted(mv["list_jam"], key=lambda x: x["tiket"], reverse=True)
            data_film.append({
                "title": mv["title"],
                "jam_terpopuler": sorted_jam[0]["jam"],
                "total_tiket": sorted_jam[0]["tiket"],
                "detail": mv["list_jam"]
            })

        hasil_minggu.append({
            "minggu_ke": i,
            "range": f"{start_date.isoformat()} s/d {end_date.isoformat()}",
            "data": data_film
        })

    return {
        "bulan": "Desember 2024",
        "minggu": hasil_minggu
    }

@router.get("/jamtayangpopuler/monthly")
def jamtayang_monthly(bulan: str, db: Session = Depends(get_db)):

    bulan_lower = bulan.lower()

    if bulan_lower not in MONTH_NAMES:
        return {"error": "Nama bulan tidak valid!"}

    month_number = MONTH_NAMES[bulan_lower]
    year = 2024    

    # tanggal awal bulan
    start_date = date(year, month_number, 1)

    # tanggal akhir bulan (exclusive)
    if month_number == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month_number + 1, 1)

    # QUERY ambil data per jam tayang
    query = text("""
        SELECT
            m.id AS movie_id,
            m.title,
            j.jam,
            COUNT(o.id) AS total_tiket
        FROM orders o
        JOIN jadwal j ON o.jadwal_id = j.id
        JOIN movies m ON j.movie_id = m.id
        WHERE o.transaction_date >= :start_date
        AND o.transaction_date < :end_date
        GROUP BY m.id, m.title, j.jam
        ORDER BY m.id, total_tiket DESC;
    """)

    rows = db.execute(query, {
        "start_date": start_date,
        "end_date": end_date
    }).mappings().all()

    # kelompokkan data per film
    output = {}

    for r in rows:
        mid = r["movie_id"]
        if mid not in output:
            output[mid] = {
                "movie_id": mid,
                "title": r["title"],
                "list_jadwal": []
            }

        output[mid]["list_jadwal"].append({
            "jam": str(r["jam"]),
            "tiket": r["total_tiket"]
        })

    # tentukan jam terpopuler per film
    for mv in output.values():
        sorted_jam = sorted(mv["list_jadwal"], key=lambda x: x["tiket"], reverse=True)
        mv["jam_terpopuler"] = sorted_jam[0]["jam"]
        mv["total_tiket_jam_terpopuler"] = sorted_jam[0]["tiket"]

    return {
        "bulan": bulan,
        "periode": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        },
        "total_film": len(output),
        "data": list(output.values())
    }


# 3. pengaruh perbedaan harga dan promo

def hasil_kesimpulan(t_change, p_change, h_change):
    """Menerjemahkan persentase perubahan menjadi kalimat kesimpulan."""
    if t_change is None:
        return "Data transaksi tanpa promo tidak tersedia untuk analisis."

    kesimpulan = []
    
    # Efektivitas berdasarkan transaksi
    if t_change is not None:
        if t_change > 0:
            kesimpulan.append(f"Promo meningkatkan jumlah transaksi sebesar {t_change}%")
        else:
            kesimpulan.append(f"Promo tidak efektif, transaksi turun {abs(t_change)}%")

    # Efektivitas berdasarkan pendapatan
    if p_change is not None:
        if p_change > 0:
            kesimpulan.append(f"Promo meningkatkan pendapatan sebesar {p_change}%")
        else:
            kesimpulan.append(f"Promo menurunkan pendapatan sebesar {abs(p_change)}%")

    # Efektivitas harga (Biaya)
    if h_change is not None:
        if h_change < 0:
            kesimpulan.append(f"Harga rata-rata turun {abs(h_change)}% saat promo (indikasi diskon efektif).")
        else:
            kesimpulan.append(f"Harga rata-rata naik {h_change}% meski ada promo (perlu evaluasi).")

    return " | ".join(kesimpulan)


# --- ROUTER ANALISIS EFEKTIVITAS PROMO ---

@router.get("/analisis/promo-efektivitas")
def analisis_efektivitas_promo(db: Session = Depends(get_db)):
    # 1. KUERI SQL PALING AMAN: Mengambil kolom mentah
    query = text("""
        SELECT 
            id,
            promo_name,
            final_price
        FROM orders;
    """)

    try:
        rows = db.execute(query).mappings().all()
    except Exception as e:
        # Jika SELECT mentah gagal, ini adalah masalah koneksi/server fatal
        raise HTTPException(status_code=500, detail=f"Gagal mengambil data orders mentah dari database: {e}")

    # 2. INISIALISASI DAN AGREGASI DI PYTHON
    tanpa = {"total_transaksi": 0, "total_pendapatan": 0.0, "harga_list": []}
    dengan = {"total_transaksi": 0, "total_pendapatan": 0.0, "harga_list": []}

    for r in rows:
        try:
            # Penanganan data NULL/Kotor: Mengubah harga menjadi float aman
            price = float(r["final_price"]) if r["final_price"] is not None else 0.0
            promo_name = r["promo_name"]
            
            # Penentuan Kategori: BUKAN 'NO PROMO'
            is_promo = (promo_name is not None and promo_name != 'NO PROMO')
    
            target = dengan if is_promo else tanpa
            
            target["total_transaksi"] += 1
            target["total_pendapatan"] += price
            target["harga_list"].append(price)

        except Exception as e:
            # Mengabaikan baris data yang kotor/bermasalah
            continue
            
    # 3. PERHITUNGAN AVG DAN FORMAT OUTPUT
    
    t_tanpa = tanpa["total_transaksi"]
    t_dengan = dengan["total_transaksi"]
    
    # Hitung AVG (Rata-rata)
    tanpa['avg_harga'] = sum(tanpa['harga_list']) / t_tanpa if t_tanpa > 0 else 0.0
    dengan['avg_harga'] = sum(dengan['harga_list']) / t_dengan if t_dengan > 0 else 0.0
    
    # Format output final (menghilangkan list harga)
    tanpa_final = {k: v for k, v in tanpa.items() if k != 'harga_list'}
    dengan_final = {k: v for k, v in dengan.items() if k != 'harga_list'}
    
    # 4. PERHITUNGAN PERSENTASE
    
    t_change, p_change, h_change = None, None, None

    if t_tanpa > 0:
        # Persentase Perubahan Volume Transaksi
        t_change = round(((t_dengan - t_tanpa) / t_tanpa) * 100, 2)
        
        # Persentase Perubahan Pendapatan
        p_tanpa = tanpa_final["total_pendapatan"]
        if p_tanpa > 0:
            p_change = round(((dengan_final["total_pendapatan"] - p_tanpa) / p_tanpa) * 100, 2)
            
        # Persentase Perubahan Harga Rata-rata
        h_tanpa = tanpa_final["avg_harga"]
        if h_tanpa > 0:
            h_change = round(((dengan_final["avg_harga"] - h_tanpa) / h_tanpa) * 100, 2)
    

    return {
        "ringkasan": {
            "transaksi_promo_vs_tanpa": t_change,
            "pendapatan_promo_vs_tanpa": p_change,
            "perbedaan_rata_rata_harga": h_change
        },
        "analisis": {
            "tanpa_promo": tanpa_final,
            "dengan_promo": dengan_final,
        },
        "kesimpulan": hasil_kesimpulan(t_change, p_change, h_change)
    }




# 4. pilihan kursi paling populer
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import APIRouter, Depends, HTTPException

# Fungsi utilitas untuk kueri Top 5 Kursi (Disimpan di sini)
def get_top5_kursi_query(start_date: date, end_date: date):
    # Menggunakan CONCAT(os.row, os.col) dan tabel orders/order_seats yang benar
    return text("""
        SELECT
            CONCAT(os.row, os.col) AS kursi_kode,
            COUNT(os.id) AS jumlah
        FROM order_seats os
        JOIN orders o ON os.order_id = o.id
        WHERE DATE(o.transaction_date) >= :start_date
          AND DATE(o.transaction_date) <= :end_date 
        GROUP BY kursi_kode
        ORDER BY jumlah DESC
        LIMIT 5;
    """)

@router.get("/kursipopuler/{mode}")
def kursi_paling_populer(
    mode: str,  # "harian", "mingguan", "bulanan"
    tanggal: str = None, # Jadikan opsional, akan dihitung jika weekly/monthly
    db: Session = Depends(get_db)
):
    """
    Menampilkan Top 5 kursi terpopuler berdasarkan mode (harian, mingguan, bulanan)
    """
    
    # 1. Tentukan Tanggal Dasar
    if tanggal:
        try:
            tgl = datetime.strptime(tanggal, "%Y-%m-%d").date() # Konversi ke date object
        except ValueError:
            raise HTTPException(status_code=400, detail="Format tanggal harus YYYY-MM-DD")
    else:
        # Jika tanggal tidak diberikan, gunakan hari ini atau 1 Desember 2024
        tgl = date(2024, 12, 1)

    # 2. Tentukan Range berdasarkan Mode
    if mode == "harian":
        start = tgl
        end = tgl
    elif mode == "harian":
        start = tgl  # tgl adalah objek date(YYYY, MM, DD)
        end = tgl    # Akhir range juga tanggal yang sama

    elif mode == "mingguan":
        raise HTTPException(status_code=400, detail="Gunakan endpoint /kursipopuler/weekly statis")
        
    elif mode == "bulanan":
        start = tgl.replace(day=1)
        if start.month == 12:
            end = date(start.year, 12, 31)
        else:
            end = date(start.year, start.month + 1, 1) - timedelta(days=1)
            
    else:
        raise HTTPException(status_code=400, detail="Mode harus harian/bulanan")

    # 3. Eksekusi Query
    query = get_top5_kursi_query(start, end)
    result = db.execute(query, {"start_date": start, "end_date": end}).mappings().all()

    if not result:
        return {"mode": mode, "message": f"Tidak ada data transaksi untuk range {start} s/d {end}"}

    return {
        "mode": mode,
        "tanggal_awal": start.isoformat(),
        "tanggal_akhir": end.isoformat(),
        "top_5_kursi": [
            {"kursi_kode": row.kursi_kode, "jumlah_pemesanan": row.jumlah}
            for row in result
        ]
    }
    