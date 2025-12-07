import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from datetime import date

# Import app utama (sesuaikan path ini dengan main.py kamu)
# Jika main.py ada di folder app, gunakan "from app.main import app"
# Jika main.py ada di root, gunakan "from main import app"
from app.main import app 

# Import dependency get_db agar bisa kita override
from app.database import get_db

# Membuat Client Test
client = TestClient(app)

# --- FIXTURE: Mock Database ---
# Ini adalah "Database Palsu" yang akan kita pakai
@pytest.fixture
def mock_db_session():
    return MagicMock()

# Ini fungsi untuk menukar database asli dengan database palsu saat test jalan
@pytest.fixture
def override_get_db(mock_db_session):
    def _override_get_db():
        try:
            yield mock_db_session
        finally:
            pass
    app.dependency_overrides[get_db] = _override_get_db
    yield
    # Kembalikan ke database asli setelah test selesai
    app.dependency_overrides = {}


# ==========================================
# TEST 1: Analisis Pendapatan Film (Top Revenue)
# ==========================================
def test_get_top_revenue_films_success(mock_db_session, override_get_db):
    # 1. SETUP: Siapkan data palsu
    # Kita pura-pura database mengembalikan 1 film juara
    mock_result = MagicMock()
    mock_result.title = "Avengers: Endgame"
    mock_result.total_revenue = 5000000
    
    # Konfigurasi mock agar mengembalikan data ini saat di-query
    mock_db_session.query.return_value.join.return_value.join.return_value.filter.return_value.filter.return_value.group_by.return_value.order_by.return_value.first.return_value = mock_result

    # 2. ACTION: Panggil endpoint lewat TestClient
    response = client.get("/analisis/top-revenue-films?period=minggu")

    # 3. ASSERT: Cek apakah hasilnya benar
    assert response.status_code == 200
    data = response.json()
    
    # Cek struktur respon
    assert "hasil_analisis" in data
    assert data["request_period"] == "minggu"
    
    # Cek apakah datanya sesuai dengan mock kita
    # Karena kita looping 5 minggu, kita cek salah satunya
    first_item = data["hasil_analisis"][0]
    assert first_item["film_juara"] == "Avengers: Endgame"
    assert first_item["pendapatan"] == 5000000

def test_get_top_revenue_films_no_param(override_get_db):
    # Test kalau user lupa isi param period
    response = client.get("/analisis/top-revenue-films") # Tanpa ?period=...
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "info"
    assert "Tolong pilih periode dulu" in data["pesan"]


# ==========================================
# TEST 2: Analisis Pelanggan (Top Customer)
# ==========================================
def test_get_top_customers_success(mock_db_session, override_get_db):
    # 1. SETUP: Siapkan data pelanggan juara palsu
    mock_member = MagicMock()
    mock_member.nama = "Budi Santoso"
    mock_member.member_id = 101
    mock_member.total_transaksi = 5

    # Rantai query mock yang panjang (sesuai kode aslimu)
    mock_db_session.query.return_value.join.return_value.filter.return_value.filter.return_value.group_by.return_value.order_by.return_value.first.return_value = mock_member

    # 2. ACTION: Panggil endpoint
    response = client.get("/analisis/top-customers?period=bulan")

    # 3. ASSERT
    assert response.status_code == 200
    data = response.json()
    
    # Cek hasil
    assert data["request_period"] == "bulan"
    # Karena period='bulan', cuma ada 1 item di list hasil
    assert len(data["hasil_analisis"]) == 1
    
    juara = data["hasil_analisis"][0]
    assert juara["pelanggan_juara"] == "Budi Santoso"
    assert juara["jumlah_transaksi"] == 5


# ==========================================
# TEST 3: Analisis Hari Teramai (Most Busiest Day)
# ==========================================
def test_get_busiest_day_success(mock_db_session, override_get_db):
    # 1. SETUP: Siapkan 2 jenis data mock
    
    # Mock A: Top Dates (Tanggal Teramai)
    mock_date_1 = MagicMock()
    mock_date_1.transaction_date = date(2024, 12, 11)
    mock_date_1.total_tiket = 150
    
    # Mock B: Top Days (Hari Teramai - Senin/Selasa)
    mock_day_1 = MagicMock()
    mock_day_1.nama_hari = "Wednesday"
    mock_day_1.total_tiket = 500

    # Karena di fungsi aslimu ada 2 kali query db.query(...).all(),
    # Kita harus mock `side_effect` agar query pertama dpt Mock A, query kedua dpt Mock B
    
    # Query 1 (Top Dates) & Query 2 (Top Days)
    # Ini trik mock tingkat lanjut karena querynya mirip
    mock_db_session.query.return_value.filter.return_value.filter.return_value.group_by.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_date_1]
    mock_db_session.query.return_value.filter.return_value.filter.return_value.group_by.return_value.order_by.return_value.all.return_value = [mock_day_1]

    # 2. ACTION
    response = client.get("/analisis/most-busiest-day?bulan=12&tahun=2024")

    # 3. ASSERT
    assert response.status_code == 200
    data = response.json()
    
    # Cek Kesimpulan
    assert "Most Busiest Time Analysis" in data["kesimpulan"]["judul"]
    assert "Wednesday" in data["kesimpulan"]["tanggal_tersibuk"]
    assert "150" in str(data["kesimpulan"]["tanggal_tersibuk"]) # Cek angka tiket
    
    # Cek Detail
    assert len(data["top_5_tanggal_teramai"]) == 1
    assert data["ranking_hari_teramai"][0]["nama_hari"] == "Wednesday"