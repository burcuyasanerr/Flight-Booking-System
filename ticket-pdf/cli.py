"""
Flight Ticket Purchasing System - CLI Tool
Komut satırı üzerinden PNR üretimi, doğrulaması ve PDF bilet oluşturma aracı.

Kullanım örnekleri:
    python cli.py --demo
    python cli.py --demo --output my_ticket.pdf
    python cli.py --generate-pnrs 5
    python cli.py --validate-pnr TK79AB
    python cli.py --name "Burcu" --surname "Yaşaner" --from IST --to ADB --flight TK1923 --seat 14B --price 1500
"""

import argparse
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Bulunduğu dizini sys.path'e ekle
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Windows console encoding uyumluluğu
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from models import CabinClass, TicketStatus
from pnr import generate_pnr, generate_unique_pnrs, validate_pnr
from service import TicketService


def run_demo(output_path: str = "demo_ticket.pdf"):
    """Gerçekçi örnek verilerle bir demo bilet PDF'i üretir."""
    print("=" * 60)
    print("[*] Ornek Ucus Bileti ve Binis Karti Uretiliyor...")
    print("=" * 60)

    now = datetime.now()
    dep_time = now.replace(microsecond=0) + timedelta(days=7, hours=3)
    arr_time = dep_time + timedelta(hours=1, minutes=15)

    pnr_code = generate_pnr(length=6, prefix="TK")
    print(f"[+] Uretilen PNR Kodu: {pnr_code}")

    ticket = TicketService.create_ticket(
        passenger_name="Burcu",
        passenger_surname="Yaşaner",
        flight_number="TK1923",
        airline_name="Türk Hava Yolları",
        origin_code="IST",
        origin_name="İstanbul Havalimanı",
        destination_code="ADB",
        destination_name="İzmir Adnan Menderes Havalimanı",
        departure_time=dep_time,
        arrival_time=arr_time,
        seat_number="12A",
        cabin_class=CabinClass.BUSINESS,
        baggage_allowance="30 Kg Bagaj + 8 Kg Kabin",
        base_price=2450.0,
        tax_amount=450.0,
        gate="214B",
        terminal="T1",
        pnr_code=pnr_code,
        identity_number="12345678901",
        email="burcu.yasaner@example.com",
        phone="+90 532 000 0000",
        aircraft_type="Airbus A321neo",
    )

    pdf_path = TicketService.issue_ticket_pdf(ticket, output_path=output_path)
    file_size_kb = Path(pdf_path).stat().st_size / 1024

    print(f"[OK] Bilet Basariyla Olusturuldu!")
    print(f"    - Yolcu: {ticket.passenger.full_name}")
    print(f"    - Guzergah: {ticket.flight.origin_code} -> {ticket.flight.destination_code}")
    print(f"    - Ucus No: {ticket.flight.flight_number}")
    print(f"    - Koltuk: {ticket.ticket.seat_number} ({ticket.ticket.cabin_class.value})")
    print(f"    - Toplam Tutar: {ticket.ticket.total_price:,.2f} {ticket.ticket.currency}")
    print(f"    - PDF Dosyasi: {pdf_path} ({file_size_kb:.1f} KB)")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Flight Ticket Purchasing System - PNR & PDF Bilet Üretim Aracı",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--demo", action="store_true", help="Örnek verilerle demo bilet PDF'i oluşturur.")
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
    parser.add_argument("--price", type=float, default=1500.0, help="Taban bilet fiyatı")

    args = parser.parse_args()

    if args.generate_pnrs:
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

    if args.demo:
        out = args.output or "demo_ticket.pdf"
        run_demo(out)
        return

    if args.name and args.surname:
        out = args.output or f"ticket_{args.name}_{args.seat}.pdf"
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
            base_price=args.price,
            tax_amount=args.price * 0.18,
        )
        pdf_path = TicketService.issue_ticket_pdf(ticket, output_path=out)
        print(f"Bilet oluşturuldu: {pdf_path} (PNR: {ticket.ticket.pnr_code})")
        return

    # Varsayılan: Demo çalıştır
    run_demo(args.output or "demo_ticket.pdf")


if __name__ == "__main__":
    main()
