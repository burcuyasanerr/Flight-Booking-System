"""
ticket-pdf modülü
Uçuş biletleme sistemi için PNR kodu üretimi, doğrulaması ve PDF bilet çıktısı oluşturma araçları.
"""

try:
    from .models import (
        CabinClass,
        FlightInfo,
        FlightTicket,
        Passenger,
        TicketDetails,
        TicketStatus,
    )
    from .pnr import (
        generate_deterministic_pnr,
        generate_pnr,
        generate_unique_pnrs,
        validate_pnr,
    )
    from .pdf_generator import (
        TicketPDFBuilder,
        generate_ticket_pdf,
        generate_ticket_pdf_bytes,
    )
    from .service import TicketService
except ImportError:
    from models import (
        CabinClass,
        FlightInfo,
        FlightTicket,
        Passenger,
        TicketDetails,
        TicketStatus,
    )
    from pnr import (
        generate_deterministic_pnr,
        generate_pnr,
        generate_unique_pnrs,
        validate_pnr,
    )
    from pdf_generator import (
        TicketPDFBuilder,
        generate_ticket_pdf,
        generate_ticket_pdf_bytes,
    )
    from service import TicketService

__all__ = [
    "CabinClass",
    "TicketStatus",
    "Passenger",
    "FlightInfo",
    "TicketDetails",
    "FlightTicket",
    "generate_pnr",
    "generate_deterministic_pnr",
    "validate_pnr",
    "generate_unique_pnrs",
    "TicketPDFBuilder",
    "generate_ticket_pdf",
    "generate_ticket_pdf_bytes",
    "TicketService",
]
