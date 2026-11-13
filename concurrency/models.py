"""
Flight Ticket Purchasing System - Concurrency Data Models
Koltuk kilitleme, sürüm kontrolü (optimistic locking) ve eşzamanlılık sonuç modelleri.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Union
from pydantic import BaseModel, Field


class SeatStatus(str, Enum):
    """Koltuk durumları"""
    AVAILABLE = "AVAILABLE"
    LOCKED = "LOCKED"
    BOOKED = "BOOKED"


class SeatClass(str, Enum):
    """Koltuk sınıfı - Veritabanı CHECK kısıtlamasıyla birebir uyumlu"""
    BUSINESS = "BUSINESS"
    ECONOMY = "ECONOMY"


class SeatInfo(BaseModel):
    """Koltuk detay bilgisi"""
    id: int
    flight_id: int
    seat_number: str
    seat_class: SeatClass
    price_multiplier: Decimal
    status: SeatStatus
    effective_status: SeatStatus = Field(
        ...,
        description="Süresi dolmuş kilitleri AVAILABLE olarak gösteren etkin durum"
    )
    locked_by_session: Optional[str] = None
    locked_until: Optional[datetime] = None
    version: int


class LockResult(BaseModel):
    """Koltuk kilitleme işlem sonucu"""
    success: bool
    seat_id: int
    session_id: str
    previous_version: Optional[int] = None
    new_version: Optional[int] = None
    locked_until: Optional[datetime] = None
    message: str
    conflict_detected: bool = False
    conflict_reason: Optional[str] = None


class ReleaseResult(BaseModel):
    """Kilit serbest bırakma sonucu"""
    success: bool
    seat_id: int
    session_id: str
    message: str


class BookingResult(BaseModel):
    """Satın alma ve kesinleştirme işlemi sonucu"""
    success: bool
    seat_id: int
    session_id: str
    pnr_code: Optional[str] = None
    total_price: Optional[Decimal] = None
    message: str
    error_code: Optional[str] = None
