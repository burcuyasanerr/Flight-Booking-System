"""
Flight Ticket Purchasing System - Seat Lock Manager
Eşzamanlı koltuk seçiminde Optimistic (İyimser) ve Pessimistic (Kötümser) kilitleme yöneticisi.
"""

from datetime import datetime
from decimal import Decimal
import logging
import threading
import time
from typing import List, Optional
import psycopg2
from psycopg2 import errors

from concurrency.config import ConcurrencyConfig, DEFAULT_CONCURRENCY_CONFIG
from concurrency.db import DatabaseManager, db_manager
from concurrency.models import (
    BookingResult,
    LockResult,
    ReleaseResult,
    SeatClass,
    SeatInfo,
    SeatStatus,
)
from ticket_pdf.pnr import generate_pnr

logger = logging.getLogger(__name__)


class SeatLockManager:
    """
    Koltuk kilitleme, serbest bırakma ve çakışma yönetimini yürüten ana servis.
    """

    def __init__(
        self,
        database_manager: Optional[DatabaseManager] = None,
        config: Optional[ConcurrencyConfig] = None,
    ):
        self.db = database_manager or db_manager
        self.config = config or DEFAULT_CONCURRENCY_CONFIG

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
                price_multiplier=Decimal(str(row[4])),
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
                    price_multiplier=Decimal(str(row[4])),
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
        lock_minutes: Optional[int] = None,
    ) -> LockResult:
        """
        Optimistic Locking (İyimser Kilitleme) ile koltuğu geçici olarak tutar.

        İyileştirmeler:
        - Madde 4: Uçuş durumu (SCHEDULED/DELAYED) ve departure_time > now() kontrol edilir.
        - Madde 8: Oturum başına azami kilit sayısı kontrol edilir (max_seats_per_session).
        - Madde 9: Aynı oturum kendi geçerli kilidini yenileyebilir (uzatır).
        - Madde 10: Çakışma nedeni tespitinde süresi dolmuş kilitler 'boş' kabul edilir.
        """
        duration = lock_minutes or self.config.lock_duration_minutes

        with self.db.get_cursor(commit=True) as cursor:
            # 1. Madde 9: Koltuk zaten bu oturum tarafından kilitlenmiş ve geçerli mi? (Kilidi yenile)
            extend_query = """
            UPDATE flight_seats
            SET locked_until = now() + (%s || ' minutes')::interval,
                version = version + 1
            FROM flights f
            WHERE flight_seats.flight_id = f.id
              AND flight_seats.id = %s
              AND flight_seats.status = 'LOCKED'
              AND flight_seats.locked_by_session = %s
              AND flight_seats.locked_until > now()
              AND f.status IN ('SCHEDULED', 'DELAYED')
              AND f.departure_time > now()
            RETURNING flight_seats.version, flight_seats.locked_until;
            """
            cursor.execute(extend_query, (duration, seat_id, session_id))
            extended_row = cursor.fetchone()
            if extended_row:
                new_version, locked_until = extended_row
                return LockResult(
                    success=True,
                    seat_id=seat_id,
                    session_id=session_id,
                    previous_version=expected_version,
                    new_version=new_version,
                    locked_until=locked_until,
                    message=f"Koltuk kilidi süresi {duration} dakika daha uzatıldı.",
                )

            # 2. Madde 8: Oturum başına kilit sınırı kontrolü
            count_query = """
            SELECT COUNT(*)
            FROM flight_seats
            WHERE flight_id = (SELECT flight_id FROM flight_seats WHERE id = %s)
              AND locked_by_session = %s
              AND locked_until > now()
              AND id <> %s;
            """
            cursor.execute(count_query, (seat_id, session_id, seat_id))
            current_active_locks = cursor.fetchone()[0]
            if current_active_locks >= self.config.max_seats_per_session:
                return LockResult(
                    success=False,
                    seat_id=seat_id,
                    session_id=session_id,
                    previous_version=expected_version,
                    conflict_detected=True,
                    conflict_reason="MAX_LOCK_LIMIT_REACHED",
                    message=f"Bir oturumda en fazla {self.config.max_seats_per_session} koltuk kilitlenebilir.",
                )

            # 3. Optimistic Kilitleme (Madde 4 dahil)
            update_query = """
            UPDATE flight_seats
            SET status = 'LOCKED',
                locked_by_session = %s,
                locked_until = now() + (%s || ' minutes')::interval,
                version = version + 1
            FROM flights f
            WHERE flight_seats.flight_id = f.id
              AND flight_seats.id = %s
              AND f.status IN ('SCHEDULED', 'DELAYED')
              AND f.departure_time > now()
              AND flight_seats.version = %s
              AND (flight_seats.status = 'AVAILABLE' OR (flight_seats.status = 'LOCKED' AND flight_seats.locked_until < now()))
            RETURNING flight_seats.version, flight_seats.locked_until;
            """
            cursor.execute(update_query, (session_id, duration, seat_id, expected_version))
            row = cursor.fetchone()

            if row:
                new_version, locked_until = row
                logger.info("Koltuk %s kilitlendi (Oturum: %s, Sürüm: %s)", seat_id, session_id, new_version)
                return LockResult(
                    success=True,
                    seat_id=seat_id,
                    session_id=session_id,
                    previous_version=expected_version,
                    new_version=new_version,
                    locked_until=locked_until,
                    message=f"Koltuk {duration} dakikalığına başarıyla kilitlendi.",
                )

            # 4. Madde 10: Çakışma nedenini doğru ve güncel analiz et
            cursor.execute(
                """
                SELECT fs.status, fs.locked_by_session, fs.locked_until, fs.version,
                       f.status, f.departure_time, (fs.locked_until > now()) AS is_active
                FROM flight_seats fs
                JOIN flights f ON f.id = fs.flight_id
                WHERE fs.id = %s;
                """,
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

            c_status, c_session, c_until, c_version, f_status, f_dept, is_lock_active = current

            # Madde 4: Uçuş iptal veya geçmiş mi?
            if f_status not in ("SCHEDULED", "DELAYED") or (f_dept and f_dept < datetime.now()):
                reason = "FLIGHT_CANCELLED_OR_PAST"
                msg = "İptal edilmiş veya kalkış zamanı geçmiş uçuşlarda koltuk kilitlenemez."
            elif c_status == "BOOKED":
                reason = "ALREADY_BOOKED"
                msg = "Bu koltuk başka bir yolcu tarafından satın alınmıştır."
            elif c_status == "LOCKED" and is_lock_active and c_session != session_id:
                reason = "LOCKED_BY_ANOTHER_USER"
                msg = "Bu koltuk şu anda başka bir kullanıcı tarafından seçilmiş durumda."
            elif c_version != expected_version:
                reason = "VERSION_MISMATCH_RACE_CONDITION"
                msg = "Eşzamanlı işlem çakışması algılandı: Koltuk durumu değişti, lütfen sayfayı yenileyiniz."
            else:
                reason = "LOCK_FAILED"
                msg = "Koltuk kilitlenemedi, lütfen tekrar deneyiniz."

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
        lock_minutes: Optional[int] = None,
    ) -> LockResult:
        """
        Pessimistic Locking (Kötümser Kilitleme) ile satırı FOR UPDATE kilitleyerek tutar.

        İyileştirmeler:
        - Madde 4: Uçuş durumu ve geçmiş uçuş kontrolü eklenmiştir.
        - Madde 8: Oturum kilit sınırı kontrol edilir.
        - Madde 9: Kendi kilidini uzatma desteği eklenmiştir.
        - Madde 11: Süre kontrolü veritabanının now() fonksiyonu ile yapılır.
        """
        duration = lock_minutes or self.config.lock_duration_minutes

        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                # Satırı ve uçuşu transaction sonuna kadar kilitle
                cursor.execute(
                    """
                    SELECT fs.id, fs.flight_id, fs.status, fs.locked_by_session, fs.locked_until, fs.version,
                           f.status AS flight_status, f.departure_time,
                           (fs.locked_until > now()) AS is_active,
                           (f.status IN ('SCHEDULED', 'DELAYED') AND f.departure_time > now()) AS is_flight_valid
                    FROM flight_seats fs
                    JOIN flights f ON f.id = fs.flight_id
                    WHERE fs.id = %s
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
                        conflict_detected=True,
                        conflict_reason="SEAT_NOT_FOUND",
                        message="Koltuk bulunamadı.",
                    )

                c_id, f_id, c_status, c_session, c_until, c_version, f_status, f_dep, is_active, is_flight_valid = row

                # Madde 4: Uçuş geçerliliği
                if not is_flight_valid:
                    conn.rollback()
                    return LockResult(
                        success=False,
                        seat_id=seat_id,
                        session_id=session_id,
                        conflict_detected=True,
                        conflict_reason="FLIGHT_CANCELLED_OR_PAST",
                        message="İptal edilmiş veya geçmiş uçuşlarda koltuk kilitlenemez.",
                    )

                # Madde 9: Kendi kilidini uzatma
                if c_status == "LOCKED" and c_session == session_id and is_active:
                    cursor.execute(
                        """
                        UPDATE flight_seats
                        SET locked_until = now() + (%s || ' minutes')::interval,
                            version = version + 1
                        WHERE id = %s
                        RETURNING version, locked_until;
                        """,
                        (duration, seat_id),
                    )
                    new_version, locked_until = cursor.fetchone()
                    conn.commit()
                    return LockResult(
                        success=True,
                        seat_id=seat_id,
                        session_id=session_id,
                        previous_version=c_version,
                        new_version=new_version,
                        locked_until=locked_until,
                        message=f"Pessimistic kilit süresi {duration} dakika uzatıldı.",
                    )

                # Koltuk uygun mu?
                is_available = (c_status == "AVAILABLE") or (c_status == "LOCKED" and not is_active)
                if not is_available:
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

                # Madde 8: Oturum kilit sınırı kontrolü
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM flight_seats
                    WHERE flight_id = %s
                      AND locked_by_session = %s
                      AND locked_until > now()
                      AND id <> %s;
                    """,
                    (f_id, session_id, seat_id),
                )
                if cursor.fetchone()[0] >= self.config.max_seats_per_session:
                    conn.rollback()
                    return LockResult(
                        success=False,
                        seat_id=seat_id,
                        session_id=session_id,
                        conflict_detected=True,
                        conflict_reason="MAX_LOCK_LIMIT_REACHED",
                        message=f"Bir oturumda en fazla {self.config.max_seats_per_session} koltuk kilitlenebilir.",
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
                cursor.execute(update_query, (session_id, duration, seat_id))
                new_version, locked_until = cursor.fetchone()
                conn.commit()

                return LockResult(
                    success=True,
                    seat_id=seat_id,
                    session_id=session_id,
                    previous_version=c_version,
                    new_version=new_version,
                    locked_until=locked_until,
                    message=f"Pessimistic kilit başarıyla alındı ({duration} dk).",
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
        passenger_first_name: str,
        passenger_last_name: str,
        passenger_identity_number: str,
        passenger_email: str,
        passenger_phone: str,
        pnr_code: Optional[str] = None,
    ) -> BookingResult:
        """
        Ödeme tamamlandığında tek bir ACID transaction içinde:
        - Madde 2: Fiyat dışarıdan parametre olarak alınmaz; transaction içinde
          flights.base_price * flight_seats.price_multiplier olarak hesaplanır.
        - Madde 3: PNR içeride üretilir; PNR çakışması (UniqueViolation) durumunda
          max_retries adedince SAVEPOINT ile yeniden dener.
        - Madde 4: Uçuş iptal veya geçmiş ise işlem reddedilir.
        - Madde 13: Veritabanı hataları (FK, CHECK vb.) exception yerine BookingResult olarak döner.
        """
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    # 1. Adım: Koltuğu BOOKED yap ve fiyatı hesapla (Madde 2 ve Madde 4)
                    update_seat_query = """
                    UPDATE flight_seats
                    SET status = 'BOOKED',
                        locked_by_session = NULL,
                        locked_until = NULL,
                        version = version + 1
                    FROM flights f
                    WHERE flight_seats.flight_id = f.id
                      AND flight_seats.id = %s
                      AND flight_seats.status = 'LOCKED'
                      AND flight_seats.locked_by_session = %s
                      AND flight_seats.locked_until > now()
                      AND f.status IN ('SCHEDULED', 'DELAYED')
                      AND f.departure_time > now()
                    RETURNING flight_seats.flight_id, (f.base_price * flight_seats.price_multiplier)::numeric;
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
                            message="Koltuk kilit süresi dolmuş, başkasına geçmiş veya uçuş geçersiz. Satış engellendi.",
                        )

                    flight_id, calculated_total_price = row
                    calculated_price_dec = Decimal(str(calculated_total_price))

                    # 2. Adım: PNR Üretimi ve Çakışma Yönetimi (Madde 3)
                    insert_booking_query = """
                    INSERT INTO bookings (
                        pnr_code, user_id, flight_id, seat_id,
                        passenger_first_name, passenger_last_name, passenger_identity_number,
                        passenger_email, passenger_phone, total_price, booking_status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'CONFIRMED')
                    RETURNING id;
                    """

                    assigned_pnr = None
                    max_attempts = self.config.max_retries

                    # Dışarıdan PNR verilmişse tek sefer dene, verilmemişse otomatik üret & dene
                    candidates = [pnr_code] if pnr_code else [generate_pnr(length=6) for _ in range(max_attempts)]

                    for candidate in candidates:
                        cursor.execute("SAVEPOINT pnr_savepoint;")
                        try:
                            cursor.execute(
                                insert_booking_query,
                                (
                                    candidate,
                                    user_id,
                                    flight_id,
                                    seat_id,
                                    passenger_first_name.strip(),
                                    passenger_last_name.strip(),
                                    passenger_identity_number.strip(),
                                    passenger_email.strip(),
                                    passenger_phone.strip(),
                                    calculated_price_dec,
                                ),
                            )
                            cursor.execute("RELEASE SAVEPOINT pnr_savepoint;")
                            assigned_pnr = candidate
                            break
                        except psycopg2.IntegrityError as ie:
                            cursor.execute("ROLLBACK TO SAVEPOINT pnr_savepoint;")
                            # Sadece pnr_code benzersizlik hatasında devam et
                            if "bookings_pnr_code_key" in str(ie) or "pnr_code" in str(ie):
                                logger.warning("PNR çakışması algılandı (%s), yeni PNR deneniyor...", candidate)
                                if pnr_code:
                                    # Dışarıdan sabit verilen PNR çakışırsa döngüye devam etmeyip otomatik üret
                                    candidates.extend([generate_pnr(length=6) for _ in range(max_attempts - 1)])
                                    pnr_code = None
                                continue
                            else:
                                raise

                    if not assigned_pnr:
                        conn.rollback()
                        return BookingResult(
                            success=False,
                            seat_id=seat_id,
                            session_id=session_id,
                            error_code="PNR_GENERATION_FAILED",
                            message="Benzersiz PNR kodu üretilemedi.",
                        )

                    conn.commit()
                    logger.info("Bilet satışı onaylandı. PNR: %s, Tutar: %s TL", assigned_pnr, calculated_price_dec)

                    return BookingResult(
                        success=True,
                        seat_id=seat_id,
                        session_id=session_id,
                        pnr_code=assigned_pnr,
                        total_price=calculated_price_dec,
                        message="Bilet satışı başarıyla tamamlandı.",
                    )

                except psycopg2.Error as db_err:
                    conn.rollback()
                    logger.error("Bilet kaydı sırasında veritabanı hatası: %s", db_err)
                    err_code = getattr(db_err, "pgcode", "DB_ERROR") or "DB_ERROR"
                    return BookingResult(
                        success=False,
                        seat_id=seat_id,
                        session_id=session_id,
                        error_code=str(err_code),
                        message=f"Veritabanı kısıtlama hatası: {db_err.pgerror or str(db_err)}",
                    )

    def cleanup_expired_locks(self) -> int:
        """
        Süresi dolmuş tüm kilitleri topluca serbest bırakır.
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


class BackgroundLockCleaner:
    """
    Madde 12: Süresi dolan kilitleri arka planda periyodik olarak temizleyen zamanlayıcı.
    """

    def __init__(self, lock_manager: SeatLockManager, interval_seconds: Optional[int] = None):
        self.lock_mgr = lock_manager
        self.interval = interval_seconds or lock_manager.config.cleanup_interval_seconds
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Temizleme iş parçacığını başlatır."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="LockCleanerThread")
        self._thread.start()
        logger.info("Arka plan kilit temizleyici başlatıldı (Aralık: %d sn).", self.interval)

    def stop(self):
        """Temizleme iş parçacığını durdurur."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        logger.info("Arka plan kilit temizleyici durduruldu.")

    def _run(self):
        while not self._stop_event.is_set():
            try:
                self.lock_mgr.cleanup_expired_locks()
            except Exception as e:
                logger.warning("Arka plan kilit temizliğinde hata: %s", e)
            self._stop_event.wait(self.interval)
