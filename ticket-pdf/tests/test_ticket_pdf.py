"""
Flight Ticket Purchasing System - Ticket & PNR Unit Tests
PNR algoritması, veri modelleri ve PDF üretim bileşenlerinin birim testleri.
"""

from datetime import datetime, timedelta
import os
from pathlib import Path
import sys
import unittest

# Modül yolunu ekle
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from models import CabinClass, FlightInfo, FlightTicket, Passenger, TicketDetails, TicketStatus
from pdf_generator import generate_ticket_pdf, generate_ticket_pdf_bytes
from pnr import (
    SAFE_PNR_ALPHABET,
    generate_deterministic_pnr,
    generate_pnr,
    generate_unique_pnrs,
    validate_pnr,
)
from service import TicketService


class TestPNRGenerator(unittest.TestCase):
    """PNR üretim ve doğrulama testleri"""

    def test_generate_pnr_default(self):
        pnr = generate_pnr()
        self.assertEqual(len(pnr), 6)
        self.assertTrue(validate_pnr(pnr))
        # Güvenli alfabe karakterleri
        for ch in pnr:
            self.assertIn(ch, SAFE_PNR_ALPHABET)

    def test_generate_pnr_with_prefix(self):
        pnr = generate_pnr(length=6, prefix="TK")
        self.assertEqual(len(pnr), 6)
        self.assertTrue(pnr.startswith("TK"))
        self.assertTrue(validate_pnr(pnr))

    def test_validate_pnr(self):
        self.assertTrue(validate_pnr("TK79AB"))
        self.assertTrue(validate_pnr("A1B2C3"))
        self.assertFalse(validate_pnr("123"))  # Çok kısa
        self.assertFalse(validate_pnr("TOOLONGLOCATOR"))  # Çok uzun
        self.assertFalse(validate_pnr("TK-123"))  # Geçersiz karakter (-)
        self.assertFalse(validate_pnr(""))
        self.assertFalse(validate_pnr(None))

    def test_generate_unique_pnrs(self):
        count = 100
        pnrs = generate_unique_pnrs(count=count, length=6)
        self.assertEqual(len(pnrs), count)
        for pnr in pnrs:
            self.assertTrue(validate_pnr(pnr))

    def test_generate_deterministic_pnr(self):
        pnr1 = generate_deterministic_pnr("TK1923", "12A", "BURCU YASANER")
        pnr2 = generate_deterministic_pnr("TK1923", "12A", "BURCU YASANER")
        pnr3 = generate_deterministic_pnr("TK1923", "12B", "BURCU YASANER")
        # Aynı girdiler daima aynı PNR'ı üretmeli
        self.assertEqual(pnr1, pnr2)
        # Farklı koltuk farklı PNR üretmeli
        self.assertNotEqual(pnr1, pnr3)
        self.assertEqual(len(pnr1), 6)


class TestModels(unittest.TestCase):
    """Veri modelleri testleri"""

    def test_passenger_full_name(self):
        p = Passenger(first_name="  burcu  ", last_name="yaşaner ")
        self.assertEqual(p.full_name, "BURCU YAŞANER")

    def test_flight_duration_calculation(self):
        dep = datetime(2026, 5, 10, 14, 0)
        arr = datetime(2026, 5, 10, 15, 45)
        flight = FlightInfo(
            flight_number="TK1923",
            origin_code="ist",
            origin_name="İstanbul",
            destination_code="adb",
            destination_name="İzmir",
            departure_datetime=dep,
            arrival_datetime=arr,
        )
        self.assertEqual(flight.origin_code, "IST")
        self.assertEqual(flight.destination_code, "ADB")
        self.assertEqual(flight.duration_formatted, "1 sa 45 dk")


class TestPDFGeneration(unittest.TestCase):
    """PDF oluşturma ve servis testleri"""

    def setUp(self):
        self.test_output = Path(__file__).parent / "temp_test_ticket.pdf"
        dep = datetime.now() + timedelta(days=2)
        arr = dep + timedelta(hours=1, minutes=20)
        self.sample_ticket = TicketService.create_ticket(
            passenger_name="Ahmet",
            passenger_surname="Demir",
            flight_number="TK2026",
            origin_code="IST",
            origin_name="İstanbul Havalimanı",
            destination_code="AYT",
            destination_name="Antalya Havalimanı",
            departure_time=dep,
            arrival_time=arr,
            seat_number="08C",
            base_price=1200.0,
            tax_amount=250.0,
            cabin_class=CabinClass.ECONOMY,
        )

    def tearDown(self):
        if self.test_output.exists():
            try:
                self.test_output.unlink()
            except Exception:
                pass

    def test_generate_ticket_pdf_file(self):
        out_path = generate_ticket_pdf(self.sample_ticket, self.test_output)
        self.assertTrue(Path(out_path).exists())
        file_size = Path(out_path).stat().st_size
        self.assertGreater(file_size, 10000, "PDF dosyası en az 10 KB olmalıdır.")

    def test_generate_ticket_pdf_bytes(self):
        pdf_bytes = generate_ticket_pdf_bytes(self.sample_ticket)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"), "Geçerli bir PDF bayt dizisi olmalıdır.")
        self.assertGreater(len(pdf_bytes), 10000)

    def test_ticket_service_end_to_end(self):
        self.assertIsNotNone(self.sample_ticket.ticket.pnr_code)
        self.assertTrue(validate_pnr(self.sample_ticket.ticket.pnr_code))
        self.assertEqual(self.sample_ticket.ticket.total_price, 1450.0)


if __name__ == "__main__":
    unittest.main()
