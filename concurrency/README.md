# 🔒 Eşzamanlılık (Concurrency) & Koltuk Kilitleme Modülü (`concurrency/`)

Bu modül, **Flight Ticket Purchasing System (Team 19)** projesinin aktif koltuk seçiminde eşzamanlılık (concurrency) çakışma yönetimini, koltuk kilitleme/bırakma yaşam döngüsünü ve yarış koşulu (race condition) korumasını sağlar.

---

## 📌 Özellikler ve Mimari Kararlar

- **Optimistic Locking (İyimser Kilitleme - Önerilen ve Birincil Strateji):** 
  - `flight_seats` tablosundaki `version` sayacı ile satır bazında çakışma tespiti yapılır.
  - Aynı anda aynı koltuğu seçen $N$ kullanıcıdan yalnızca birincisi kilidi alır; diğerleri veritabanı bütünlüğü bozulmadan sürüm çakışması (`VERSION_MISMATCH_RACE_CONDITION`) hatası alır. Çift satış veritabanı seviyesinde imkansızdır.
  - Kullanıcı kendi geçerli kilidini tekrar seçtiğinde kilit süresi otomatik olarak uzatılır (yenilenir).
- **Zaman Aşımı Koruması (Lock Timeout):**
  - Kilit süresi SQL tarafında doğrudan `now() + INTERVAL '10 minutes'` ile atanır. Sunucu ve veritabanı arasındaki saat dilimi farklarından etkilenmez.
  - Süresi dolan kilitler koltuk haritasında anında `AVAILABLE` olarak değerlendirilir.
- **Kötümser Kilitleme Desteği (Pessimistic Locking):**
  - Yüksek rekabetli veya anlık kritik transaction'lar için `SELECT ... FOR UPDATE` alternatifi sunulur (`lock_seat_pessimistic`).
- **Oturum Başına Kilit Sınırı:**
  - Tek bir kullanıcının veya botun tüm uçak koltuklarını bloke etmesini önlemek amacıyla oturum başına azami kilit sınırı (`max_seats_per_session=9`) uygulanır.
- **Güvenli Fiyat ve Atomik Satın Alma:**
  - `confirm_seat_booking` fonksiyonu dışarıdan fiyat parametresi kabul etmez; fiyatı transaction içinde doğrudan `flights.base_price * flight_seats.price_multiplier` formülüyle hesaplar.
  - Bilet kaydında PNR çakışması (UniqueViolation) olursa transaction iptal edilmez; `SAVEPOINT` mekanizmasıyla yeni bir PNR üretilerek otomatik olarak yeniden denenir (`max_retries`).
- **Uçuş Geçerlilik Kontrolü:**
  - İptal edilmiş (`CANCELLED`) veya kalkış zamanı geçmiş (`departure_time <= now()`) uçuşlarda koltuk kilitleme ve bilet satışı engellenir.
- **Arka Plan Kilit Temizleyici (Background Cleaner):**
  - Süresi dolan kilitlerin veritabanında birikmemesi için periyodik temizleme iş parçacığı (`BackgroundLockCleaner`) sunulur.

---

## 📂 Klasör Mimarisi

```text
concurrency/
├── __init__.py           # Paket dışa aktarımları
├── config.py             # Veritabanı (.env destekli) ve kilit yapılandırması
├── db.py                 # Thread-safe bağlantı havuzu (ThreadedConnectionPool)
├── models.py             # Pydantic veri modelleri (SeatInfo, LockResult, BookingResult)
├── lock_manager.py       # Optimistic & Pessimistic kilitleme mantığı ve temizleyici
├── simulator.py          # Yarış koşulu (race condition) simülatörü ve stres testi
├── cli.py                # Komut satırı yönetim aracı (--lock, --release, --simulate vb.)
├── requirements.txt      # Bağımlılıklar (psycopg2-binary, pydantic, python-dotenv)
├── README.md             # Dokümantasyon
└── tests/
    └── test_concurrency.py # 10 adet birim ve çoklu iş parçacığı entegrasyon testi
```

---

## 🚀 Kurulum ve Yapılandırma

Gerekli Python paketlerini yüklemek için:

```bash
pip install -r requirements.txt
```

Ortam değişkenleri kök dizindeki `.env` dosyasından veya ortamdan okunur (`python-dotenv`):
- `DB_HOST`: `localhost`
- `DB_PORT`: `5432`
- `DB_NAME`: `flight_booking`
- `DB_USER`: `postgres`
- `DB_PASSWORD`: Veritabanı şifreniz
- `DB_MIN_CONN`: `5` (Bağlantı havuzu minimum bağlantı)
- `DB_MAX_CONN`: `20` (Maksimum bağlantı)
- `MAX_SEATS_PER_SESSION`: `9` (Oturum başına azami kilit sınırı)

---

## 💻 Backend İçin Entegrasyon Kılavuzu

Backend ekibi koltuk kilitleme ve kontrol işlemlerini doğrudan `concurrency` modülü üzerinden kullanabilir:

### 1. Koltuk Haritasını Listeleme

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
    passenger_first_name="Ahmet",
    passenger_last_name="Yılmaz",
    passenger_identity_number="12345678901",
    passenger_email="ahmet.yilmaz@example.com",
    passenger_phone="+905551112233"
)

if booking_res.success:
    print(f"Satış tamam! PNR: {booking_res.pnr_code}, Tutar: {booking_res.total_price} TL")
else:
    print(f"Satış başarısız: {booking_res.message} (Hata: {booking_res.error_code})")
```

### 5. Arka Planda Kilit Temizleyicisini Çalıştırma

Backend ayağa kalkarken süresi dolmuş kilitleri temizleyen arka plan işi başlatılabilir:

```python
from concurrency.lock_manager import BackgroundLockCleaner, SeatLockManager

lock_mgr = SeatLockManager()
cleaner = BackgroundLockCleaner(lock_mgr, interval_seconds=60)
cleaner.start()  # Arka planda daemon thread olarak çalışır

# Uygulama kapanırken:
# cleaner.stop()
```

---

## 🛠️ Komut Satırı (CLI) Kullanımı

```bash
# Veritabanı bağlantı durumunu denetle
python -m concurrency.cli --status

# Koltuk haritasını listele
python -m concurrency.cli --list-seats --flight 1

# Koltuk kilitle
python -m concurrency.cli --lock --seat 2 --session test_user

# Kilidi serbest bırak
python -m concurrency.cli --release --seat 2 --session test_user

# 10 kullanıcının aynı koltuğu kapmaya çalıştığı yarış simülasyonunu çalıştır
python -m concurrency.cli --simulate --seat 2 --users 10

# Süresi dolmuş kilitleri temizle
python -m concurrency.cli --cleanup
```

---

## 🧪 Testlerin Çalıştırılması

```bash
python -m unittest discover -s concurrency/tests
```
