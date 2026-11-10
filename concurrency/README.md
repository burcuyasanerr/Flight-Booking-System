# 🔒 Eşzamanlılık (Concurrency) & Koltuk Kilitleme Modülü (`concurrency/`)

Bu modül, **Flight Ticket Purchasing System (Team 19)** projesinin aktif koltuk seçiminde eşzamanlılık (concurrency) çakışma yönetimini, koltuk kilitleme/bırakma yaşam döngüsünü ve yarış koşulu (race condition) korumasını sağlar.

---

## 📌 Özellikler

- **Optimistic Locking (İyimser Kilitleme):** 
  - `flight_seats` tablosundaki `version` sayacı ile satır bazında çakışma tespiti.
  - Aynı anda aynı koltuğu seçen $N$ kullanıcıdan yalnızca birincisi kilidi alır; diğerleri veritabanı bütünlüğü bozulmadan sürüm çakışması (`VERSION_MISMATCH_RACE_CONDITION`) hatası alır.
- **Zaman Aşımı Koruması (Lock Timeout):**
  - Kilit süresi SQL tarafında `now() + INTERVAL '10 minutes'` ile atanır. Sunucu ve veritabanı saat dilimi farklarından etkilenmez.
  - Süresi dolan kilitler koltuk haritasında anında `AVAILABLE` olarak değerlendirilir.
- **Pessimistic Locking Desteği:**
  - Kritik transaction'lar için `SELECT ... FOR UPDATE` alternatifi.
- **Atomik Satın Alma Transaction'ı:**
  - Ödeme tamamlandığında koltuğu `BOOKED` yapma ve `bookings` tablosuna bilet yazma işlemleri tek bir ACID transaction içinde gerçekleşir. Kilit süresi dolmuşsa işlem otomatik `ROLLBACK` edilir.
- **Eşzamanlılık Simülatörü & Stres Testi:**
  - `threading.Barrier` ile aynı milisaniyede 10+ kullanıcının aynı koltuğa yüklendiği senaryoyu test eden simülasyon motoru.

---

## 📂 Klasör Mimarisi

```text
concurrency/
├── __init__.py           # Paket dışa aktarımları
├── config.py             # Veritabanı ve kilit süresi ayarları
├── db.py                 # Thread-safe bağlantı havuzu (ThreadedConnectionPool)
├── models.py             # Pydantic veri modelleri (SeatInfo, LockResult, BookingResult)
├── lock_manager.py       # Optimistic & Pessimistic kilitleme mantığı
├── simulator.py          # Yarış koşulu (race condition) simülatörü ve stres testi
├── cli.py                # Komut satırı yönetim aracı
├── requirements.txt      # Bağımlılıklar (psycopg2-binary, pydantic)
├── README.md             # Kullanım ve entegrasyon dokümantasyonu
└── tests/
    └── test_concurrency.py # Birim ve çoklu iş parçacığı entegrasyon testleri
```

---

## 🚀 Kurulum ve Yapılandırma

Gerekli Python paketlerini yüklemek için:

```bash
pip install -r requirements.txt
```

Veritabanı bağlantı parametreleri ortam değişkenleri (`.env`) veya varsayılanlar üzerinden yönetilir:
- `DB_HOST`: `localhost` (Varsayılan)
- `DB_PORT`: `5432` (Varsayılan)
- `DB_NAME`: `flight_booking` (Varsayılan)
- `DB_USER`: `postgres` (Varsayılan)
- `DB_PASSWORD`: Veritabanı şifreniz

---

## 💻 Backend İçin Entegrasyon Kılavuzu

Backend ekibi koltuk kilitleme ve kontrol işlemlerini doğrudan `SeatLockManager` üzerinden çağırabilir:

### 1. Koltuk Haritasını Getirme

```python
from concurrency import SeatLockManager

lock_mgr = SeatLockManager()
seats = lock_mgr.get_flight_seats(flight_id=1)

for seat in seats:
    print(f"Koltuk: {seat.seat_number}, Durum: {seat.effective_status.value}, Sürüm: {seat.version}")
```

### 2. Koltuk Kilitleme (Optimistic Lock)

```python
result = lock_mgr.lock_seat_optimistic(
    seat_id=14,
    session_id="user_session_abc123",
    expected_version=1,
    lock_minutes=10
)

if result.success:
    print(f"Koltuk tutuldu! Kilit bitiş zamanı: {result.locked_until}")
else:
    print(f"Koltuk tutulamadı: {result.message} (Neden: {result.conflict_reason})")
```

### 3. Kullanıcı Vazgeçtiğinde Kilidi Bırakma

```python
rel_result = lock_mgr.release_seat_lock(seat_id=14, session_id="user_session_abc123")
```

### 4. Bilet Satın Alma (Atomik Kesinleştirme)

```python
booking_res = lock_mgr.confirm_seat_booking(
    seat_id=14,
    session_id="user_session_abc123",
    user_id=1,
    pnr_code="TK79AB",
    passenger_first_name="Ahmet",
    passenger_last_name="Yılmaz",
    passenger_identity_number="12345678901",
    passenger_email="ahmet.yilmaz@example.com",
    passenger_phone="+905551112233",
    total_price=1450.00
)
```

---

## 🛠️ Komut Satırı (CLI) Kullanımı

Modül dizini içerisinden doğrudan CLI komutları çalıştırılabilir:

### 1. Veritabanı Bağlantı Durumu
```bash
python cli.py --status
```

### 2. Uçuş Koltuklarını Listeleme
```bash
python cli.py --list-seats --flight 1
```

### 3. Eşzamanlı Yarış Koşulu (Race Condition) Simülasyonu
Aynı anda 10 kullanıcının aynı koltuğu seçmeye çalıştığı senaryo:
```bash
python cli.py --simulate --seat 2 --users 10
```

### 4. Süresi Dolan Kilitleri Temizleme
```bash
python cli.py --cleanup
```

---

## 🧪 Testlerin Çalıştırılması

```bash
python -m unittest tests/test_concurrency.py
```
