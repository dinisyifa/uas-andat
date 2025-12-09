# 🎬 Movie Booking System API

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.95%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-ORM-red?style=for-the-badge&logo=sqlalchemy&logoColor=white)
![MySQL](https://img.shields.io/badge/Database-MySQL-orange?style=for-the-badge&logo=mysql&logoColor=white)
![Pytest](https://img.shields.io/badge/Testing-Pytest-yellow?style=for-the-badge&logo=pytest&logoColor=black)

Proyek ini mencakup fitur lengkap mulai dari manajemen film oleh admin, transaksi pemesanan tiket oleh user, hingga analisis data bisnis.

---

## 🚀 Fitur Utama

### 🛠 Admin 
* **Manajemen Film:** Melakukan CRUD (Tambah, Lihat, Ubah, Hapus) detail film (Judul, Durasi, Sutradara, Rating). Harga Tiket (price) secara otomatis ditetapkan oleh sistem berdasarkan durasi film.
* **Manajemen Studio:** Melakukan CRUD pengaturan studio (Nama, Kode, Kapasitas). Input utama adalah jumlah Baris (rows) dan Kolom (cols) untuk menentukan layout kursi.
* **Manajemen Jadwal:** Membuat, melihat, memperbarui, dan menghapus jadwal tayang. Setiap jadwal harus terhubung dengan satu Movie Code dan satu Studio Code yang valid. Pencegahan Konflik: Saat menambahkan jadwal baru, sistem melakukan validasi penting:
Memastikan Studio tidak mengalami bentrok waktu tayang pada tanggal yang sama, dengan memperhitungkan durasi film (end_time).
* **Membership System:** Melakukan CRUD untuk jenis-jenis keanggotaan. Setiap jenis keanggotaan memiliki Kode unik (misalnya, MEM001) dan Nama. Ini mendasari sistem diskon dan validasi keanggotaan di sisi transaksi.

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
* **Film Terlaris:** Film terlaris berdasarkan penjualan tiket (Harian/Mingguan/Bulanan).
* **Jam Tayang Puncak:** Menganalisis dan menentukan Jam Tayang Paling Ramai untuk setiap film, membantu optimasi jadwal..
* **Popularitas Genre:** Mengukur Tren Genre Film yang diminati audiens, disajikan dalam persentase kontribusi terhadap total tiket terjual
* **Kursi Paling Populer:** Menampilkan Top 5 Kursi yang paling sering dipesan, membantu memahami preferensi layout penonton.
* **Efektivitas Promo: **Membandingkan kinerja transaksi dengan vs. tanpa promo.
* Pendapatan Film: **Mengidentifikasi Film Juara Pendapatan (Pendapatan Tertinggi) per periode (harian, mingguan, bulanan), fokus pada metrik finansial.
* Pelanggan Terbaik: **Mengidentifikasi Pelanggan Ter-Rajin (Top Customers) berdasarkan frekuensi order terbanyak per periode (mingguan atau bulanan).
* Hari Tersibuk: **Menentukan Tanggal Spesifik dan Nama Hari yang paling sibuk/ramai (berdasarkan total tiket terjual).

---

## 📂 Struktur Proyek

```text
movie-booking-system/
├── .env 
├── app/
│   ├── __init__.py
│   ├── main.py # Entry point aplikasi FastAPI
│   ├── database.py # Koneksi Database
│   ├── models.py # Definisi Tabel & Script Seeding
│   └── routers/ # Endpoint API
│       ├── __init__.py
│       ├── admin_film.py # API Admin (Film)
│       ├── admin_jadwal.py # API Admin (Jadwal)
│       ├── analisis.py 
│       ├── user_catalog.py # API User (Katalog Film)
│       └── user_transaction.py # API User (Transaksi/Checkout)
├── tests/
│   ├── __init__.py
│   ├── test_admin_film.py # Unit Testing
│   ├── test_admin_jadwal.py # Unit Testing
│   ├── test_user_catalog.py # Unit Testing
│   └── test_user_transaction.py # Unit Testing
├── .gitignore
├── README.md # Dokumentasi Proyek
└── requirements.txt # Daftar Library Python
