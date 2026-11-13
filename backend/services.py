"""
Paylaşılan servis nesneleri.

Backend kendi bağlantı havuzunu açmaz; `concurrency` modülündeki havuzu
(`db_manager`) kullanır. Böylece koltuk kilitleme, PDF bilet ve API sorguları
aynı havuzdan bağlantı alır.
"""

from concurrency.db import db_manager
from concurrency.lock_manager import SeatLockManager

lock_manager = SeatLockManager(database_manager=db_manager)

__all__ = ["db_manager", "lock_manager"]
