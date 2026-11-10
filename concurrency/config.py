"""
Flight Ticket Purchasing System - Concurrency Configuration
Veritabanı bağlantı parametreleri ve kilit zaman aşımı yapılandırması.
"""

import os
from dataclasses import dataclass


@dataclass
class DatabaseConfig:
    """Veritabanı bağlantı ayarları"""
    host: str = os.getenv("DB_HOST", "localhost")
    port: int = int(os.getenv("DB_PORT", "5432"))
    dbname: str = os.getenv("DB_NAME", "flight_booking")
    user: str = os.getenv("DB_USER", "postgres")
    password: str = os.getenv("DB_PASSWORD", "postgres")
    min_conn: int = int(os.getenv("DB_MIN_CONN", "2"))
    max_conn: int = int(os.getenv("DB_MAX_CONN", "20"))


@dataclass
class ConcurrencyConfig:
    """Eşzamanlılık ve kilit zaman aşımı ayarları"""
    lock_duration_minutes: int = int(os.getenv("LOCK_DURATION_MINUTES", "10"))
    cleanup_interval_seconds: int = int(os.getenv("CLEANUP_INTERVAL_SECONDS", "60"))
    max_retries: int = int(os.getenv("CONCURRENCY_MAX_RETRIES", "3"))


DEFAULT_DB_CONFIG = DatabaseConfig()
DEFAULT_CONCURRENCY_CONFIG = ConcurrencyConfig()
