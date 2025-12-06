from fastapi import APIRouter, Depends
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


# 3. Pilihan kursi paling populer

# 4. Pendapatan per film

# 5. Perilaku pelanggann (member paling sering beli)