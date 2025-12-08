# 🎬 Movie Booking System API

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.95%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-ORM-red?style=for-the-badge&logo=sqlalchemy&logoColor=white)
![MySQL](https://img.shields.io/badge/Database-MySQL-orange?style=for-the-badge&logo=mysql&logoColor=white)
![Pytest](https://img.shields.io/badge/Testing-Pytest-yellow?style=for-the-badge&logo=pytest&logoColor=black)

API Backend yang kuat untuk sistem manajemen bioskop. Proyek ini mencakup fitur lengkap mulai dari manajemen film oleh admin, transaksi pemesanan tiket oleh user, hingga analisis data bisnis (Business Intelligence).

---

## 🚀 Fitur Utama

### 🛠 Admin 
* **Manajemen Film:** CRUD data film (Judul, Genre, Durasi, Harga).
* **Manajemen Studio:** Pengaturan layout kursi (Baris & Kolom).
* **Manajemen Jadwal:** Penjadwalan tayang film.
* **Membership System:** Menambahkan keanggotaan.

### 👤 User 
* **Katalog Film:** Menampilkan film yang sedang tayang
* **Katalog Jadwal:** Menampilkan jadwal terkini
* **Katalog Kursi:** Menampilkan pilihan kursi
* **Membership System:** Validasi keanggotaan.
* **Keranjang Belanja (Cart):**
  * Validasi kursi (mencegah double booking).
  * Validasi item duplikat di keranjang.
* **Checkout & Pembayaran:**
  * Mendukung metode pembayaran **CASH** (dengan perhitungan kembalian).
  * Mendukung metode **QRIS/Cashless**.
  * Perhitungan diskon otomatis (Promo Bulk Buy, Tanggal Cantik, dll).
* **Tiket:** Generasi kode order unik (`ORD-XXXXXX`).

### 📊 Analisis Data (Analytics)
API khusus untuk melihat performa bisnis menggunakan **SQLAlchemy & Pandas**:
* **Top Movies:** Film terlaris berdasarkan penjualan tiket (Harian/Mingguan/Bulanan).
* **Peak Hours:** Analisis jam tayang paling ramai.
* **Payment Preference:** Statistik metode pembayaran favorit user.
* **Genre Popularity:** Tren genre film yang paling diminati.

---

## 📂 Struktur Proyek

```text
movie-booking-system/
├── app/
│   ├── __init__.py
│   ├── main.py              # Entry point aplikasi FastAPI
│   ├── database.py          # Koneksi Database
│   ├── models.py            # Definisi Tabel & Script Seeding
│   └── routers/             # Endpoint API
│       ├── __init__.py
│       ├── admin_film.py    # API Admin (Film, Studio, Jadwal)
│       ├── admin_analytics.py # API Analisis Data
│       └── user_transaction.py # API Cart & Checkout
├── tests/
│   ├── test_analisis_lulu.py # Unit Testing (SQLite In-Memory)
├── .env                     # Konfigurasi Environment (Password DB)
├── requirements.txt         # Daftar Library Python
└── README.md                # Dokumentasi Proyek
