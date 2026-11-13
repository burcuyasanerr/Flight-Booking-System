"""
FastAPI uygulaması.

Çalıştırmak için proje kök klasöründe:

    python -m backend

Ardından API dokümantasyonu: http://localhost:5000/docs
"""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.errors import register_error_handlers
from backend.routers import airports, bookings, flights, seats
from backend.schemas import HealthResponse
from backend.services import db_manager, lock_manager
from concurrency.lock_manager import BackgroundLockCleaner

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("backend")


@asynccontextmanager
async def lifespan(_: FastAPI):
    if not db_manager.check_connection():
        logger.warning(
            "Veritabanına bağlanılamadı (%s:%s/%s). .env dosyasını kontrol edin; API istekleri 503 dönecek.",
            db_manager.config.host,
            db_manager.config.port,
            db_manager.config.dbname,
        )

    cleaner = BackgroundLockCleaner(lock_manager) if settings.lock_cleaner_enabled else None
    if cleaner:
        cleaner.start()
    try:
        yield
    finally:
        if cleaner:
            cleaner.stop()
        db_manager.close_pool()


app = FastAPI(
    title="Flight Ticket Purchasing System API",
    description="CEN317 Engineering Design · Team 19 — uçuş arama, koltuk kilitleme ve PNR/PDF bilet servisi.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],  # PDF indirirken dosya adını okuyabilmek için
)

register_error_handlers(app)

for router in (airports.router, flights.router, seats.router, bookings.router):
    app.include_router(router, prefix=settings.api_prefix)


@app.get(f"{settings.api_prefix}/health", response_model=HealthResponse, tags=["Sistem"], summary="Sağlık kontrolü")
def health():
    database_ok = db_manager.check_connection()
    return HealthResponse(status="ok" if database_ok else "degraded", database=database_ok)
