"""
Flight Ticket Purchasing System - CLI Tool
Komut satırı üzerinden PNR üretimi, doğrulaması ve PDF bilet oluşturma aracı.

Kullanım örnekleri:
    python -m ticket_pdf.cli --demo
    python -m ticket_pdf.cli --demo --output my_ticket.pdf
    python -m ticket_pdf.cli --generate-pnrs 5
    python -m ticket_pdf.cli --validate-pnr TK79AB
    python -m ticket_pdf.cli --pnr TK19AB
    python -m ticket_pdf.cli --name "Burcu" --surname "Yaşaner" --from IST --to ADB --flight TK1923 --seat 14B --price 1500
"""

import argparse
from datetime import datetime, timedelta
from pathlib import Path
import re
import sys

# Windows console encoding uyumluluğu
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from ticket_pdf.models import CabinClass, TicketStatus
from ticket_pdf.pnr import generate_pnr, generate_unique_pnrs, validate_pnr
from ticket_pdf.service import TicketService


def sanitize_filename(filename: str) -> str:
    """Madde 29: Dosya adındaki geçersiz karakterleri (/ \ : * ? " < > |) temizler."""
    return re.sub(r'[\\/*?:"<>|]', "_", filename).strip()


def run_demo(output_path: str = "demo_ticket.pdf"):
    """Gerçekçi örnek verilerle bir demo bilet PDF'i üretir."""
    print("=" * 60)
    print("[*] Örnek Uçuş Bileti ve Biniş Kartı Üretiliyor...")
    print("=" * 60)

    now = datetime.now()
    dep_time = now.replace(microsecond=0) + timedelta(days=7, hours=3)
    arr_time = dep_time + timedelta(hours=1, minutes=15)

    pnr_code = generate_pnr(length=6, prefix="TK")
    print(f"[+] Üretilen PNR Kodu: {pnr_code}")

    ticket = TicketService.create_ticket(
        passenger_name="Emine",
        passenger_surname="Şirin",
        flight_number="TK-2101",
        airline_name="Türk Hava Yolları",
        origin_code="IST",
        origin_name="İstanbul Havalimanı",
        destination_code="ESB",
        destination_name="Esenboğa Havalimanı",
        departure_time=dep_time,
        arrival_time=arr_time,
        seat_number="1A",
        cabin_class=CabinClass.BUSINESS,
        baggage_allowance="30 Kg Bagaj + 8 Kg Kabin",
        total_price=2175.00,
        gate=None,
        terminal=None,
        pnr_code=pnr_code,
        identity_number="12345678901",
        email="emine.sirin@example.com",
        phone="+90 532 000 0000",
    )

    clean_out = sanitize_filename(output_path)
    pdf_path = TicketService.issue_ticket_pdf(ticket, output_path=clean_out)
    file_size_kb = Path(pdf_path).stat().st_size / 1024

    print(f"[OK] Bilet Başarıyla Oluşturuldu!")
    print(f"    - Yolcu: {ticket.passenger.full_name}")
    print(f"    - Güzergah: {ticket.flight.origin_code} -> {ticket.flight.destination_code}")
    print(f"    - Uçuş No: {ticket.flight.flight_number}")
    print(f"    - Koltuk: {ticket.ticket.seat_number} ({ticket.ticket.cabin_class.display_name})")
    print(f"    - Toplam Tutar: {ticket.ticket.total_price:,.2f} {ticket.ticket.currency}")
    print(f"    - PDF Dosyası: {pdf_path} ({file_size_kb:.1f} KB)")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Flight Ticket Purchasing System - PNR & PDF Bilet Üretim Aracı",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--demo", action="store_true", help="Örnek verilerle demo bilet PDF'i oluşturur.")
    parser.add_argument("--pnr", type=str, metavar="PNR", help="Veritabanından PNR koduna göre bileti çekip PDF oluşturur (Örn: TK19AB).")
    parser.add_argument("--last-name", type=str, metavar="SOYAD", help="Güvenlik amaçlı yolcu soyadı doğrulaması.")
    parser.add_argument("--output", "-o", default=None, help="Çıktı PDF dosyasının kaydedileceği yol.")
    parser.add_argument("--generate-pnrs", type=int, metavar="N", help="N adet benzersiz IATA uyumlu PNR kodu üretir.")
    parser.add_argument("--validate-pnr", type=str, metavar="PNR", help="Verilen PNR kodunun geçerliliğini denetler.")

    # Özel bilet parametreleri
    parser.add_argument("--name", help="Yolcu adı")
    parser.add_argument("--surname", help="Yolcu soyadı")
    parser.add_argument("--flight", default="TK1923", help="Uçuş kodu (Örn: TK1923)")
    parser.add_argument("--from", dest="origin", default="IST", help="Kalkış IATA kodu (Örn: IST)")
    parser.add_argument("--to", dest="destination", default="ADB", help="Varış IATA kodu (Örn: ADB)")
    parser.add_argument("--seat", default="14A", help="Koltuk numarası (Örn: 14A)")
    parser.add_argument("--price", type=float, default=1500.0, help="Toplam bilet fiyatı")

    args = parser.parse_args()

    # Madde 29: args.generate_pnrs is not None kontrolü (0 verildiğinde demo çalışmasın)
    if args.generate_pnrs is not None:
        if args.generate_pnrs <= 0:
            print("Üretilecek PNR adedi 0'dan büyük olmalıdır.")
            return
        print(f"--- {args.generate_pnrs} Adet Benzersiz PNR Kodu ---")
        pnrs = generate_unique_pnrs(args.generate_pnrs)
        for i, pnr in enumerate(sorted(pnrs), 1):
            print(f"{i:2d}. {pnr}")
        return

    if args.validate_pnr:
        is_valid = validate_pnr(args.validate_pnr)
        status = "GEÇERLİ (VALID)" if is_valid else "GEÇERSİZ (INVALID)"
        print(f"PNR '{args.validate_pnr}': {status}")
        return

    if args.pnr:
        default_out = f"ticket_{args.pnr.upper()}.pdf"
        out = sanitize_filename(args.output or default_out)
        print(f"[*] Veritabanından PNR '{args.pnr.upper()}' sorgulanıyor...")
        pdf_path = TicketService.issue_pdf_from_db(args.pnr, last_name=args.last_name, output_path=out)
        if not pdf_path:
            print(f"[!] HATA: Veritabanında '{args.pnr.upper()}' kodlu bir bilet bulunamadı (veya soyadı eşleşmedi)!")
            return
        file_size_kb = Path(pdf_path).stat().st_size / 1024
        print(f"[OK] Bilet veritabanından çekildi ve PDF başarıyla üretildi!")
        print(f"     PDF Dosyası: {pdf_path} ({file_size_kb:.1f} KB)")
        return

    if args.demo:
        out = args.output or "demo_ticket.pdf"
        run_demo(out)
        return

    if args.name and args.surname:
        raw_name = f"ticket_{args.name}_{args.seat}.pdf"
        out = sanitize_filename(args.output or raw_name)
        dep = datetime.now() + timedelta(days=3, hours=4)
        arr = dep + timedelta(hours=1, minutes=20)
        ticket = TicketService.create_ticket(
            passenger_name=args.name,
            passenger_surname=args.surname,
            flight_number=args.flight,
            origin_code=args.origin,
            origin_name=f"{args.origin} Havalimanı",
            destination_code=args.destination,
            destination_name=f"{args.destination} Havalimanı",
            departure_time=dep,
            arrival_time=arr,
            seat_number=args.seat,
            total_price=args.price,
        )
        pdf_path = TicketService.issue_ticket_pdf(ticket, output_path=out)
        print(f"Bilet oluşturuldu: {pdf_path} (PNR: {ticket.ticket.pnr_code})")
        return

    # Varsayılan: Demo çalıştır
    run_demo(args.output or "demo_ticket.pdf")


if __name__ == "__main__":
    main()
