"""
Flight Ticket Purchasing System - Ticket Data Models
Bu modül, biletleme sistemi için gerekli veri modellerini (Pydantic) tanımlar.
Veritabanı şeması sınırları ve tipleri ile birebir uyumludur.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
import re
from typing import Optional, Union
from pydantic import BaseModel, Field, field_validator


def tr_upper(text: Optional[str]) -> str:
    """
    Madde 19: Türkçe karakterleri ('i' -> 'İ', 'ı' -> 'I') doğru dönüştüren büyük harf fonksiyonu.
    'Emine Şirin'.upper() -> 'EMINE ŞIRIN' yerine 'EMİNE ŞİRİN' üretir.
    """
    if not text:
        return ""
    trans = str.maketrans({"i": "İ", "ı": "I"})
    return text.translate(trans).upper()


class CabinClass(str, Enum):
    """
    Madde 34: Veritabanı şemasındaki CHECK (seat_class IN ('BUSINESS', 'ECONOMY'))
    kısıtlamasıyla birebir uyumlu kabin sınıfları.
    """
    BUSINESS = "BUSINESS"
    ECONOMY = "ECONOMY"

    @property
    def display_name(self) -> str:
        return "Business" if self == CabinClass.BUSINESS else "Ekonomi"


class TicketStatus(str, Enum):
    """
    Madde 34: Veritabanı şemasındaki CHECK (booking_status IN ('CONFIRMED', 'CANCELLED'))
    kısıtlamasıyla birebir uyumlu bilet durumları.
    """
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"

    @property
    def display_name(self) -> str:
        return "ONAYLANDI" if self == TicketStatus.CONFIRMED else "İPTAL EDİLDİ"


class Passenger(BaseModel):
    """
    Yolcu bilgileri modeli
    Madde 20: Veritabanındaki VARCHAR(100) sınırlarıyla eşitlendi (1 - 100 karakter).
    """
    first_name: str = Field(..., min_length=1, max_length=100, description="Yolcu adı")
    last_name: str = Field(..., min_length=1, max_length=100, description="Yolcu soyadı")
    identity_number: Optional[str] = Field(None, max_length=20, description="TC Kimlik No veya Pasaport No")
    email: Optional[str] = Field(None, max_length=150, description="İletişim e-posta adresi")
    phone: Optional[str] = Field(None, max_length=30, description="İletişim telefon numarası")

    @property
    def full_name(self) -> str:
        """Madde 19: Türkçe büyük harfle tam isim döndürür."""
        return f"{tr_upper(self.first_name.strip())} {tr_upper(self.last_name.strip())}"

    @property
    def stub_name(self) -> str:
        """Kupon için SOYAD / AD biçiminde Türkçe büyük harfli isim."""
        return f"{tr_upper(self.last_name.strip())} / {tr_upper(self.first_name.strip())}"


class FlightInfo(BaseModel):
    """Uçuş bilgileri modeli"""
    flight_number: str = Field(..., max_length=15, description="Uçuş kodu (Örn: TK-2101)")
    airline_name: str = Field(default="SkyWings Airlines", description="Havayolu şirketi adı")
    origin_code: str = Field(..., min_length=3, max_length=3, description="Kalkış IATA kodu (Örn: IST)")
    origin_name: str = Field(..., description="Kalkış havalimanı / şehir adı")
    destination_code: str = Field(..., min_length=3, max_length=3, description="Varış IATA kodu (Örn: ESB)")
    destination_name: str = Field(..., description="Varış havalimanı / şehir adı")
    departure_datetime: datetime = Field(..., description="Kalkış tarihi ve saati")
    arrival_datetime: datetime = Field(..., description="Varış tarihi ve saati")
    gate: Optional[str] = Field(default=None, description="Biniş kapısı")
    terminal: Optional[str] = Field(default=None, description="Terminal")
    boarding_time: Optional[datetime] = Field(default=None, description="Biniş başlangıç saati")
    aircraft_type: Optional[str] = Field(default=None, description="Uçak modeli")

    @field_validator("origin_code", "destination_code")
    @classmethod
    def uppercase_codes(cls, v: str) -> str:
        return v.upper().strip()

    @property
    def duration_formatted(self) -> str:
        """Uçuş süresini hesaplar."""
        delta = self.arrival_datetime - self.departure_datetime
        total_minutes = max(0, int(delta.total_seconds() // 60))
        hours = total_minutes // 60
        minutes = total_minutes % 60
        if hours > 0:
            return f"{hours} sa {minutes} dk"
        return f"{minutes} dk"


class TicketDetails(BaseModel):
    """
    Bilet ve rezervasyon ayrıntıları modeli
    Madde 20: PNR kodu tam 6 karakter zorunludur (veritabanı check ile birebir).
    """
    pnr_code: str = Field(..., min_length=6, max_length=6, pattern=r"^[A-Z0-9]{6}$", description="6 haneli PNR")
    seat_number: str = Field(..., max_length=5, description="Koltuk numarası (Örn: 1A)")
    cabin_class: CabinClass = Field(default=CabinClass.ECONOMY, description="Kabin sınıfı")
    baggage_allowance: str = Field(default="20 Kg Bagaj + 8 Kg Kabin", description="Bagaj hakkı")
    total_price: Decimal = Field(..., ge=0, description="Toplam bilet fiyatı (TL)")
    currency: str = Field(default="TRY", description="Para birimi")
    payment_method: str = Field(default="Elektronik Tahsilat", description="Ödeme yöntemi")
    booking_date: datetime = Field(default_factory=datetime.now, description="Rezervasyon oluşturulma tarihi")
    ticket_status: TicketStatus = Field(default=TicketStatus.CONFIRMED, description="Bilet durumu")

    @field_validator("pnr_code")
    @classmethod
    def uppercase_pnr(cls, v: str) -> str:
        return v.upper().strip()


class FlightTicket(BaseModel):
    """Tüm bilet bileşenlerini birleştiren ana model"""
    passenger: Passenger
    flight: FlightInfo
    ticket: TicketDetails
