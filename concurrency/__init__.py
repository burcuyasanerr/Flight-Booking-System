"""
Flight Ticket Purchasing System - Concurrency Modülü
Aktif koltuk seçiminde eşzamanlılık (concurrency) çakışma yönetimi ve kilitleme araçları.
"""

try:
    from .config import ConcurrencyConfig, DatabaseConfig
    from .db import DatabaseManager, db_manager
    from .lock_manager import SeatLockManager
    from .models import (
        BookingResult,
        LockResult,
        ReleaseResult,
        SeatClass,
        SeatInfo,
        SeatStatus,
    )
    from .simulator import ConcurrencySimulator, SimulationReport
except ImportError:
    from config import ConcurrencyConfig, DatabaseConfig
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
    from simulator import ConcurrencySimulator, SimulationReport

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
