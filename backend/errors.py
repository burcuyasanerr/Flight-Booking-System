"""
Ortak hata yapısı.

Tüm hatalar aynı biçimde döner, böylece frontend tek bir yerde işleyebilir:

    {"detail": {"code": "FLIGHT_NOT_FOUND", "message": "Uçuş bulunamadı."}}
"""

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import psycopg2
from psycopg2.pool import PoolError

logger = logging.getLogger(__name__)


def api_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": {"code": code, "message": message}})


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(PoolError)
    async def pool_exhausted(_: Request, exc: PoolError):
        logger.warning("Bağlantı havuzu dolu: %s", exc)
        return _error_response(503, "SERVER_BUSY", "Sunucu şu anda yoğun, lütfen tekrar deneyiniz.")

    @app.exception_handler(psycopg2.OperationalError)
    async def database_unavailable(_: Request, exc: psycopg2.OperationalError):
        logger.error("Veritabanına bağlanılamadı: %s", exc)
        return _error_response(503, "DATABASE_UNAVAILABLE", "Veritabanına bağlanılamadı.")

    @app.exception_handler(psycopg2.Error)
    async def database_error(_: Request, exc: psycopg2.Error):
        # Ayrıntı yalnızca sunucu loguna yazılır, istemciye SQL hatası gösterilmez
        logger.exception("Veritabanı hatası: %s", exc)
        return _error_response(500, "DATABASE_ERROR", "Beklenmeyen bir veritabanı hatası oluştu.")
