"""
Flight Ticket Purchasing System - Concurrency Modülü
Aktif koltuk seçiminde eşzamanlılık (concurrency) çakışma yönetimi ve kilitleme araçları.
"""

from concurrency.config import ConcurrencyConfig, DatabaseConfig
from concurrency.db import DatabaseManager, db_manager
from concurrency.lock_manager import SeatLockManager
from concurrency.models import (
    BookingResult,
    LockResult,
    ReleaseResult,
    SeatClass,
    SeatInfo,
    SeatStatus,
)
from concurrency.simulator import ConcurrencySimulator, SimulationReport

__all__ = [
    "DatabaseConfig",
    "ConcurrencyConfig",
    "DatabaseManager",
    "db_manager",
    "SeatStatus",
    "SeatClass",
    "SeatInfo",
    "LockResult",
    "ReleaseResult",
    "BookingResult",
    "SeatLockManager",
    "ConcurrencySimulator",
    "SimulationReport",
]
