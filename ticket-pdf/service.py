"""
Flight Ticket Purchasing System - Ticket Service
Backend ve diğer servislerin bilet oluşturma, PNR üretme ve PDF çıktısı alma
işlemlerini tek bir çatı altından kolayca yönetmesini sağlayan servis katmanı.
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Union

try:
    from .models import (
        CabinClass,
        FlightInfo,
        FlightTicket,
        Passenger,
        TicketDetails,
        TicketStatus,
    )
    from .pdf_generator import generate_ticket_pdf, generate_ticket_pdf_bytes
    from .pnr import generate_deterministic_pnr, generate_pnr, validate_pnr
except ImportError:
    from models import (
        CabinClass,
        FlightInfo,
        FlightTicket,
        Passenger,
        TicketDetails,
        TicketStatus,
    )
    from pdf_generator import generate_ticket_pdf, generate_ticket_pdf_bytes
    from pnr import generate_deterministic_pnr, generate_pnr, validate_pnr


class TicketService:
    """
    Biletleme ve PNR işlemlerini yöneten servis sınıfı.
    """

    @staticmethod
    def create_ticket(
        passenger_name: str,
        passenger_surname: str,
        flight_number: str,
        origin_code: str,
        origin_name: str,
        destination_code: str,
        destination_name: str,
        departure_time: datetime,
        arrival_time: datetime,
        seat_number: str,
        base_price: float,
        tax_amount: float = 0.0,
        airline_name: str = "SkyWings Airlines",
        cabin_class: Union[str, CabinClass] = CabinClass.ECONOMY,
        baggage_allowance: str = "20 Kg Bagaj + 8 Kg Kabin",
        gate: str = "--",
        terminal: str = "T1",
        pnr_prefix: Optional[str] = None,
        identity_number: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        aircraft_type: str = "Boeing 737-800",
        pnr_code: Optional[str] = None,
    ) -> FlightTicket:
        """
        Girdi parametrelerinden geçerli bir FlightTicket veri modeli oluşturur.
        PNR kodu belirtilmemişse otomatik olarak kriptografik güvenli bir PNR üretir.
        """
        # PNR otomatik veya sağlanan kod
        if not pnr_code:
            pnr_code = generate_pnr(length=6, prefix=pnr_prefix)
        else:
            if not validate_pnr(pnr_code):
                raise ValueError(f"Geçersiz PNR formatı: {pnr_code}")

        # Kabin sınıfı dönüşümü
        if isinstance(cabin_class, str):
            cabin_enum = CabinClass.ECONOMY
            for c in CabinClass:
                if c.value.lower() == cabin_class.lower() or c.name.lower() == cabin_class.lower():
                    cabin_enum = c
                    break
        else:
            cabin_enum = cabin_class

        # Biniş saati: Kalkıştan 40 dk önce
        boarding_time = departure_time - timedelta(minutes=40)
        total_price = base_price + tax_amount

        passenger = Passenger(
            first_name=passenger_name,
            last_name=passenger_surname,
            identity_number=identity_number,
            email=email,
            phone=phone,
        )

        flight = FlightInfo(
            flight_number=flight_number,
            airline_name=airline_name,
            origin_code=origin_code,
            origin_name=origin_name,
            destination_code=destination_code,
            destination_name=destination_name,
            departure_datetime=departure_time,
            arrival_datetime=arrival_time,
            gate=gate,
            terminal=terminal,
            boarding_time=boarding_time,
            aircraft_type=aircraft_type,
        )

        ticket_details = TicketDetails(
            pnr_code=pnr_code,
            seat_number=seat_number,
            cabin_class=cabin_enum,
            baggage_allowance=baggage_allowance,
            base_price=base_price,
            tax_amount=tax_amount,
            total_price=total_price,
            ticket_status=TicketStatus.CONFIRMED,
        )

        return FlightTicket(
            passenger=passenger,
            flight=flight,
            ticket=ticket_details,
        )

    @classmethod
    def issue_ticket_pdf(
        cls,
        ticket: FlightTicket,
        output_path: Optional[Union[str, Path]] = None,
    ) -> str:
        """
        Verilen bileti PDF formatında diske kaydeder.
        Hedef dosya yolu belirtilmemişse 'output/ticket_<PNR>.pdf' altına kaydeder.
        """
        if not output_path:
            out_dir = Path("output")
            out_dir.mkdir(exist_ok=True)
            output_path = out_dir / f"ticket_{ticket.ticket.pnr_code}_{ticket.ticket.seat_number}.pdf"

        return generate_ticket_pdf(ticket, output_path)

    @classmethod
    def issue_ticket_pdf_bytes(cls, ticket: FlightTicket) -> bytes:
        """
        Verilen bileti doğrudan bellekte PDF bayt dizisi (bytes) olarak döner.
        """
        return generate_ticket_pdf_bytes(ticket)
