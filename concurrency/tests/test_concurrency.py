"""
Flight Ticket Purchasing System - Concurrency Unit & Integration Tests
Optimistic locking, veri modelleri, kilit yöneticisi ve çoklu iş parçacığı testleri.
"""

import unittest
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Modül yolunu ekle
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from db import DatabaseManager, db_manager
from lock_manager import SeatLockManager
from models import (
    BookingResult,
    LockResult,
    ReleaseResult,
    SeatClass,
    SeatInfo,
    SeatStatus,
)
from simulator import ConcurrencySimulator


class TestConcurrencyModels(unittest.TestCase):
    """Veri modelleri ve durum kontrolleri testleri"""

    def test_seat_info_creation(self):
        seat = SeatInfo(
            id=1,
            flight_id=1,
            seat_number="1A",
            seat_class=SeatClass.BUSINESS,
            price_multiplier=1.5,
            status=SeatStatus.AVAILABLE,
            effective_status=SeatStatus.AVAILABLE,
            version=1,
        )
        self.assertEqual(seat.seat_number, "1A")
        self.assertEqual(seat.status, SeatStatus.AVAILABLE)
        self.assertEqual(seat.version, 1)

    def test_lock_result_conflict(self):
        result = LockResult(
            success=False,
            seat_id=1,
            session_id="user_test",
            conflict_detected=True,
            conflict_reason="VERSION_MISMATCH_RACE_CONDITION",
            message="Çakışma tespit edildi",
        )
        self.assertFalse(result.success)
        self.assertTrue(result.conflict_detected)
        self.assertEqual(result.conflict_reason, "VERSION_MISMATCH_RACE_CONDITION")


class TestLiveConcurrency(unittest.TestCase):
    """Canlı PostgreSQL veritabanı üzerindeki eşzamanlılık testleri"""

    @classmethod
    def setUpClass(cls):
        cls.is_db_connected = db_manager.check_connection()
        cls.lock_mgr = SeatLockManager(db_manager)

    def setUp(self):
        if not self.is_db_connected:
            self.skipTest("PostgreSQL veritabanı bağlantısı aktif değil, canlı testler atlandı.")

    def test_get_flight_seats(self):
        seats = self.lock_mgr.get_flight_seats(flight_id=1)
        self.assertGreater(len(seats), 0, "Uçuş 1 için en az 1 koltuk bulunmalı.")
        first_seat = seats[0]
        self.assertIsInstance(first_seat.version, int)
        self.assertIn(first_seat.status, [SeatStatus.AVAILABLE, SeatStatus.LOCKED, SeatStatus.BOOKED])

    def test_optimistic_lock_and_release_lifecycle(self):
        # Boş bir koltuk bul (Örn: 2A veya 2B)
        seats = self.lock_mgr.get_flight_seats(flight_id=1)
        avail = [s for s in seats if s.effective_status == SeatStatus.AVAILABLE]
        if not avail:
            self.skipTest("Test için boş koltuk bulunamadı.")

        target = avail[-1]
        session_a = "test_lifecycle_session_a"
        session_b = "test_lifecycle_session_b"

        # 1. Oturum A koltuğu kilitler (Başarılı olmalı)
        res_a = self.lock_mgr.lock_seat_optimistic(
            seat_id=target.id,
            session_id=session_a,
            expected_version=target.version,
            lock_minutes=2,
        )
        self.assertTrue(res_a.success)
        self.assertEqual(res_a.new_version, target.version + 1)

        # 2. Oturum B aynı koltuğu eski sürümle kilitlemeye çalışır (Yarış Koşulu -> Başarısız olmalı)
        res_b = self.lock_mgr.lock_seat_optimistic(
            seat_id=target.id,
            session_id=session_b,
            expected_version=target.version,  # Eski sürüm
            lock_minutes=2,
        )
        self.assertFalse(res_b.success)
        self.assertTrue(res_b.conflict_detected)

        # 3. Oturum A kilidi serbest bırakır
        rel = self.lock_mgr.release_seat_lock(seat_id=target.id, session_id=session_a)
        self.assertTrue(rel.success)

        # 4. Koltuk tekrar AVAILABLE olmalı
        refreshed = self.lock_mgr.get_seat(target.id)
        self.assertEqual(refreshed.status, SeatStatus.AVAILABLE)

    def test_concurrent_simulation_race_condition(self):
        """10 kullanıcının aynı anda aynı koltuğu kilitleme yarış testi"""
        seats = self.lock_mgr.get_flight_seats(flight_id=1)
        avail = [s for s in seats if s.effective_status == SeatStatus.AVAILABLE]
        if not avail:
            self.skipTest("Simülasyon için boş koltuk bulunamadı.")

        target_seat = avail[0]
        sim = ConcurrencySimulator(self.lock_mgr)

        report = sim.run_concurrent_lock_test(
            seat_id=target_seat.id,
            concurrent_users=8,
            use_pessimistic=False,
        )

        # Tam olarak 1 kazanan olmalı
        self.assertEqual(report.successful_locks, 1)
        # Kalan 7 kullanıcı çakışma almalı
        self.assertEqual(report.failed_locks, 7)
        self.assertTrue(report.is_consistent)

        # Test sonrası temizlik: Kilidi serbest bırak
        winner = [r for r in report.results if r.success][0]
        self.lock_mgr.release_seat_lock(target_seat.id, winner.session_id)


if __name__ == "__main__":
    unittest.main()
