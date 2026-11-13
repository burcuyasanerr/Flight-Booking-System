from typing import Optional

from fastapi import APIRouter, Path, Query
from fastapi.responses import Response

from backend.errors import api_error
from backend.schemas import Booking, ErrorResponse
from backend.services import db_manager
from ticket_pdf.models import tr_upper
from ticket_pdf.service import TicketService

router = APIRouter(tags=["Biletler"])

PNR_PATTERN = "^[A-Za-z0-9]{6}$"

BOOKING_QUERY = """
SELECT b.pnr_code, b.booking_status, b.passenger_first_name, b.passenger_last_name,
       v.flight_id, v.flight_number, v.status AS flight_status,
       v.departure_code, v.departure_city, v.departure_time,
       v.arrival_code, v.arrival_city, v.arrival_time,
       s.seat_number, s.seat_class, b.total_price, b.created_at
FROM bookings b
JOIN flight_seats s     ON s.id = b.seat_id
JOIN v_flight_search v  ON v.flight_id = b.flight_id
WHERE b.pnr_code = %s;
"""

PNR_PARAM = Path(pattern=PNR_PATTERN, description="6 karakterlik PNR kodu, örn. TK19AB")
LAST_NAME_PARAM = Query(
    None,
    min_length=1,
    max_length=100,
    description="Yolcu soyadı. Verilirse PNR ile birlikte kontrol edilir (büyük/küçük harf ve Türkçe karakter duyarsız).",
)


def _find_booking(pnr: str, last_name: Optional[str]) -> Booking:
    with db_manager.get_cursor(commit=False) as cursor:
        cursor.execute(BOOKING_QUERY, (pnr.upper(),))
        row = cursor.fetchone()
        columns = [c.name for c in cursor.description]

    booking = Booking(**dict(zip(columns, row))) if row else None

    # Soyad yanlışsa da "bulunamadı" denir; böylece PNR'nin var olup olmadığı sızdırılmaz.
    # SQL'deki LOWER() Türkçe I/ı ayrımını yapamadığı için karşılaştırma burada tr_upper ile yapılır.
    if booking is None or (
        last_name is not None and tr_upper(last_name.strip()) != tr_upper(booking.passenger_last_name.strip())
    ):
        raise api_error(404, "BOOKING_NOT_FOUND", "Bu PNR koduna ait bilet bulunamadı.")
    return booking


@router.get(
    "/bookings/pnr/{pnr}",
    response_model=Booking,
    summary="PNR ile bilet sorgula",
    responses={404: {"model": ErrorResponse}},
)
def get_booking_by_pnr(pnr: str = PNR_PARAM, last_name: Optional[str] = LAST_NAME_PARAM):
    """Yolcunun kimlik numarası, e-posta ve telefonu cevapta yer almaz."""
    return _find_booking(pnr, last_name)


@router.get(
    "/bookings/pnr/{pnr}/pdf",
    summary="Bilet PDF'ini indir",
    response_class=Response,
    responses={
        200: {"content": {"application/pdf": {}}, "description": "Bilet PDF dosyası"},
        404: {"model": ErrorResponse},
    },
)
def download_ticket_pdf(pnr: str = PNR_PARAM, last_name: Optional[str] = LAST_NAME_PARAM):
    """PDF, `ticket_pdf` modülü ile üretilir. İptal edilmiş biletlerde PDF üzerinde iptal ibaresi yer alır."""
    booking = _find_booking(pnr, last_name)

    ticket = TicketService.get_ticket_from_db(booking.pnr_code, db_manager=db_manager)
    if ticket is None:  # sorgu ile PDF arasında bilet silinmişse
        raise api_error(404, "BOOKING_NOT_FOUND", "Bu PNR koduna ait bilet bulunamadı.")

    pdf_bytes = TicketService.issue_ticket_pdf_bytes(ticket)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="bilet_{booking.pnr_code}.pdf"'},
    )
