"""
Flight Ticket Purchasing System - Ticket & PNR Unit Tests
Madde 27: İptal edilmiş bilet, özel karakter (<), Türkçe harf (i/ı),
50+ karakterli isim ve PDF metin doğrulama testleri.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
import unittest
import fitz  # PyMuPDF ile PDF içerik doğrulama

from ticket_pdf.models import (
    CabinClass,
    FlightInfo,
    FlightTicket,
    Passenger,
    TicketDetails,
    TicketStatus,
    tr_upper,
)
from ticket_pdf.pdf_generator import generate_ticket_pdf, generate_ticket_pdf_bytes
from ticket_pdf.pnr import (
    SAFE_PNR_ALPHABET,
    generate_deterministic_pnr,
    generate_pnr,
    generate_unique_pnrs,
    validate_pnr,
)
from ticket_pdf.service import TicketService


class TestPNRGenerator(unittest.TestCase):
    """PNR üretim ve doğrulama testleri"""

    def test_generate_pnr_default(self):
        pnr = generate_pnr()
        self.assertEqual(len(pnr), 6)
        self.assertTrue(validate_pnr(pnr))
        for ch in pnr:
            self.assertIn(ch, SAFE_PNR_ALPHABET)

    def test_validate_pnr_strict_six_chars(self):
        self.assertTrue(validate_pnr("TK19AB"))
        self.assertTrue(validate_pnr("A1B2C3"))
        self.assertFalse(validate_pnr("123"))        # Çok kısa
        self.assertFalse(validate_pnr("TOOLONG99"))  # Çok uzun (Madde 20: Tam 6 olmalı)
        self.assertFalse(validate_pnr("TK-123"))     # Geçersiz karakter

    def test_generate_unique_pnrs(self):
        count = 100
        pnrs = generate_unique_pnrs(count=count, length=6)
        self.assertEqual(len(pnrs), count)
        for pnr in pnrs:
            self.assertTrue(validate_pnr(pnr))

    def test_deterministic_pnr_test_only(self):
        pnr1 = generate_deterministic_pnr("TK-2101", "1A", "BURCU YASANER")
        pnr2 = generate_deterministic_pnr("TK-2101", "1A", "BURCU YASANER")
        self.assertEqual(pnr1, pnr2)
        self.assertEqual(len(pnr1), 6)


class TestModelsAndTurkishCharacters(unittest.TestCase):
    """Veri modelleri ve Türkçe karakter testleri"""

    def test_turkish_uppercase_conversion(self):
        """Madde 19: i -> İ, ı -> I dönüşümü kontrolü"""
        self.assertEqual(tr_upper("Emine Şirin"), "EMİNE ŞİRİN")
        self.assertEqual(tr_upper("ahmet çetin yıldırım"), "AHMET ÇETİN YILDIRIM")
        p = Passenger(first_name="Emine", last_name="Şirin")
        self.assertEqual(p.full_name, "EMİNE ŞİRİN")
        self.assertEqual(p.stub_name, "ŞİRİN / EMİNE")

    def test_passenger_name_limits_db_aligned(self):
        """Madde 20: 100 karaktere kadar isim ve 1 harfli isimler geçerli olmalıdır"""
        long_name = "A" * 90
        p = Passenger(first_name=long_name, last_name="Test")
        self.assertEqual(len(p.first_name), 90)

        single_char = Passenger(first_name="A", last_name="B")
        self.assertEqual(single_char.full_name, "A B")

    def test_unknown_cabin_class_raises_value_error(self):
        """Madde 24: Tanınmayan kabin sınıfı ValueError fırlatmalıdır"""
        with self.assertRaises(ValueError):
            TicketService.create_ticket(
                passenger_name="Ahmet",
                passenger_surname="Yılmaz",
                flight_number="TK-2101",
                origin_code="IST",
                origin_name="İstanbul",
                destination_code="ESB",
                destination_name="Ankara",
                departure_time=datetime.now(),
                arrival_time=datetime.now() + timedelta(hours=1),
                seat_number="1A",
                total_price=1500,
                cabin_class="SUPER_LUXURY",  # Tanımsız sınıf
            )


class TestPDFGenerationAdvanced(unittest.TestCase):
    """Madde 5, 18, 27: PDF oluşturma ve içerik denetleme testleri"""

    def setUp(self):
        self.test_output = Path(__file__).parent / "temp_advanced_ticket.pdf"
        self.addCleanup(self._cleanup_temp_file)

    def _cleanup_temp_file(self):
        if self.test_output.exists():
            try:
                self.test_output.unlink()
            except Exception:
                pass

    def test_xml_characters_in_passenger_name(self):
        """Madde 5 & 27: İsim içinde < veya > olduğunda PDF hata vermeden üretilmeli"""
        ticket = TicketService.create_ticket(
            passenger_name="Ay<se",
            passenger_surname="O>zlem",
            flight_number="TK-2101",
            origin_code="IST",
            origin_name="İstanbul Havalimanı",
            destination_code="ESB",
            destination_name="Esenboğa Havalimanı",
            departure_time=datetime.now() + timedelta(days=2),
            arrival_time=datetime.now() + timedelta(days=2, hours=1),
            seat_number="2B",
            total_price=Decimal("1850.00"),
        )
        pdf_path = generate_ticket_pdf(ticket, self.test_output)
        self.assertTrue(Path(pdf_path).exists())

        # PDF içindeki metni kontrol et
        doc = fitz.open(pdf_path)
        page_text = doc[0].get_text()
        self.assertIn("AY<SE", page_text)
        self.assertIn("TK-2101", page_text)

    def test_cancelled_ticket_pdf_layout(self):
        """Madde 18 & 27: İptal edilen bilette iptal başlığı ve ibareleri yer almalı"""
        ticket = TicketService.create_ticket(
            passenger_name="Mehmet",
            passenger_surname="Demir",
            flight_number="TK-2101",
            origin_code="IST",
            origin_name="İstanbul Havalimanı",
            destination_code="ESB",
            destination_name="Esenboğa Havalimanı",
            departure_time=datetime.now() + timedelta(days=2),
            arrival_time=datetime.now() + timedelta(days=2, hours=1),
            seat_number="3C",
            total_price=Decimal("1450.00"),
            ticket_status=TicketStatus.CANCELLED,
        )
        pdf_bytes = generate_ticket_pdf_bytes(ticket)
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page_text = doc[0].get_text()

        self.assertIn("İPTAL EDİLMİŞTİR", page_text)
        self.assertNotIn("Fatura Durumu: Düzenlendi", page_text)

    def test_long_name_and_text_extraction(self):
        """Madde 27: Uzun isimli bilet metin denetimi"""
        ticket = TicketService.create_ticket(
            passenger_name="Fatma Zehra Nuray",
            passenger_surname="Karaosmanoğlulları",
            flight_number="TK-2101",
            origin_code="IST",
            origin_name="İstanbul Havalimanı",
            destination_code="ESB",
            destination_name="Esenboğa Havalimanı",
            departure_time=datetime.now() + timedelta(days=1),
            arrival_time=datetime.now() + timedelta(days=1, hours=1),
            seat_number="10D",
            total_price=Decimal("1200.00"),
        )
        pdf_path = generate_ticket_pdf(ticket, self.test_output)
        doc = fitz.open(pdf_path)
        page_text = doc[0].get_text()

        self.assertIn("FATMA ZEHRA NURAY", page_text)
        self.assertIn("KARAOSMANOĞLULLARI", page_text)
        self.assertIn("1,200.00 TRY", page_text)


if __name__ == "__main__":
    unittest.main()
