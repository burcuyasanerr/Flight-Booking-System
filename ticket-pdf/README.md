# ✈️ PNR Üretimi ve Bilet PDF Çıktısı Modülü (`ticket-pdf/`)

Bu modül, **Flight Ticket Purchasing System (Team 19)** projesinin rezervasyon (PNR) kodu üretimi, format doğrulaması ve IATA standartlarına uygun profesyonel elektronik uçuş bileti / biniş kartı (Boarding Pass) PDF çıktısı oluşturma sorumluluğunu yerine getirir.

---

## 📌 Özellikler

- **IATA Standartlarında PNR Üretimi:** 
  - İnsan gözüyle karıştırılabilecek karakterleri (`0`, `O`, `1`, `I`) otomatik olarak filtreleyen kriptografik güvenli rastgele PNR üretici (`generate_pnr`).
  - Eşzamanlılık ve test senaryoları için deterministik (öngörülebilir) PNR türetme (`generate_deterministic_pnr`).
  - PNR biçim ve uzunluk doğrulama (`validate_pnr`).
- **Profesyonel A4 Biniş Kartı & Bilet PDF Tasarımı:**
  - Modern havayolu renk paleti ve yüksek çözünürlüklü vektörel çizimler.
  - Türkçe karakter desteği (`ç, ğ, ı, ö, ş, ü, İ, Ç, Ğ, Ö, Ş, Ü`).
  - Dinamik **QR Kod** (PNR, yolcu, koltuk, uçuş bilgilerini içeren taranabilir optik kod).
  - Biniş kapısı için **Code128 Barkod** çizgileri.
  - Sağ tarafta delikli/koparılabilir kupon (Passenger Stub) stili.
  - Detaylı ücret & vergi döküm tablosu.
  - Bagaj hakkı ve önemli havacılık yolcu bilgilendirmeleri.
- **Backend Entegrasyon Kolaylığı:**
  - Hem doğrudan dosya olarak diske kaydetme (`generate_ticket_pdf`) hem de API yanıtları için bellekte bayt dizisi (`generate_ticket_pdf_bytes`) üretme.
  - Tek satırda çağrılabilir yüksek seviyeli `TicketService` servis katmanı.
- **Komut Satırı (CLI) Aracı:**
  - Komut satırından tek komutla test bileti oluşturma, PNR üretme veya doğrulama.

---

## 📂 Klasör Mimarisi

```text
ticket-pdf/
├── __init__.py           # Paket dışa aktarımları
├── models.py             # Pydantic veri modelleri (Passenger, FlightInfo, TicketDetails, FlightTicket)
├── pnr.py                # PNR kod algoritması, güvenli alfabe ve doğrulama fonksiyonları
├── pdf_generator.py      # ReportLab tabanlı bilet ve biniş kartı PDF oluşturucu
├── service.py            # Backend için yüksek seviyeli TicketService katmanı
├── cli.py                # Komut satırı arayüzü (CLI aracı)
├── requirements.txt      # Modül bağımlılıkları
├── README.md             # Kullanım ve entegrasyon dokümantasyonu
└── tests/
    └── test_ticket_pdf.py # 10 adet kapsamlı birim testi (Unit Tests)
```

---

## 🚀 Kurulum

Gerekli Python paketlerini yüklemek için:

```bash
pip install -r requirements.txt
```

---

## 💻 Backend İçin Entegrasyon Kılavuzu

Backend ekibindeki arkadaşlarınız bu servisi iki şekilde kullanabilir:

### 1. `TicketService` Kullanarak Bilet Oluşturma ve PDF Kaydetme

```python
from datetime import datetime, timedelta
import sys
sys.path.append("ticket-pdf")

from service import TicketService
from models import CabinClass

# 1. Bilet Modelini Oluştur
departure = datetime.now() + timedelta(days=5, hours=10)
arrival = departure + timedelta(hours=1, minutes=20)

ticket = TicketService.create_ticket(
    passenger_name="Ahmet Can",
    passenger_surname="Öztürk",
    flight_number="TK1923",
    airline_name="Türk Hava Yolları",
    origin_code="IST",
    origin_name="İstanbul Havalimanı",
    destination_code="ADB",
    destination_name="İzmir Adnan Menderes Havalimanı",
    departure_time=departure,
    arrival_time=arrival,
    seat_number="14B",
    cabin_class=CabinClass.ECONOMY,
    base_price=1750.0,
    tax_amount=350.0,
    gate="214B",
    terminal="T1"
)

# 2. PDF Dosyası Olarak Kaydet
pdf_path = TicketService.issue_ticket_pdf(ticket, output_path="bilet_TK1923.pdf")
print("Bilet kaydedildi:", pdf_path)
print("Üretilen PNR:", ticket.ticket.pnr_code)
```

### 2. Web API / FastAPI / Flask Üzerinden İndirme (In-Memory Bytes)

```python
from service import TicketService
# ...
# PDF'i diske yazmadan doğrudan bayt olarak al:
pdf_bytes = TicketService.issue_ticket_pdf_bytes(ticket)

# FastAPI / Starlette örneği:
# from fastapi.responses import Response
# return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=bilet_{ticket.ticket.pnr_code}.pdf"})
```

---

## 🛠️ Komut Satırı (CLI) Kullanımı

Modül dizini içerisinden doğrudan CLI komutları çalıştırılabilir:

### 1. Örnek Demo Bilet Oluşturma
```bash
python cli.py --demo
# veya özel çıktı yoluyla:
python cli.py --demo --output ornek_bilet.pdf
```

### 2. Belirtilen Yolcu ve Uçuş Bilgileriyle Bilet Oluşturma
```bash
python cli.py --name "Burcu" --surname "Yaşaner" --from IST --to ADB --flight TK1923 --seat 12A --price 2450 --output bilet.pdf
```

### 3. Benzersiz PNR Kodları Üretme
```bash
python cli.py --generate-pnrs 5
```

### 4. PNR Kodu Formatını Doğrulama
```bash
python cli.py --validate-pnr TK79AB
```

---

## 🧪 Testlerin Çalıştırılması

Tüm fonksiyonların ve algoritmaların doğruluğunu test etmek için:

```bash
python -m unittest tests/test_ticket_pdf.py
```

Test çıktısı:
```text
..........
----------------------------------------------------------------------
Ran 10 tests in 0.134s

OK
```
