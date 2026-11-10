"""
Flight Ticket Purchasing System - Seat Lock Manager
Eşzamanlı koltuk seçiminde Optimistic (İyimser) ve Pessimistic (Kötümser) kilitleme yöneticisi.
"""

from datetime import datetime
import logging
from typing import List, Optional
import psycopg2

try:
    from .db import DatabaseManager, db_manager
    from .models import (
        BookingResult,
        LockResult,
        ReleaseResult,
        SeatClass,
        SeatInfo,
        SeatStatus,
    )
except ImportError:
    from db import DatabaseManager, db_manager
    from models import (
        BookingResult,
        LockResult,
        ReleaseResult,
        SeatClass,
        SeatInfo,
        SeatStatus,
    )

logger = logging.getLogger(__name__)


class SeatLockManager:
    """
    Koltuk kilitleme, serbest bırakma ve çakışma yönetimini yürüten ana servis.
    """

    def __init__(self, database_manager: Optional[DatabaseManager] = None):
        self.db = database_manager or db_manager

    def get_seat(self, seat_id: int) -> Optional[SeatInfo]:
        """
        Belirtilen koltuğun güncel durumunu veritabanından sorgular.
        Süresi dolmuş kilitleri etkin durumda AVAILABLE olarak değerlendirir.
        """
        query = """
        SELECT id, flight_id, seat_number, seat_class, price_multiplier, status,
               CASE WHEN status = 'LOCKED' AND locked_until < now()
                    THEN 'AVAILABLE' ELSE status END AS effective_status,
               locked_by_session, locked_until, version
        FROM flight_seats
        WHERE id = %s;
        """
        with self.db.get_cursor(commit=False) as cursor:
            cursor.execute(query, (seat_id,))
            row = cursor.fetchone()
            if not row:
                return None

            return SeatInfo(
                id=row[0],
                flight_id=row[1],
                seat_number=row[2],
                seat_class=SeatClass(row[3]),
                price_multiplier=float(row[4]),
                status=SeatStatus(row[5]),
                effective_status=SeatStatus(row[6]),
                locked_by_session=row[7],
                locked_until=row[8],
                version=row[9],
            )

    def get_flight_seats(self, flight_id: int) -> List[SeatInfo]:
        """
        Bir uçuşun tüm koltuklarını güncel kilit durumlarıyla listeler.
        """
        query = """
        SELECT id, flight_id, seat_number, seat_class, price_multiplier, status,
               CASE WHEN status = 'LOCKED' AND locked_until < now()
                    THEN 'AVAILABLE' ELSE status END AS effective_status,
               locked_by_session, locked_until, version
        FROM flight_seats
        WHERE flight_id = %s
        ORDER BY length(seat_number), seat_number;
        """
        with self.db.get_cursor(commit=False) as cursor:
            cursor.execute(query, (flight_id,))
            rows = cursor.fetchall()

            return [
                SeatInfo(
                    id=row[0],
                    flight_id=row[1],
                    seat_number=row[2],
                    seat_class=SeatClass(row[3]),
                    price_multiplier=float(row[4]),
                    status=SeatStatus(row[5]),
                    effective_status=SeatStatus(row[6]),
                    locked_by_session=row[7],
                    locked_until=row[8],
                    version=row[9],
                )
                for row in rows
            ]

    def lock_seat_optimistic(
        self,
        seat_id: int,
        session_id: str,
        expected_version: int,
        lock_minutes: int = 10,
    ) -> LockResult:
        """
        Optimistic Locking (İyimser Kilitleme) ile koltuğu geçici olarak tutar.

        İşleyiş:
        - Koltuk AVAILABLE ise veya önceki kilidinin süresi dolmuşsa kilitlenir.
        - `version = expected_version` doğrulanır; aynı anda başka bir işlem
          koltukta değişiklik yapmışsa sürüm artacağı için güncelleme 0 satır etkiler.
        - Kilit süresi SQL tarafında `now() + INTERVAL 'X minutes'` ile hesaplanır
          (sunucu ile DB arasındaki zaman farklarından etkilenmez).
        """
        update_query = """
        UPDATE flight_seats
        SET status = 'LOCKED',
            locked_by_session = %s,
            locked_until = now() + (%s || ' minutes')::interval,
            version = version + 1
        WHERE id = %s
          AND version = %s
          AND (status = 'AVAILABLE' OR (status = 'LOCKED' AND locked_until < now()))
        RETURNING version, locked_until;
        """

        with self.db.get_cursor(commit=True) as cursor:
            cursor.execute(
                update_query,
                (session_id, lock_minutes, seat_id, expected_version),
            )
            row = cursor.fetchone()

            if row:
                new_version, locked_until = row
                logger.info(
                    "Koltuk %s başarıyla kilitlendi. (Oturum: %s, Yeni Sürüm: %s)",
                    seat_id,
                    session_id,
                    new_version,
                )
                return LockResult(
                    success=True,
                    seat_id=seat_id,
                    session_id=session_id,
                    previous_version=expected_version,
                    new_version=new_version,
                    locked_until=locked_until,
                    message=f"Koltuk {lock_minutes} dakikalığına başarıyla kilitlendi.",
                )

            # Başarısız olduysa çakışmanın kesin nedenini analiz et
            cursor.execute(
                "SELECT status, locked_by_session, locked_until, version FROM flight_seats WHERE id = %s;",
                (seat_id,),
            )
            current = cursor.fetchone()

            if not current:
                return LockResult(
                    success=False,
                    seat_id=seat_id,
                    session_id=session_id,
                    conflict_detected=True,
                    conflict_reason="SEAT_NOT_FOUND",
                    message="Belirtilen koltuk bulunamadı.",
                )

            c_status, c_session, c_until, c_version = current

            if c_status == "BOOKED":
                reason = "ALREADY_BOOKED"
                msg = "Bu koltuk başka bir yolcu tarafından satın alınmıştır."
            elif c_status == "LOCKED" and c_session != session_id:
                reason = "LOCKED_BY_ANOTHER_USER"
                msg = "Bu koltuk şu anda başka bir kullanıcı tarafından seçilmiş durumda."
            elif c_version != expected_version:
                reason = "VERSION_MISMATCH_RACE_CONDITION"
                msg = "Eşzamanlı işlem çakışması algılandı: Koltuk durumu değişti, lütfen sayfayı yenileyiniz."
            else:
                reason = "LOCK_FAILED"
                msg = "Koltuk kilitlenemedi, lütfen tekrar deneyiniz."

            logger.warning(
                "Koltuk %s kilitlenemedi! Neden: %s (Oturum: %s)",
                seat_id,
                reason,
                session_id,
            )

            return LockResult(
                success=False,
                seat_id=seat_id,
                session_id=session_id,
                previous_version=expected_version,
                conflict_detected=True,
                conflict_reason=reason,
                message=msg,
            )

    def lock_seat_pessimistic(
        self,
        seat_id: int,
        session_id: str,
        lock_minutes: int = 10,
    ) -> LockResult:
        """
        Pessimistic Locking (Kötümser Kilitleme) ile satırı FOR UPDATE kilitleyerek tutar.
        Kısa süreli kritik transaction'lar veya yüksek çakışmalı uçuşlar için alternatif stratejidir.
        """
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                # Satırı transaction sonuna kadar kilitle
                cursor.execute(
                    """
                    SELECT id, status, locked_by_session, locked_until, version
                    FROM flight_seats
                    WHERE id = %s
                    FOR UPDATE;
                    """,
                    (seat_id,),
                )
                row = cursor.fetchone()
                if not row:
                    conn.rollback()
                    return LockResult(
                        success=False,
                        seat_id=seat_id,
                        session_id=session_id,
                        message="Koltuk bulunamadı.",
                    )

                c_id, c_status, c_session, c_until, c_version = row

                # Koltuk uygun mu kontrolü
                is_available = (c_status == "AVAILABLE")
                is_expired_lock = (c_status == "LOCKED" and c_until and c_until < datetime.now(c_until.tzinfo))

                if not (is_available or is_expired_lock):
                    conn.rollback()
                    reason = "ALREADY_BOOKED" if c_status == "BOOKED" else "LOCKED_BY_ANOTHER_USER"
                    return LockResult(
                        success=False,
                        seat_id=seat_id,
                        session_id=session_id,
                        conflict_detected=True,
                        conflict_reason=reason,
                        message="Koltuk seçilemez durumda.",
                    )

                # Kilitle
                update_query = """
                UPDATE flight_seats
                SET status = 'LOCKED',
                    locked_by_session = %s,
                    locked_until = now() + (%s || ' minutes')::interval,
                    version = version + 1
                WHERE id = %s
                RETURNING version, locked_until;
                """
                cursor.execute(update_query, (session_id, lock_minutes, seat_id))
                new_version, locked_until = cursor.fetchone()
                conn.commit()

                return LockResult(
                    success=True,
                    seat_id=seat_id,
                    session_id=session_id,
                    previous_version=c_version,
                    new_version=new_version,
                    locked_until=locked_until,
                    message=f"Pessimistic kilit başarıyla alındı ({lock_minutes} dk).",
                )

    def release_seat_lock(self, seat_id: int, session_id: str) -> ReleaseResult:
        """
        Kullanıcı seçimden vazgeçtiğinde veya sayfadan ayrıldığında kilidi serbest bırakır.
        Sadece kilidi koyan oturum serbest bırakabilir.
        """
        query = """
        UPDATE flight_seats
        SET status = 'AVAILABLE',
            locked_by_session = NULL,
            locked_until = NULL,
            version = version + 1
        WHERE id = %s AND locked_by_session = %s
        RETURNING id;
        """
        with self.db.get_cursor(commit=True) as cursor:
            cursor.execute(query, (seat_id, session_id))
            row = cursor.fetchone()
            if row:
                return ReleaseResult(
                    success=True,
                    seat_id=seat_id,
                    session_id=session_id,
                    message="Koltuk kilidi başarıyla kaldırıldı.",
                )
            return ReleaseResult(
                success=False,
                seat_id=seat_id,
                session_id=session_id,
                message="Kilit kaldırılamadı. Koltuk bu oturuma ait değil veya zaten serbest.",
            )

    def confirm_seat_booking(
        self,
        seat_id: int,
        session_id: str,
        user_id: int,
        pnr_code: str,
        passenger_first_name: str,
        passenger_last_name: str,
        passenger_identity_number: str,
        passenger_email: str,
        passenger_phone: str,
        total_price: float,
    ) -> BookingResult:
        """
        Ödeme tamamlandığında tek bir ACID transaction içinde:
        1. Koltuğun kilidinin geçerli olduğunu ve bu oturuma ait olduğunu doğrular.
        2. Koltuğu BOOKED durumuna geçirir ve kilidi temizler (`version` artırılır).
        3. `bookings` tablosuna bilet kaydını ekler.
        Eğer koltuk kilidi zaman aşımına uğramışsa veya başkası almışsa
        işlem ROLLBACK edilir ve satış engellenir.
        """
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                # 1. Adım: Koltuğu BOOKED yap
                update_seat_query = """
                UPDATE flight_seats
                SET status = 'BOOKED',
                    locked_by_session = NULL,
                    locked_until = NULL,
                    version = version + 1
                WHERE id = %s
                  AND status = 'LOCKED'
                  AND locked_by_session = %s
                  AND locked_until > now()
                RETURNING flight_id;
                """
                cursor.execute(update_seat_query, (seat_id, session_id))
                row = cursor.fetchone()

                if not row:
                    conn.rollback()
                    return BookingResult(
                        success=False,
                        seat_id=seat_id,
                        session_id=session_id,
                        error_code="LOCK_EXPIRED_OR_INVALID",
                        message="Koltuk kilit süresi dolmuş veya kilit geçersiz. Satış iptal edildi.",
                    )

                flight_id = row[0]

                # 2. Adım: Bilet kaydı oluştur
                insert_booking_query = """
                INSERT INTO bookings (
                    pnr_code, user_id, flight_id, seat_id,
                    passenger_first_name, passenger_last_name, passenger_identity_number,
                    passenger_email, passenger_phone, total_price, booking_status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'CONFIRMED')
                RETURNING id;
                """
                cursor.execute(
                    insert_booking_query,
                    (
                        pnr_code,
                        user_id,
                        flight_id,
                        seat_id,
                        passenger_first_name,
                        passenger_last_name,
                        passenger_identity_number,
                        passenger_email,
                        passenger_phone,
                        total_price,
                    ),
                )
                conn.commit()

                logger.info(
                    "Bilet satışı onaylandı! PNR: %s, Koltuk ID: %s, Yolcu: %s %s",
                    pnr_code,
                    seat_id,
                    passenger_first_name,
                    passenger_last_name,
                )

                return BookingResult(
                    success=True,
                    seat_id=seat_id,
                    session_id=session_id,
                    pnr_code=pnr_code,
                    message="Bilet satışı başarıyla tamamlandı.",
                )

    def cleanup_expired_locks(self) -> int:
        """
        Süresi dolmuş tüm kilitleri topluca serbest bırakır.
        Arka plan zamanlayıcıları (cron/celery) tarafından periyodik çağrılabilir.
        """
        query = """
        UPDATE flight_seats
        SET status = 'AVAILABLE',
            locked_by_session = NULL,
            locked_until = NULL,
            version = version + 1
        WHERE status = 'LOCKED' AND locked_until < now();
        """
        with self.db.get_cursor(commit=True) as cursor:
            cursor.execute(query)
            affected = cursor.rowcount
            if affected > 0:
                logger.info("%d adet süresi dolmuş koltuk kilidi temizlendi.", affected)
            return affected
