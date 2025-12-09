#analsis.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta

from app.database import get_db
from sqlalchemy import text

router = APIRouter()

MONTH_NAMES = {
    "januari": 1, "februari": 2, "maret": 3, "april": 4, "mei": 5, "juni": 6,
    "juli": 7, "agustus": 8, "september": 9, "oktober": 10, "november": 11, "desember": 12
}


# ==============================================================================
# 1. ANALISIS EFEKTIVITAS PROMO (LOGIKA PYTHON STABIL)
# ==============================================================================

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


@router.get("/analisis/promo-efektivitas")
def analisis_efektivitas_promo(db: Session = Depends(get_db)):
    
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
        raise HTTPException(status_code=500, detail=f"Gagal mengambil data orders mentah dari database: {e}")

    # INISIALISASI DAN AGREGASI DI PYTHON
    tanpa = {"total_transaksi": 0, "total_pendapatan": 0.0, "harga_list": []}
    dengan = {"total_transaksi": 0, "total_pendapatan": 0.0, "harga_list": []}

    for r in rows:
        try:
            # Penanganan data NULL/Kotor
            price = float(r["final_price"]) if r["final_price"] is not None else 0.0
            promo_name = r["promo_name"]
            
            is_promo = (promo_name is not None and promo_name != 'NO PROMO')
    
            target = dengan if is_promo else tanpa
            
            target["total_transaksi"] += 1
            target["total_pendapatan"] += price
            target["harga_list"].append(price)

        except Exception:
            continue
            
    t_tanpa = tanpa["total_transaksi"]
    t_dengan = dengan["total_transaksi"]
    
    # Hitung AVG (Perlindungan ZeroDivisionError sudah aman)
    tanpa['avg_harga'] = sum(tanpa['harga_list']) / t_tanpa if t_tanpa > 0 else 0.0
    dengan['avg_harga'] = sum(dengan['harga_list']) / t_dengan if t_dengan > 0 else 0.0
    
    tanpa_final = {k: v for k, v in tanpa.items() if k != 'harga_list'}
    dengan_final = {k: v for k, v in dengan.items() if k != 'harga_list'}
    
    t_change, p_change, h_change = None, None, None

    if t_tanpa > 0:
        t_change = round(((t_dengan - t_tanpa) / t_tanpa) * 100, 2)
        
        p_tanpa = tanpa_final["total_pendapatan"]
        if p_tanpa > 0:
            p_change = round(((dengan_final["total_pendapatan"] - p_tanpa) / p_tanpa) * 100, 2)
            
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


# ==============================================================================
# 2. KURSI PALING POPULER (FIXED: CONCAT -> ||)
# ==============================================================================

# Fungsi utilitas untuk kueri Top 5 Kursi
def get_top5_kursi_query(start_date: date, end_date: date):
    return text("""
        SELECT
            CONCAT(os.row, os.col) AS kursi_kode,
            COUNT(os.id) AS jumlah_pemesanan
        FROM order_seats os
        JOIN orders o ON os.order_id = o.id
        WHERE DATE(o.transaction_date) >= :start_date
          AND DATE(o.transaction_date) <= :end_date 
        GROUP BY kursi_kode
        ORDER BY jumlah_pemesanan DESC
        LIMIT 5;
    """)


@router.get("/kursipopuler/{mode}")
def kursi_paling_populer(
    mode: str, 
    tanggal: str = None, 
    db: Session = Depends(get_db)
):
    
    mode_map = {"harian": 0, "mingguan": 1, "bulanan": 2}
    if mode not in mode_map:
        raise HTTPException(status_code=400, detail="Mode harus harian, mingguan, atau bulanan.")

    # 1. Tentukan Tanggal Dasar
    if tanggal:
        try:
            tgl = datetime.strptime(tanggal, "%Y-%m-%d").date() 
        except ValueError:
            raise HTTPException(status_code=400, detail="Format tanggal harus YYYY-MM-DD")
    else:
        tgl = date.today() # Gunakan hari ini jika tidak ada tanggal

    # 2. Tentukan Range
    if mode == "harian":
        start = tgl
        end = tgl

    elif mode == "mingguan":
        # Menemukan hari Minggu sebelumnya (Hari ke-6, 0=Senin, 6=Minggu)
        start = tgl - timedelta(days=tgl.weekday()) # Senin
        end = start + timedelta(days=6) # Minggu

    elif mode == "bulanan":
        start = tgl.replace(day=1)
        # Menghitung hari terakhir bulan
        if start.month == 12:
            end = date(start.year, 12, 31)
        else:
            end = date(start.year, start.month + 1, 1) - timedelta(days=1)
            
    # 3. Eksekusi Query
    query = get_top5_kursi_query(start, end)
    result = db.execute(query, {"start_date": start, "end_date": end}).mappings().all()


    return {
        "mode": mode,
        "tanggal_awal": start.isoformat(),
        "tanggal_akhir": end.isoformat(),
        "top_5_kursi": [
            {"kursi_kode": row.kursi_kode, "jumlah_pemesanan": row.jumlah_pemesanan}
            for row in result
        ]
    }