"""
Flight Ticket Purchasing System - Ticket Service
Backend ve diğer servislerin bilet oluşturma, PNR üretme ve PDF çıktısı alma
işlemlerini tek bir çatı altından kolayca yönetmesini sağlayan servis katmanı.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Optional, Union

from concurrency.db import db_manager as default_db_manager
from ticket_pdf.models import (
    CabinClass,
    FlightInfo,
    FlightTicket,
    Passenger,
    TicketDetails,
    TicketStatus,
)
from ticket_pdf.pdf_generator import generate_ticket_pdf, generate_ticket_pdf_bytes
from ticket_pdf.pnr import generate_pnr, validate_pnr


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
        total_price: Union[float, Decimal],
        airline_name: str = "SkyWings Airlines",
        cabin_class: Union[str, CabinClass] = CabinClass.ECONOMY,
        baggage_allowance: Optional[str] = None,
        gate: Optional[str] = None,
        terminal: Optional[str] = None,
        pnr_prefix: Optional[str] = None,
        identity_number: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        aircraft_type: Optional[str] = None,
        pnr_code: Optional[str] = None,
        ticket_status: TicketStatus = TicketStatus.CONFIRMED,
    ) -> FlightTicket:
        """
        Girdi parametrelerinden geçerli bir FlightTicket veri modeli oluşturur.
        Madde 24: Tanınmayan kabin sınıfı gelirse sessizce geçiştirmek yerine ValueError fırlatır.
        """
        if not pnr_code:
            pnr_code = generate_pnr(length=6, prefix=pnr_prefix)
        else:
            if not validate_pnr(pnr_code):
                raise ValueError(f"Geçersiz PNR formatı (6 karakter olmalı): {pnr_code}")

        # Madde 24: Bilinmeyen kabin sınıfı kontrolü
        if isinstance(cabin_class, str):
            clean_class = cabin_class.strip().upper()
            if clean_class in ("BUSINESS", "EKONOMI", "ECONOMY"):
                cabin_enum = CabinClass.BUSINESS if clean_class == "BUSINESS" else CabinClass.ECONOMY
            else:
                raise ValueError(f"Geçersiz kabin sınıfı: '{cabin_class}'. İzin verilenler: BUSINESS, ECONOMY.")
        elif isinstance(cabin_class, CabinClass):
            cabin_enum = cabin_class
        else:
            raise ValueError(f"Geçersiz kabin sınıfı türü: {type(cabin_class)}")

        boarding_time = departure_time - timedelta(minutes=40)
        price_dec = Decimal(str(total_price))

        if not baggage_allowance:
            baggage_allowance = "30 Kg Bagaj + 8 Kg Kabin" if cabin_enum == CabinClass.BUSINESS else "20 Kg Bagaj + 8 Kg Kabin"

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
            total_price=price_dec,
            ticket_status=ticket_status,
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
        """Verilen bileti PDF formatında diske kaydeder."""
        if not output_path:
            out_dir = Path("output")
            out_dir.mkdir(exist_ok=True)
            output_path = out_dir / f"ticket_{ticket.ticket.pnr_code}_{ticket.ticket.seat_number}.pdf"

        return generate_ticket_pdf(ticket, output_path)

    @classmethod
    def issue_ticket_pdf_bytes(cls, ticket: FlightTicket) -> bytes:
        """Verilen bileti doğrudan bellekte PDF bayt dizisi (bytes) olarak döner."""
        return generate_ticket_pdf_bytes(ticket)

    @classmethod
    def get_ticket_from_db(
        cls,
        pnr_code: str,
        last_name: Optional[str] = None,
        db_manager=None,
    ) -> Optional[FlightTicket]:
        """
        Madde 7, 31, 32:
        - Madde 31: v_flight_search view'ı yerine doğrudan flights ve airports tabloları join edilir (sadeleştirme).
        - Madde 7: Güvenlik için soyadı kontrolü desteklenir (PNR + Soyad sorgulaması).
        - Madde 32: created_at saat dilimi düzgün işlenir.
        - Madde 21: Uydurma vergi bölünmesi yapılmaz, veritabanındaki gerçek tutar kullanılır.
        """
        db = db_manager or default_db_manager
        clean_pnr = pnr_code.strip().upper()

        query = """
        SELECT b.pnr_code, b.booking_status, b.total_price, b.created_at,
               b.passenger_first_name, b.passenger_last_name, b.passenger_identity_number,
               b.passenger_email, b.passenger_phone,
               s.seat_number, s.seat_class,
               f.flight_number, f.departure_time, f.arrival_time,
               da.iata_code AS dep_code, da.city AS dep_city, da.name AS dep_airport,
               aa.iata_code AS arr_code, aa.city AS arr_city, aa.name AS arr_airport
        FROM bookings b
        JOIN flight_seats s   ON s.id = b.seat_id
        JOIN flights f        ON f.id = b.flight_id
        JOIN airports da      ON da.id = f.departure_airport_id
        JOIN airports aa      ON aa.id = f.arrival_airport_id
        WHERE b.pnr_code = %s
        """
        params = [clean_pnr]

        # Madde 7: Güvenlik amaçlı soyadı kontrolü (varsa)
        if last_name:
            query += " AND LOWER(b.passenger_last_name) = LOWER(%s)"
            params.append(last_name.strip())

        query += ";"

        with db.get_cursor(commit=False) as cursor:
            cursor.execute(query, tuple(params))
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
                airline_name="SkyWings Airlines",
                origin_code=dep_code,
                origin_name=f"{dep_city} ({dep_airport})",
                destination_code=arr_code,
                destination_name=f"{arr_city} ({arr_airport})",
                departure_datetime=dep_time,
                arrival_datetime=arr_time,
                boarding_time=boarding_time,
                gate=None,          # Madde 21: Bilinmeyen kapı bilgisi verilmez
                terminal=None,
                aircraft_type=None,
            )

            # Madde 32: Saat dilimi dönüşümü
            booking_dt = created_at
            if hasattr(booking_dt, "astimezone"):
                booking_dt = booking_dt.astimezone()

            ticket_details = TicketDetails(
                pnr_code=pnr,
                seat_number=s_number,
                cabin_class=cabin,
                baggage_allowance="30 Kg Bagaj + 8 Kg Kabin" if cabin == CabinClass.BUSINESS else "20 Kg Bagaj + 8 Kg Kabin",
                total_price=Decimal(str(total_price)),
                currency="TRY",
                payment_method="Elektronik Tahsilat",
                booking_date=booking_dt.replace(tzinfo=None) if hasattr(booking_dt, "replace") else booking_dt,
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
        last_name: Optional[str] = None,
        output_path: Optional[Union[str, Path]] = None,
        db_manager=None,
    ) -> Optional[str]:
        """Veritabanından PNR koduna göre bileti çekip PDF dosyasını üretir."""
        ticket = cls.get_ticket_from_db(pnr_code, last_name=last_name, db_manager=db_manager)
        if not ticket:
            return None
        return cls.issue_ticket_pdf(ticket, output_path=output_path)

    @classmethod
    def issue_pdf_bytes_from_db(
        cls,
        pnr_code: str,
        last_name: Optional[str] = None,
        db_manager=None,
    ) -> Optional[bytes]:
        """Veritabanından PNR koduna göre bileti çekip PDF bayt dizisi (bytes) döner."""
        ticket = cls.get_ticket_from_db(pnr_code, last_name=last_name, db_manager=db_manager)
        if not ticket:
            return None
        return cls.issue_ticket_pdf_bytes(ticket)
