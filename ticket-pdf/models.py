"""
Flight Ticket Purchasing System - Ticket Data Models
Bu modül, biletleme sistemi için gerekli veri modellerini (Pydantic) tanımlar.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class CabinClass(str, Enum):
    """Kabin sınıfları"""
    ECONOMY = "Ekonomi"
    BUSINESS = "Business"
    FIRST = "First Class"


class TicketStatus(str, Enum):
    """Bilet durumları"""
    CONFIRMED = "ONAYLANDI"
    CANCELLED = "İPTAL EDİLDİ"
    REFUNDED = "İADE EDİLDİ"


class Passenger(BaseModel):
    """Yolcu bilgileri modeli"""
    first_name: str = Field(..., min_length=2, max_length=50, description="Yolcu adı")
    last_name: str = Field(..., min_length=2, max_length=50, description="Yolcu soyadı")
    identity_number: Optional[str] = Field(None, description="TC Kimlik No veya Pasaport No")
    email: Optional[str] = Field(None, description="İletişim e-posta adresi")
    phone: Optional[str] = Field(None, description="İletişim telefon numarası")

    @property
    def full_name(self) -> str:
        """Büyük harflerle yolcu ad ve soyadı döndürür."""
        return f"{self.first_name.strip()} {self.last_name.strip()}".upper()


class FlightInfo(BaseModel):
    """Uçuş bilgileri modeli"""
    flight_number: str = Field(..., description="Uçuş kodu (Örn: TK1923)")
    airline_name: str = Field(default="SkyWings Airlines", description="Havayolu şirketi adı")
    origin_code: str = Field(..., min_length=3, max_length=4, description="Kalkış havalimanı IATA kodu (Örn: IST)")
    origin_name: str = Field(..., description="Kalkış havalimanı / şehir adı")
    destination_code: str = Field(..., min_length=3, max_length=4, description="Varış havalimanı IATA kodu (Örn: ADB)")
    destination_name: str = Field(..., description="Varış havalimanı / şehir adı")
    departure_datetime: datetime = Field(..., description="Kalkış tarihi ve saati")
    arrival_datetime: datetime = Field(..., description="Varış tarihi ve saati")
    gate: Optional[str] = Field(default="--", description="Biniş kapısı (Gate)")
    terminal: Optional[str] = Field(default="T1", description="Terminal bilgisi")
    boarding_time: Optional[datetime] = Field(default=None, description="Biniş başlangıç saati")
    aircraft_type: Optional[str] = Field(default="Boeing 737-800", description="Uçak modeli")

    @field_validator("origin_code", "destination_code")
    @classmethod
    def uppercase_codes(cls, v: str) -> str:
        return v.upper().strip()

    @property
    def duration_formatted(self) -> str:
        """Uçuş süresini 'X sa Y dk' biçiminde hesaplar."""
        delta = self.arrival_datetime - self.departure_datetime
        total_minutes = int(delta.total_seconds() // 60)
        hours = total_minutes // 60
        minutes = total_minutes % 60
        if hours > 0:
            return f"{hours} sa {minutes} dk"
        return f"{minutes} dk"


class TicketDetails(BaseModel):
    """Bilet ve rezervasyon ayrıntıları modeli"""
    pnr_code: str = Field(..., min_length=5, max_length=8, description="PNR Rezervasyon Kodu (Örn: TK79AB)")
    seat_number: str = Field(..., description="Koltuk numarası (Örn: 12A)")
    cabin_class: CabinClass = Field(default=CabinClass.ECONOMY, description="Kabin sınıfı")
    baggage_allowance: str = Field(default="20 Kg Bagaj + 8 Kg Kabin", description="Bagaj hakkı")
    base_price: float = Field(..., ge=0, description="Taban bilet fiyatı")
    tax_amount: float = Field(default=0.0, ge=0, description="Vergi ve harçlar tutarı")
    total_price: float = Field(..., ge=0, description="Toplam ödenen tutar")
    currency: str = Field(default="TRY", description="Para birimi (TRY, USD, EUR vb.)")
    payment_method: str = Field(default="Kredi Kartı", description="Ödeme yöntemi")
    booking_date: datetime = Field(default_factory=datetime.now, description="Rezervasyon oluşturulma tarihi")
    ticket_status: TicketStatus = Field(default=TicketStatus.CONFIRMED, description="Bilet durumu")

    @field_validator("pnr_code")
    @classmethod
    def uppercase_pnr(cls, v: str) -> str:
        return v.upper().strip()


class FlightTicket(BaseModel):
    """Tüm bilet bileşenlerini birleştiren ana bilet modeli"""
    passenger: Passenger
    flight: FlightInfo
    ticket: TicketDetails
