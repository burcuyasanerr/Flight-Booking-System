# ✈️ PNR Üretimi ve Bilet PDF Çıktısı Modülü (`ticket_pdf/`)

Bu modül, **Flight Ticket Purchasing System (Team 19)** projesinin rezervasyon (PNR) kodu üretimi, format doğrulaması ve elektronik uçuş bileti / biniş kartı (Boarding Pass) PDF çıktısı oluşturma sorumluluğunu yerine getirir.

---

## 📌 Özellikler

- **Güvenli PNR Üretimi:** 
  - İnsan gözüyle karıştırılabilecek karakterleri (`0`, `O`, `1`, `I`) otomatik olarak filtreleyen 6 haneli kriptografik rastgele PNR üretici (`generate_pnr`).
  - Veritabanı `CHECK (pnr_code ~ '^[A-Z0-9]{6}$')` kuralı ile tam uyumlu doğrulama (`validate_pnr`).
- **Profesyonel A4 Biniş Kartı & Bilet PDF Tasarımı:**
  - Modern havayolu renk paleti ve yüksek çözünürlüklü vektörel çizimler.
  - Türkçe büyük harf (`i` -> `İ`, `ı` -> `I`) ve özel karakter kaçış (`xml.sax.saxutils.escape`) desteği ile tam güvenlik.
  - Dinamik **QR Kod** ve kapı tarayıcıları için **Code128 Barkod**.
  - Sağ tarafta koparılabilir kupon (Passenger Stub) stili.
  - İptal edilmiş biletlerde belirgin kırmızı **İPTAL EDİLMİŞTİR** uyarı bandı ve iptal bilgilendirmesi.
  - Uzun yolcu ve havalimanı isimlerinde taşma yapmayan dinamik metin kaydırma.
- **Backend Entegrasyon Kolaylığı:**
  - Hem doğrudan dosya olarak diske kaydetme hem de Web API yanıtları için bellekte bayt dizisi (`generate_ticket_pdf_bytes`) üretme.
  - PostgreSQL `bookings`, `flights` ve `airports` tablolarından doğrudan PNR ve yolcu soyadı doğrulamasıyla bilet getiren `TicketService` servis katmanı.

---

## 📂 Klasör Mimarisi

```text
ticket_pdf/
├── __init__.py           # Paket dışa aktarımları
├── models.py             # Pydantic veri modelleri (Passenger, FlightInfo, TicketDetails, FlightTicket)
├── pnr.py                # PNR kod algoritması ve güvenli alfabe
├── pdf_generator.py      # ReportLab tabanlı bilet ve biniş kartı PDF oluşturucu
├── service.py            # Backend için TicketService katmanı
├── cli.py                # Komut satırı arayüzü (CLI aracı)
├── requirements.txt      # Bağımlılıklar (reportlab, qrcode, pillow, pydantic)
├── README.md             # Kullanım dokümantasyonu
└── tests/
    └── test_ticket_pdf.py # 10 adet birim ve PDF içerik doğrulama testi
```

---

## 🚀 Kurulum

```bash
pip install -r requirements.txt
```

---

## 💻 Backend İçin Entegrasyon Kılavuzu

### 1. Bellekten Doğrudan Bilet Modeli Oluşturup PDF Kaydetme

```python
from datetime import datetime, timedelta
from ticket_pdf.service import TicketService
from ticket_pdf.models import CabinClass

departure = datetime.now() + timedelta(days=5, hours=10)
arrival = departure + timedelta(hours=1, minutes=20)

ticket = TicketService.create_ticket(
    passenger_name="Emine",
    passenger_surname="Şirin",
    flight_number="TK-2101",
    airline_name="Türk Hava Yolları",
    origin_code="IST",
    origin_name="İstanbul Havalimanı",
    destination_code="ESB",
    destination_name="Esenboğa Havalimanı",
    departure_time=departure,
    arrival_time=arrival,
    seat_number="1A",
    cabin_class=CabinClass.BUSINESS,
    total_price=2175.00
)

# PDF Dosyası Olarak Kaydet
pdf_path = TicketService.issue_ticket_pdf(ticket, output_path="bilet_TK2101.pdf")
print("Bilet kaydedildi:", pdf_path)
```

### 2. Veritabanından PNR ve Soyad ile Bilet Çekip PDF İndirme (API Uç Noktası)

```python
from ticket_pdf.service import TicketService

# Güvenlik amaçlı PNR ve yolcu soyadı ile sorgula:
pdf_bytes = TicketService.issue_pdf_bytes_from_db(pnr_code="TK19AB", last_name="Yılmaz")

if pdf_bytes:
    # FastAPI / Express yanıtı:
    # return Response(content=pdf_bytes, media_type="application/pdf")
    pass
```

---

## 🛠️ Komut Satırı (CLI) Kullanımı

```bash
# Örnek demo bilet oluştur
python -m ticket_pdf.cli --demo

# Veritabanındaki PNR koduyla bilet oluştur
python -m ticket_pdf.cli --pnr TK19AB --output bilet_TK19AB.pdf

# Güvenlik amaçlı soyadı doğrulamasıyla sorgula
python -m ticket_pdf.cli --pnr TK19AB --last-name Yılmaz

# 5 adet benzersiz PNR kodu üret
python -m ticket_pdf.cli --generate-pnrs 5

# PNR formatını doğrula
python -m ticket_pdf.cli --validate-pnr TK19AB
```

---

## 🧪 Testlerin Çalıştırılması

```bash
python -m unittest discover -s ticket_pdf/tests
```
