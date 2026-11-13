# Backend (FastAPI)

React arayüzü ile PostgreSQL arasındaki REST API. Koltuk kilitleme için
[`concurrency`](../concurrency), PNR ve PDF bilet için [`ticket_pdf`](../ticket_pdf)
modüllerini doğrudan kullanır; ayrı bir bağlantı havuzu açmaz.

```text
React (Vite, :5173)  ──HTTP/JSON──▶  FastAPI (:5000/api)  ──psycopg2──▶  PostgreSQL
                                        │
                                        ├── concurrency  (koltuk kilitleme)
                                        └── ticket_pdf   (PNR + PDF bilet)
```

## Kurulum

Komutların hepsi **proje kök klasöründe** çalıştırılır (Git Bash):

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r backend/requirements.txt
cp .env.example .env
```

> CMD kullanıyorsan: `source .venv/Scripts/activate` yerine `.venv\Scripts\activate`, `cp` yerine `copy` yaz.
> Sanal ortamı (`activate`) her yeni terminalde tekrar açman gerekir.

`.env` içindeki `DB_PASSWORD` değerini kendi PostgreSQL şifrenle değiştir.
Veritabanının kurulu olması gerekir (ana README → *Veritabanını kur*).

## Çalıştırma

```bash
python -m backend
```

- API: http://localhost:5000/api
- Otomatik dokümantasyon (Swagger): http://localhost:5000/docs
- Sağlık kontrolü: http://localhost:5000/api/health → `{"status": "ok", "database": true}`

## Uç noktalar

| Metot | Adres | Açıklama |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Sunucu ve veritabanı bağlantısı |
| `GET` | `/api/airports` | Havalimanları ve koordinatları |
| `GET` | `/api/flights?from=IST&to=ESB&date=2026-11-15` | Uçuş arama (parametreler isteğe bağlı). İptal edilen uçuşlar da `status: "CANCELLED"` ile gelir; arayüz bunları "İptal" rozetiyle gösterir ve koltuk seçtirmez. |
| `GET` | `/api/flights/{id}` | Tek uçuş |
| `GET` | `/api/flights/{id}/seats` | Koltuk haritası |
| `POST` | `/api/seats/{id}/lock` | Koltuğu 10 dk tut. Gövde: `{"session_id": "...", "expected_version": 3}` |
| `DELETE` | `/api/seats/{id}/lock?session_id=...` | Koltuğu bırak |
| `GET` | `/api/bookings/pnr/{pnr}?last_name=...` | PNR ile bilet sorgula |
| `GET` | `/api/bookings/pnr/{pnr}/pdf?last_name=...` | Bilet PDF'ini indir |

**Koltuk kilitleme:** `expected_version` gönderilirse *optimistic locking*
(koltuğun `version` değeri değiştiyse istek reddedilir), gönderilmezse
*pessimistic locking* (`SELECT ... FOR UPDATE`) kullanılır. Giriş sistemi
eklenene kadar `session_id` değerini istemci üretir (örn. `crypto.randomUUID()`).

**Hatalar** her zaman aynı biçimde döner:

```json
{ "detail": { "code": "LOCKED_BY_ANOTHER_USER", "message": "Bu koltuk şu anda başka bir kullanıcı tarafından seçilmiş durumda." } }
```

| HTTP | Ne zaman |
| :-: | :--- |
| 404 | Uçuş, koltuk veya bilet bulunamadı |
| 409 | Koltuk dolu / başkası tutuyor / sürüm değişmiş / uçuş iptal veya geçmiş / kilit sınırı |
| 422 | Geçersiz parametre (örn. `from=ISTX`, aynı kalkış-varış, hatalı tarih) |
| 503 | Veritabanına bağlanılamıyor veya sunucu yoğun |

422 cevaplarında hangi alanların hatalı olduğu ayrıca `errors` listesinde verilir:

```json
{ "detail": { "code": "VALIDATION_ERROR", "message": "Geçersiz veya eksik alan: from",
              "errors": [{ "field": "from", "message": "String should match pattern '^[A-Za-z]{3}$'" }] } }
```

## Testler

Testler `flight_booking_test` adında geçici bir veritabanı kurup siler;
asıl veritabanına dokunmaz. PostgreSQL çalışmıyorsa testler atlanır.

```bash
python -m pytest backend/tests -v
```

## Henüz yapılmayanlar

- Kayıt / giriş (`/api/auth/*`) ve kilitlerin giriş yapan kullanıcıya bağlanması
- Bilet satın alma (`POST /api/bookings`), biletlerim, bilet iptali
- PNR sorgusunda soyadının zorunlu hale getirilmesi
