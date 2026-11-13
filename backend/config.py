"""
Backend ayarları.

Veritabanı bilgileri (DB_HOST, DB_NAME, DB_USER, DB_PASSWORD ...) proje
kökündeki `.env` dosyasından `concurrency.config` tarafından okunur; burada
yalnızca backend'e özgü ayarlar tutulur.
"""

from dataclasses import dataclass, field
import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:  # python-dotenv kurulu değilse ortam değişkenleri kullanılır
    pass


def _split(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _bool(value: str) -> bool:
    return value.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    api_prefix: str = "/api"
    host: str = os.getenv("API_HOST", "127.0.0.1")
    port: int = int(os.getenv("API_PORT", "5000"))
    # Vite geliştirme sunucusu varsayılan olarak 5173 portunda çalışır
    cors_origins: list[str] = field(
        default_factory=lambda: _split(
            os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
        )
    )
    # Süresi dolan koltuk kilitlerini arka planda temizleyen iş parçacığı
    lock_cleaner_enabled: bool = _bool(os.getenv("LOCK_CLEANER_ENABLED", "true"))


settings = Settings()
