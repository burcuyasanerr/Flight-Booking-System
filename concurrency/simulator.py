"""
Flight Ticket Purchasing System - Concurrency Stress Test & Simulator
Aynı anda birden fazla kullanıcının aynı koltuğu seçmeye çalıştığı yarış koşullarını
(race condition) simüle eder ve Optimistic Locking mekanizmasını doğrular.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
import logging
import threading
import time
from typing import List, Optional

from concurrency.lock_manager import SeatLockManager
from concurrency.models import LockResult, SeatInfo

logger = logging.getLogger(__name__)


@dataclass
class SimulationReport:
    """Eşzamanlılık simülasyonu özet raporu"""
    seat_id: int
    initial_version: int
    final_version: int
    total_attempts: int        # İstenen toplam kullanıcı sayısı
    successful_locks: int
    failed_locks: int
    conflicts_detected: int
    errors: int = 0            # Madde 6: Havuz veya bağlantı hataları sayacı
    duration_ms: float = 0.0
    results: List[LockResult] = field(default_factory=list)

    @property
    def is_consistent(self) -> bool:
        """
        Madde 6:
        - Hiçbir işçi hata (error) almamalıdır.
        - Tam 1 istek başarılı olmalıdır.
        - Kalan (total_attempts - 1) istek kontrollü şekilde çakışma almalıdır.
        """
        if self.errors > 0:
            return False
        return self.successful_locks == 1 and self.failed_locks == (self.total_attempts - 1)


class ConcurrencySimulator:
    """
    Eşzamanlı koltuk kilitleme simülatörü.
    """

    def __init__(self, lock_manager: Optional[SeatLockManager] = None):
        self.lock_mgr = lock_manager or SeatLockManager()

    def run_concurrent_lock_test(
        self,
        seat_id: int,
        concurrent_users: int = 10,
        use_pessimistic: bool = False,
    ) -> SimulationReport:
        """
        Belirtilen koltuk için aynı anda `concurrent_users` adet kullanıcının
        kilitleme isteği gönderdiği senaryoyu simüle eder.
        """
        seat = self.lock_mgr.get_seat(seat_id)
        if not seat:
            raise ValueError(f"Koltuk bulunamadı: {seat_id}")

        # Madde 6: Bağlantı havuzu kapasitesi kontrolü ve uyarısı
        max_conn = self.lock_mgr.db.config.max_conn
        if concurrent_users > max_conn:
            logger.warning(
                "UYARI: Simülasyon kullanıcı sayısı (%d), veritabanı maksimum havuz sınırını (%d) aşıyor! PoolError riski var.",
                concurrent_users,
                max_conn,
            )

        initial_version = seat.version
        barrier = threading.Barrier(concurrent_users)
        results: List[LockResult] = []
        error_count = 0
        error_lock = threading.Lock()

        def worker_task(user_idx: int) -> Optional[LockResult]:
            nonlocal error_count
            session_id = f"sim_user_{user_idx}_{int(time.time()*1000)}"
            try:
                # Tüm iş parçacıklarının bariyerde toplanmasını bekle
                barrier.wait(timeout=10)

                # Tam aynı anda kilitleme isteği gönder
                if use_pessimistic:
                    return self.lock_mgr.lock_seat_pessimistic(
                        seat_id=seat_id,
                        session_id=session_id,
                        lock_minutes=5,
                    )
                else:
                    return self.lock_mgr.lock_seat_optimistic(
                        seat_id=seat_id,
                        session_id=session_id,
                        expected_version=initial_version,
                        lock_minutes=5,
                    )
            except Exception as ex:
                with error_lock:
                    error_count += 1
                logger.error("Simülasyon çalışanı (#%d) beklenmeyen hata aldı: %s", user_idx, ex)
                return None

        start_time = time.perf_counter()

        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            future_to_user = {
                executor.submit(worker_task, i + 1): i + 1
                for i in range(concurrent_users)
            }
            for future in as_completed(future_to_user):
                res = future.result()
                if res is not None:
                    results.append(res)

        duration_ms = (time.perf_counter() - start_time) * 1000.0

        # Nihai koltuk durumunu oku
        updated_seat = self.lock_mgr.get_seat(seat_id)
        final_version = updated_seat.version if updated_seat else initial_version

        successes = sum(1 for r in results if r.success)
        failures = sum(1 for r in results if not r.success)
        conflicts = sum(1 for r in results if r.conflict_detected)

        return SimulationReport(
            seat_id=seat_id,
            initial_version=initial_version,
            final_version=final_version,
            total_attempts=concurrent_users,  # Madde 6: Gerçekte hedeflenen toplam kullanıcı
            successful_locks=successes,
            failed_locks=failures,
            conflicts_detected=conflicts,
            errors=error_count,               # Madde 6: Hata sayısı
            duration_ms=duration_ms,
            results=results,
        )
