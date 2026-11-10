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

    @classmethod
    def get_ticket_from_db(
        cls,
        pnr_code: str,
        db_manager=None,
    ) -> Optional[FlightTicket]:
        """
        Veritabanından PNR koduna göre bilet, uçuş ve yolcu bilgilerini sorgular
        ve FlightTicket veri modeline dönüştürür.
        """
        if db_manager is None:
            try:
                import sys
                from pathlib import Path
                concurrency_dir = Path(__file__).resolve().parent.parent / "concurrency"
                if str(concurrency_dir) not in sys.path:
                    sys.path.insert(0, str(concurrency_dir))
                from db import db_manager as default_db
                db_manager = default_db
            except Exception as e:
                raise RuntimeError(f"Veritabanı yöneticisine erişilemedi: {e}")

        clean_pnr = pnr_code.strip().upper()
        query = """
        SELECT b.pnr_code, b.booking_status, b.total_price, b.created_at,
               b.passenger_first_name, b.passenger_last_name, b.passenger_identity_number,
               b.passenger_email, b.passenger_phone,
               s.seat_number, s.seat_class,
               v.flight_number, v.departure_time, v.arrival_time,
               v.departure_code, v.departure_city, v.departure_airport,
               v.arrival_code, v.arrival_city, v.arrival_airport
        FROM bookings b
        JOIN flight_seats s     ON s.id = b.seat_id
        JOIN v_flight_search v  ON v.flight_id = b.flight_id
        WHERE b.pnr_code = %s;
        """

        with db_manager.get_cursor(commit=False) as cursor:
            cursor.execute(query, (clean_pnr,))
            row = cursor.fetchone()
            if not row:
                return None

            (
                pnr, status_str, total_price, created_at,
                p_first, p_last, p_id_no, p_email, p_phone,
                s_number, s_class,
                f_number, dep_time, arr_time,
                dep_code, dep_city, dep_airport,
                arr_code, arr_city, arr_airport,
            ) = row

            cabin = CabinClass.BUSINESS if s_class == "BUSINESS" else CabinClass.ECONOMY
            status = TicketStatus.CONFIRMED if status_str == "CONFIRMED" else TicketStatus.CANCELLED

            passenger = Passenger(
                first_name=p_first,
                last_name=p_last,
                identity_number=p_id_no,
                email=p_email,
                phone=p_phone,
            )

            boarding_time = dep_time - timedelta(minutes=40)
            flight = FlightInfo(
                flight_number=f_number,
                airline_name="Türk Hava Yolları" if f_number.startswith("TK") else "Pegasus Airlines",
                origin_code=dep_code,
                origin_name=f"{dep_city} - {dep_airport}",
                destination_code=arr_code,
                destination_name=f"{arr_city} - {arr_airport}",
                departure_datetime=dep_time,
                arrival_datetime=arr_time,
                boarding_time=boarding_time,
                gate="214B",
                terminal="T1",
                aircraft_type="Airbus A321neo" if f_number.startswith("TK") else "Boeing 737-800",
            )

            tot_price = float(total_price)
            base_p = tot_price * 0.82
            tax_p = tot_price * 0.18

            ticket_details = TicketDetails(
                pnr_code=pnr,
                seat_number=s_number,
                cabin_class=cabin,
                baggage_allowance="30 Kg Bagaj + 8 Kg Kabin" if cabin == CabinClass.BUSINESS else "20 Kg Bagaj + 8 Kg Kabin",
                base_price=round(base_p, 2),
                tax_amount=round(tax_p, 2),
                total_price=tot_price,
                currency="TRY",
                payment_method="Kredi Kartı / Havale",
                booking_date=created_at.replace(tzinfo=None) if hasattr(created_at, "replace") else created_at,
                ticket_status=status,
            )

            return FlightTicket(
                passenger=passenger,
                flight=flight,
                ticket=ticket_details,
            )

    @classmethod
    def issue_pdf_from_db(
        cls,
        pnr_code: str,
        output_path: Optional[Union[str, Path]] = None,
        db_manager=None,
    ) -> Optional[str]:
        """
        Veritabanından PNR koduna göre bileti çekip PDF dosyasını üretir ve yolunu döner.
        """
        ticket = cls.get_ticket_from_db(pnr_code, db_manager=db_manager)
        if not ticket:
            return None
        return cls.issue_ticket_pdf(ticket, output_path=output_path)

    @classmethod
    def issue_pdf_bytes_from_db(
        cls,
        pnr_code: str,
        db_manager=None,
    ) -> Optional[bytes]:
        """
        Veritabanından PNR koduna göre bileti çekip PDF bayt dizisi (bytes) döner.
        """
        ticket = cls.get_ticket_from_db(pnr_code, db_manager=db_manager)
        if not ticket:
            return None
        return cls.issue_ticket_pdf_bytes(ticket)
