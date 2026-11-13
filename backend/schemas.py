"""
API'nin istek ve cevap modelleri.

Alan adları veritabanındaki kolonlar ve `v_flight_search` view'ı ile aynıdır;
frontend'deki `mock.js` de aynı yapıyı kullanır.
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

FlightStatus = Literal["SCHEDULED", "DELAYED", "CANCELLED", "COMPLETED"]
SeatStatus = Literal["AVAILABLE", "LOCKED", "BOOKED"]
SeatClass = Literal["BUSINESS", "ECONOMY"]


class ErrorDetail(BaseModel):
    code: str = Field(examples=["FLIGHT_NOT_FOUND"])
    message: str = Field(examples=["Uçuş bulunamadı."])


class ErrorResponse(BaseModel):
    detail: ErrorDetail


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    database: bool


class Airport(BaseModel):
    id: int
    iata_code: str = Field(examples=["IST"])
    name: str = Field(examples=["İstanbul Havalimanı"])
    city: str = Field(examples=["İstanbul"])
    latitude: float
    longitude: float


class Flight(BaseModel):
    flight_id: int
    flight_number: str = Field(examples=["TK-2101"])
    departure_time: datetime
    arrival_time: datetime
    base_price: float = Field(examples=[1450.0])
    status: FlightStatus
    departure_code: str
    departure_city: str
    departure_airport: str
    departure_lat: float
    departure_lng: float
    arrival_code: str
    arrival_city: str
    arrival_airport: str
    arrival_lat: float
    arrival_lng: float
    available_seats: int


class Seat(BaseModel):
    id: int
    seat_number: str = Field(examples=["1A"])
    seat_class: SeatClass
    price_multiplier: float = Field(examples=[1.5])
    status: SeatStatus
    version: int = Field(description="Optimistic locking için koltuğun güncel sürümü")


class LockRequest(BaseModel):
    session_id: str = Field(
        min_length=1,
        max_length=100,
        description="Koltuğu tutan oturum. Giriş sistemi eklenene kadar istemci üretir (örn. UUID).",
        examples=["3f1c9e2a-7b4d-4c1e-9a77-1d2b3c4d5e6f"],
    )
    expected_version: Optional[int] = Field(
        default=None,
        ge=1,
        description=(
            "Verilirse optimistic locking kullanılır: koltuk bu sürümden sonra değiştiyse "
            "istek reddedilir. Verilmezse pessimistic locking (SELECT ... FOR UPDATE) kullanılır."
        ),
    )


class LockResponse(BaseModel):
    seat_id: int
    session_id: str
    locked_until: datetime
    version: int
    message: str


class ReleaseResponse(BaseModel):
    seat_id: int
    message: str


class Booking(BaseModel):
    pnr_code: str = Field(examples=["TK19AB"])
    booking_status: Literal["CONFIRMED", "CANCELLED"]
    passenger_first_name: str
    passenger_last_name: str
    flight_id: int
    flight_number: str
    flight_status: FlightStatus
    departure_code: str
    departure_city: str
    departure_time: datetime
    arrival_code: str
    arrival_city: str
    arrival_time: datetime
    seat_number: str
    seat_class: SeatClass
    total_price: float
    created_at: datetime
