"""
Flight Ticket Purchasing System - Concurrency Configuration
Veritabanı bağlantı parametreleri ve kilit zaman aşımı yapılandırması.
.env dosyasını otomatik olarak yükler.
"""

from dataclasses import dataclass
import os
from pathlib import Path

# .env dosyasını yükle (varsa)
try:
    from dotenv import load_dotenv
    # Proje kökü veya concurrency dizinindeki .env
    env_paths = [
        Path(__file__).resolve().parent / ".env",
        Path(__file__).resolve().parent.parent / ".env",
    ]
    for p in env_paths:
        if p.exists():
            load_dotenv(p)
            break
    else:
        load_dotenv()
except ImportError:
    pass


@dataclass
class DatabaseConfig:
    """Veritabanı bağlantı ayarları"""
    host: str = os.getenv("DB_HOST", "localhost")
    port: int = int(os.getenv("DB_PORT", "5432"))
    dbname: str = os.getenv("DB_NAME", "flight_booking")
    user: str = os.getenv("DB_USER", "postgres")
    password: str = os.getenv("DB_PASSWORD", "postgres")
    min_conn: int = int(os.getenv("DB_MIN_CONN", "5"))   # Madde 16: Bağlantı sarsıntısını önlemek için min 5
    max_conn: int = int(os.getenv("DB_MAX_CONN", "20"))


@dataclass
class ConcurrencyConfig:
    """Eşzamanlılık, kilit ve çakışma ayarları"""
    lock_duration_minutes: int = int(os.getenv("LOCK_DURATION_MINUTES", "10"))
    cleanup_interval_seconds: int = int(os.getenv("CLEANUP_INTERVAL_SECONDS", "60"))
    max_retries: int = int(os.getenv("CONCURRENCY_MAX_RETRIES", "5"))  # PNR çakışması tekrar deneme
    max_seats_per_session: int = int(os.getenv("MAX_SEATS_PER_SESSION", "9"))  # Madde 8: Oturum başına kilit sınırı


DEFAULT_DB_CONFIG = DatabaseConfig()
DEFAULT_CONCURRENCY_CONFIG = ConcurrencyConfig()
