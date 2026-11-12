"""
Flight Ticket Purchasing System - Concurrency Unit & Integration Tests
Madde 26: addCleanup kullanımı, confirm_seat_booking (başarı, süre aşımı, PNR çakışması),
pessimistic mod, cleanup_expired_locks ve oturum kilit sınırı testleri.
"""

from datetime import datetime, timedelta
from decimal import Decimal
import unittest

from concurrency.config import ConcurrencyConfig
from concurrency.db import db_manager
from concurrency.lock_manager import SeatLockManager
from concurrency.models import (
    BookingResult,
    LockResult,
    ReleaseResult,
    SeatClass,
    SeatInfo,
    SeatStatus,
)
from concurrency.simulator import ConcurrencySimulator


class TestConcurrencyModels(unittest.TestCase):
    """Veri modelleri testleri"""

    def test_seat_info_creation(self):
        seat = SeatInfo(
            id=1,
            flight_id=1,
            seat_number="1A",
            seat_class=SeatClass.BUSINESS,
            price_multiplier=Decimal("1.50"),
            status=SeatStatus.AVAILABLE,
            effective_status=SeatStatus.AVAILABLE,
            version=1,
        )
        self.assertEqual(seat.seat_number, "1A")
        self.assertEqual(seat.status, SeatStatus.AVAILABLE)
        self.assertEqual(seat.price_multiplier, Decimal("1.50"))

    def test_lock_result_conflict_structure(self):
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


class TestLiveConcurrency(unittest.TestCase):
    """Canlı PostgreSQL veritabanı üzerindeki kapsamlı eşzamanlılık testleri"""

    @classmethod
    def setUpClass(cls):
        cls.is_db_connected = db_manager.check_connection()
        cls.custom_config = ConcurrencyConfig(
            lock_duration_minutes=5,
            max_retries=3,
            max_seats_per_session=3,  # Test için düşük sınır
        )
        cls.lock_mgr = SeatLockManager(db_manager, config=cls.custom_config)

    def setUp(self):
        if not self.is_db_connected:
            self.skipTest("PostgreSQL veritabanı bağlantısı aktif değil.")

    def _reset_seat(self, seat_id: int):
        """Madde 26: Koltuğu test öncesi veya sonrası temizleyen güvenli yardımcı"""
        with self.lock_mgr.db.get_cursor(commit=True) as cursor:
            cursor.execute(
                """
                UPDATE flight_seats
                SET status = 'AVAILABLE',
                    locked_by_session = NULL,
                    locked_until = NULL,
                    version = 1
                WHERE id = %s;
                """,
                (seat_id,),
            )

    def _delete_test_booking(self, pnr_code: str):
        """Test amaçlı oluşturulan bilet kaydını siler"""
        with self.lock_mgr.db.get_cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM bookings WHERE pnr_code = %s;", (pnr_code,))

    def test_get_flight_seats(self):
        seats = self.lock_mgr.get_flight_seats(flight_id=1)
        self.assertGreater(len(seats), 0)
        self.assertIn(seats[0].status, [SeatStatus.AVAILABLE, SeatStatus.LOCKED, SeatStatus.BOOKED])

    def test_optimistic_lock_and_renewal_lifecycle(self):
        """Madde 9 & 26: addCleanup ile güvenli kilit ve aynı oturumun kilidi uzatması"""
        target_seat_id = 15
        self._reset_seat(target_seat_id)
        self.addCleanup(self._reset_seat, target_seat_id)

        session_a = "session_lifecycle_a"
        session_b = "session_lifecycle_b"

        # 1. Oturum A kilitler
        res_a = self.lock_mgr.lock_seat_optimistic(target_seat_id, session_a, expected_version=1, lock_minutes=5)
        self.assertTrue(res_a.success)

        # 2. Madde 9: Oturum A aynı koltuğu tekrar seçer -> Kilit uzatılmalı
        res_renew = self.lock_mgr.lock_seat_optimistic(target_seat_id, session_a, expected_version=res_a.new_version, lock_minutes=8)
        self.assertTrue(res_renew.success)
        self.assertIn("uzatıldı", res_renew.message)

        # 3. Oturum B kilitlemeye çalışır -> Reddedilmeli
        res_b = self.lock_mgr.lock_seat_optimistic(target_seat_id, session_b, expected_version=res_renew.new_version, lock_minutes=5)
        self.assertFalse(res_b.success)
        self.assertEqual(res_b.conflict_reason, "LOCKED_BY_ANOTHER_USER")

        # 4. Serbest bırak
        rel = self.lock_mgr.release_seat_lock(target_seat_id, session_a)
        self.assertTrue(rel.success)

    def test_pessimistic_lock_mode(self):
        """Madde 11 & 26: Pessimistic kilitleme ve FOR UPDATE testi"""
        target_seat_id = 16
        self._reset_seat(target_seat_id)
        self.addCleanup(self._reset_seat, target_seat_id)

        session_p = "session_pessimistic_p"
        res = self.lock_mgr.lock_seat_pessimistic(target_seat_id, session_p, lock_minutes=4)
        self.assertTrue(res.success)
        self.assertIsNotNone(res.locked_until)

        # Başkası kilitleyemez
        res_conflict = self.lock_mgr.lock_seat_pessimistic(target_seat_id, "other_session")
        self.assertFalse(res_conflict.success)

        # Temizlik
        self.lock_mgr.release_seat_lock(target_seat_id, session_p)

    def test_cleanup_expired_locks(self):
        """Madde 12 & 26: Süresi geçmiş kilitlerin temizlenmesi testi"""
        target_seat_id = 17
        self._reset_seat(target_seat_id)
        self.addCleanup(self._reset_seat, target_seat_id)

        # Veritabanında elle süresi geçmiş kilit oluştur (1 saat önce)
        with self.lock_mgr.db.get_cursor(commit=True) as cursor:
            cursor.execute(
                """
                UPDATE flight_seats
                SET status = 'LOCKED',
                    locked_by_session = 'expired_session',
                    locked_until = now() - INTERVAL '1 hour',
                    version = 2
                WHERE id = %s;
                """,
                (target_seat_id,),
            )

        # Temizleyiciyi çağır
        cleaned_count = self.lock_mgr.cleanup_expired_locks()
        self.assertGreaterEqual(cleaned_count, 1)

        # Koltuk tekrar AVAILABLE olmalı
        seat = self.lock_mgr.get_seat(target_seat_id)
        self.assertEqual(seat.status, SeatStatus.AVAILABLE)

    def test_confirm_seat_booking_lifecycle_and_price_calculation(self):
        """Madde 2, 3, 26: Satın alma, SQL tabanlı fiyat hesabı ve PNR üretimi"""
        target_seat_id = 18
        self._reset_seat(target_seat_id)
        self.addCleanup(self._reset_seat, target_seat_id)

        session_book = "session_buyer_18"

        # 1. Önce koltuğu kilitle
        lock_res = self.lock_mgr.lock_seat_optimistic(target_seat_id, session_book, expected_version=1)
        self.assertTrue(lock_res.success)

        # 2. Satın al (fiyat dışarıdan gönderilmiyor, SQL hesaplıyor)
        book_res = self.lock_mgr.confirm_seat_booking(
            seat_id=target_seat_id,
            session_id=session_book,
            user_id=1,
            passenger_first_name="Can",
            passenger_last_name="Yılmaz",
            passenger_identity_number="98765432101",
            passenger_email="can@example.com",
            passenger_phone="+905559998877",
        )
        self.assertTrue(book_res.success)
        self.assertIsNotNone(book_res.pnr_code)
        self.assertGreater(book_res.total_price, 0)

        # Oluşan biletin silinmesini cleanup'a ekle
        self.addCleanup(self._delete_test_booking, book_res.pnr_code)

        # Koltuk BOOKED olmalı
        seat = self.lock_mgr.get_seat(target_seat_id)
        self.assertEqual(seat.status, SeatStatus.BOOKED)

    def test_confirm_seat_booking_fails_on_expired_or_invalid_lock(self):
        """Madde 26: Kilitli olmayan koltukta satın alma engellenmeli"""
        target_seat_id = 19
        self._reset_seat(target_seat_id)
        self.addCleanup(self._reset_seat, target_seat_id)

        # Kilitlenmemiş koltuğu satın almaya çalış
        book_res = self.lock_mgr.confirm_seat_booking(
            seat_id=target_seat_id,
            session_id="unauthorized_session",
            user_id=1,
            passenger_first_name="Test",
            passenger_last_name="User",
            passenger_identity_number="12345678901",
            passenger_email="test@example.com",
            passenger_phone="+905550001122",
        )
        self.assertFalse(book_res.success)
        self.assertEqual(book_res.error_code, "LOCK_EXPIRED_OR_INVALID")

    def test_max_seats_per_session_limit(self):
        """Madde 8 & 26: Oturum başına azami kilit sınırı testi"""
        seats = [20, 21, 22, 23]
        for sid in seats:
            self._reset_seat(sid)
            self.addCleanup(self._reset_seat, sid)

        session_spammer = "session_greedy_spammer"
        # max_seats_per_session=3 olarak ayarlanmıştı
        self.assertTrue(self.lock_mgr.lock_seat_optimistic(20, session_spammer, expected_version=1).success)
        self.assertTrue(self.lock_mgr.lock_seat_optimistic(21, session_spammer, expected_version=1).success)
        self.assertTrue(self.lock_mgr.lock_seat_optimistic(22, session_spammer, expected_version=1).success)

        # 4. kilit reddedilmeli
        res_blocked = self.lock_mgr.lock_seat_optimistic(23, session_spammer, expected_version=1)
        self.assertFalse(res_blocked.success)
        self.assertEqual(res_blocked.conflict_reason, "MAX_LOCK_LIMIT_REACHED")

    def test_concurrent_simulation_race_condition(self):
        """Madde 6 & 26: Çoklu iş parçacığı yarış koşulu testi"""
        target_seat_id = 24
        self._reset_seat(target_seat_id)
        self.addCleanup(self._reset_seat, target_seat_id)

        sim = ConcurrencySimulator(self.lock_mgr)
        report = sim.run_concurrent_lock_test(
            seat_id=target_seat_id,
            concurrent_users=6,
            use_pessimistic=False,
        )

        self.assertEqual(report.successful_locks, 1)
        self.assertEqual(report.failed_locks, 5)
        self.assertEqual(report.errors, 0)
        self.assertTrue(report.is_consistent)


if __name__ == "__main__":
    unittest.main()
