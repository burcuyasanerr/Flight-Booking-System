"""
Flight Ticket Purchasing System - Concurrency CLI Tool
Komut satırı üzerinden eşzamanlılık simülasyonu, koltuk listeleme ve kilit testi aracı.

Kullanım örnekleri:
    python cli.py --status
    python cli.py --list-seats --flight 1
    python cli.py --simulate --seat 2 --users 10
    python cli.py --lock --seat 2 --session test_user
    python cli.py --release --seat 2 --session test_user
    python cli.py --cleanup
"""

import argparse
from pathlib import Path
import sys

# Bulunduğu dizini sys.path'e ekle
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Windows terminal çıktı uyumluluğu
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from db import db_manager
from lock_manager import SeatLockManager
from simulator import ConcurrencySimulator


def print_banner():
    print("=" * 65)
    print("   ✈️  FLIGHT BOOKING SYSTEM - EŞZAMANLILIK (CONCURRENCY) YÖNETİCİSİ")
    print("=" * 65)


def cmd_status():
    print_banner()
    print("[*] PostgreSQL Veritabanı Bağlantısı Test Ediliyor...")
    connected = db_manager.check_connection()
    if connected:
        print("[OK] Veritabanı bağlantısı AKTİF ve ÇALIŞIYOR!")
        print(f"     Host: {db_manager.config.host}:{db_manager.config.port}")
        print(f"     Veritabanı: {db_manager.config.dbname}")
        print(f"     Kullanıcı: {db_manager.config.user}")
    else:
        print("[HATA] Veritabanına bağlanılamadı!")
        print("       Lütfen PostgreSQL servisinin çalıştığından ve şifrenin doğru olduğundan emin olun.")
    print("=" * 65)


def cmd_list_seats(flight_id: int):
    print_banner()
    lock_mgr = SeatLockManager()
    print(f"[*] Uçuş ID: {flight_id} Koltuk Haritası Listeleniyor...")
    seats = lock_mgr.get_flight_seats(flight_id)

    if not seats:
        print(f"[!] Uçuş ID {flight_id} için koltuk bulunamadı.")
        return

    print(f"\n{'ID':<5} {'KOLTUK':<8} {'SINIF':<10} {'DURUM':<12} {'ETKİN DURUM':<14} {'SÜRÜM':<6} {'KİLİTLEYEN'}")
    print("-" * 65)
    for s in seats:
        lock_info = s.locked_by_session or "-"
        print(f"{s.id:<5} {s.seat_number:<8} {s.seat_class.value:<10} {s.status.value:<12} {s.effective_status.value:<14} {s.version:<6} {lock_info}")
    print("=" * 65)


def cmd_simulate(seat_id: int, users: int, pessimistic: bool):
    print_banner()
    lock_mgr = SeatLockManager()
    seat = lock_mgr.get_seat(seat_id)

    if not seat:
        print(f"[HATA] Koltuk ID {seat_id} bulunamadı!")
        return

    mode_name = "Pessimistic (FOR UPDATE)" if pessimistic else "Optimistic (Version Sayacı)"
    print(f"[*] EŞZAMANLI YARIŞ KOŞULU (RACE CONDITION) SİMÜLASYONU BAŞLATILIYOR")
    print(f"    - Hedef Koltuk: ID {seat.id} ({seat.seat_number} - {seat.seat_class.value})")
    print(f"    - Başlangıç Sürümü: v{seat.version}")
    print(f"    - Mevcut Durum: {seat.effective_status.value}")
    print(f"    - Eşzamanlı Kullanıcı Sayısı: {users}")
    print(f"    - Kilitleme Stratejisi: {mode_name}")
    print("-" * 65)

    sim = ConcurrencySimulator(lock_mgr)
    report = sim.run_concurrent_lock_test(
        seat_id=seat_id,
        concurrent_users=users,
        use_pessimistic=pessimistic,
    )

    print(f"\n[+] SİMÜLASYON TAMAMLANDI! ({report.duration_ms:.2f} ms)")
    print(f"    - Toplam İstek: {report.total_attempts}")
    print(f"    - Başarılı Kilit: {report.successful_locks} adet (İstenen: Tam 1)")
    print(f"    - Engellenen / Çakışan: {report.failed_locks} adet")
    print(f"    - Çakışma Tespiti: {report.conflicts_detected} adet")
    print(f"    - Koltuk Yeni Sürümü: v{report.final_version}")

    if report.is_consistent:
        print("\n>>> [BAŞARILI] Eşzamanlılık testi %100 BAŞARILI!")
        print(">>> Yarışan kullanıcılardan yalnızca 1'i kilidi alabildi, diğerlerinin çakışması engellendi.")
        print(">>> Veritabanı bütünlüğü kusursuz korundu (Çift rezervasyon İMKANSIZ).")
    else:
        print("\n>>> [UYARI] Tutarsızlık tespit edildi! (Birden fazla kilit verildi veya hepsi başarısız)")
    print("=" * 65)


def cmd_cleanup():
    print_banner()
    lock_mgr = SeatLockManager()
    print("[*] Süresi dolmuş kilitler temizleniyor...")
    count = lock_mgr.cleanup_expired_locks()
    print(f"[OK] {count} adet zaman aşımına uğramış kilit serbest bırakıldı.")
    print("=" * 65)


def main():
    parser = argparse.ArgumentParser(
        description="Flight Ticket Purchasing System - Koltuk Kilitleme & Concurrency CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--status", action="store_true", help="Veritabanı bağlantı durumunu kontrol eder.")
    parser.add_argument("--list-seats", action="store_true", help="Uçuş koltuklarını listeler.")
    parser.add_argument("--flight", type=int, default=1, help="Uçuş ID numarası (Varsayılan: 1).")
    parser.add_argument("--simulate", action="store_true", help="Eşzamanlı yarış simülasyonunu çalıştırır.")
    parser.add_argument("--seat", type=int, default=2, help="Kilitlenecek veya simüle edilecek koltuk ID'si.")
    parser.add_argument("--users", type=int, default=10, help="Simülasyonda yarışacak eşzamanlı kullanıcı sayısı.")
    parser.add_argument("--pessimistic", action="store_true", help="Pessimistic locking modunu kullanır.")
    parser.add_argument("--cleanup", action="store_true", help="Süresi dolmuş kilitleri temizler.")

    args = parser.parse_args()

    if args.status:
        cmd_status()
        return

    if args.list_seats:
        cmd_list_seats(args.flight)
        return

    if args.simulate:
        cmd_simulate(args.seat, args.users, args.pessimistic)
        return

    if args.cleanup:
        cmd_cleanup()
        return

    # Argümansız çağrılırsa durum göster
    cmd_status()


if __name__ == "__main__":
    main()
