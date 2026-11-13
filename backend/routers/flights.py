from datetime import date, datetime, time, timedelta
from typing import Optional

from fastapi import APIRouter, Path, Query

from backend.errors import api_error
from backend.schemas import ErrorResponse, Flight, Seat
from backend.services import db_manager, lock_manager

router = APIRouter(tags=["Uçuşlar"])

FLIGHT_COLUMNS = """
    flight_id, flight_number, departure_time, arrival_time, base_price, status,
    departure_code, departure_city, departure_airport, departure_lat, departure_lng,
    arrival_code, arrival_city, arrival_airport, arrival_lat, arrival_lng,
    available_seats
"""

IATA_PATTERN = "^[A-Za-z]{3}$"


def _rows_to_flights(cursor) -> list[Flight]:
    columns = [c.name for c in cursor.description]
    return [Flight(**dict(zip(columns, row))) for row in cursor.fetchall()]


def _flight_exists(cursor, flight_id: int) -> bool:
    cursor.execute("SELECT 1 FROM flights WHERE id = %s;", (flight_id,))
    return cursor.fetchone() is not None


@router.get(
    "/flights",
    response_model=list[Flight],
    summary="Uçuş arama",
    responses={422: {"description": "Geçersiz havalimanı kodu, tarih veya aynı kalkış-varış"}},
)
def search_flights(
    from_code: Optional[str] = Query(None, alias="from", pattern=IATA_PATTERN, description="Kalkış IATA kodu, örn. IST"),
    to_code: Optional[str] = Query(None, alias="to", pattern=IATA_PATTERN, description="Varış IATA kodu, örn. ESB"),
    flight_date: Optional[date] = Query(None, alias="date", description="Kalkış tarihi (YYYY-MM-DD)"),
):
    """Parametrelerin hepsi isteğe bağlıdır; verilmeyen filtre uygulanmaz. Sonuçlar kalkış saatine göre sıralıdır."""
    if from_code and to_code and from_code.upper() == to_code.upper():
        raise api_error(422, "SAME_AIRPORT", "Kalkış ve varış havalimanı aynı olamaz.")

    conditions, params = [], []
    if from_code:
        conditions.append("departure_code = %s")
        params.append(from_code.upper())
    if to_code:
        conditions.append("arrival_code = %s")
        params.append(to_code.upper())
    if flight_date:
        # departure_time üzerindeki indeksi kullanabilmek için aralık sorgusu
        day_start = datetime.combine(flight_date, time.min)
        conditions.append("departure_time >= %s AND departure_time < %s")
        params.extend([day_start, day_start + timedelta(days=1)])

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = f"SELECT {FLIGHT_COLUMNS} FROM v_flight_search {where} ORDER BY departure_time;"

    with db_manager.get_cursor(commit=False) as cursor:
        cursor.execute(query, params)
        return _rows_to_flights(cursor)


@router.get(
    "/flights/{flight_id}",
    response_model=Flight,
    summary="Tek uçuş detayı",
    responses={404: {"model": ErrorResponse}},
)
def get_flight(flight_id: int = Path(gt=0)):
    with db_manager.get_cursor(commit=False) as cursor:
        cursor.execute(f"SELECT {FLIGHT_COLUMNS} FROM v_flight_search WHERE flight_id = %s;", (flight_id,))
        flights = _rows_to_flights(cursor)

    if not flights:
        raise api_error(404, "FLIGHT_NOT_FOUND", "Uçuş bulunamadı.")
    return flights[0]


@router.get(
    "/flights/{flight_id}/seats",
    response_model=list[Seat],
    summary="Koltuk haritası",
    responses={404: {"model": ErrorResponse}},
)
def get_flight_seats(flight_id: int = Path(gt=0)):
    """
    Koltukların güncel durumunu döner. Süresi dolmuş kilitler `AVAILABLE` olarak
    gösterilir. Kilidi kimin tuttuğu (session) dışarıya verilmez.
    """
    with db_manager.get_cursor(commit=False) as cursor:
        if not _flight_exists(cursor, flight_id):
            raise api_error(404, "FLIGHT_NOT_FOUND", "Uçuş bulunamadı.")

    seats = lock_manager.get_flight_seats(flight_id)
    return [
        Seat(
            id=s.id,
            seat_number=s.seat_number,
            seat_class=s.seat_class.value,
            price_multiplier=float(s.price_multiplier),
            status=s.effective_status.value,
            version=s.version,
        )
        for s in seats
    ]
