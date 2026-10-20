# Flight Ticket Purchasing System (Team 19)

Kalkış-varış noktaları ve tarihlere göre uçuş aranan, koltuk seçimi yapılarak bilet satın alınan seyahat platformu.

## Proje Klasör Yapısı

```text
Flight-Booking-System/
├── database/       # Veritabanı tasarımı ve tablolar
├── backend/        # Sunucu tarafı ve API servisleri
├── frontend/       # Kullanıcı arayüzü ve harita üzerinde uçuş güzergâhı görselleştirme
├── concurrency/    # Aktif koltuk seçiminde eşzamanlılık (concurrency) çakışma yönetimi
└── ticket-pdf/     # PNR kodu üretimi ve bilet PDF çıktısı oluşturma
```

## Ekip Görev Dağılımı

| Ekip Üyesi | Sorumluluk Alanı | Çalışacağı Klasörler |
| :--- | :--- | :--- |
| **1. Üye** | Backend & Veritabanı | `database/`, `backend/` |
| **2. Üye** | Frontend & Harita Görselleştirme | `frontend/` |
| **3. Üye** | Eşzamanlılık (Concurrency) & PNR PDF Çıktısı | `concurrency/`, `ticket-pdf/` |
