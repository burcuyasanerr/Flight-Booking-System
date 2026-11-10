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

try:
    from .lock_manager import SeatLockManager
    from .models import LockResult, SeatInfo
except ImportError:
    from lock_manager import SeatLockManager
    from models import LockResult, SeatInfo

logger = logging.getLogger(__name__)


@dataclass
class SimulationReport:
    """Eşzamanlılık simülasyonu özet raporu"""
    seat_id: int
    initial_version: int
    final_version: int
    total_attempts: int
    successful_locks: int
    failed_locks: int
    conflicts_detected: int
    duration_ms: float
    results: List[LockResult] = field(default_factory=list)

    @property
    def is_consistent(self) -> bool:
        """
        Kritik test: Aynı anda yarışan N kullanıcıdan
        tam olarak 1 tanesi başarılı olmalı ve kalan hepsi çakışma almalıdır.
        """
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

        İşleyiş:
        1. Koltuğun başlangıç sürümünü okur.
        2. `threading.Barrier` kullanarak tüm iş parçacıklarının hazır olmasını bekler.
        3. Tüm iş parçacıklarını tam aynı milisaniyede serbest bırakarak yarış koşulu oluşturur.
        4. Sonuçları toplayıp raporlar.
        """
        seat = self.lock_mgr.get_seat(seat_id)
        if not seat:
            raise ValueError(f"Koltuk bulunamadı: {seat_id}")

        initial_version = seat.version
        barrier = threading.Barrier(concurrent_users)
        results: List[LockResult] = []

        def worker_task(user_idx: int) -> LockResult:
            session_id = f"sim_user_{user_idx}_{int(time.time()*1000)}"
            # Tüm iş parçacıklarının bariyerde toplanmasını bekle
            barrier.wait()

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

        start_time = time.perf_counter()

        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            future_to_user = {
                executor.submit(worker_task, i + 1): i + 1
                for i in range(concurrent_users)
            }
            for future in as_completed(future_to_user):
                try:
                    res = future.result()
                    results.append(res)
                except Exception as ex:
                    logger.error("Simülasyon çalışanı hata verdi: %s", ex)

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
            total_attempts=len(results),
            successful_locks=successes,
            failed_locks=failures,
            conflicts_detected=conflicts,
            duration_ms=duration_ms,
            results=results,
        )
