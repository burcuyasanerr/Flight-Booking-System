"""
Ortak hata yapısı.

Tüm hatalar aynı biçimde döner, böylece frontend tek bir yerde işleyebilir:

    {"detail": {"code": "FLIGHT_NOT_FOUND", "message": "Uçuş bulunamadı."}}
"""

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import psycopg2
from psycopg2.pool import PoolError

logger = logging.getLogger(__name__)


def api_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": {"code": code, "message": message}})


def _field_name(loc: tuple) -> str:
    # ("query", "from") -> "from", ("body", "session_id") -> "session_id", ("body",) -> "body"
    if not loc:
        return "request"
    parts = [str(p) for p in loc if p not in ("query", "path", "body", "header")]
    return ".".join(parts) or str(loc[-1])


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        # FastAPI'nin varsayılan 422 cevabı bir liste döner; diğer hatalarla aynı biçime getirilir.
        errors = [{"field": _field_name(tuple(e.get("loc", ()))), "message": e.get("msg", "")} for e in exc.errors()]
        fields = ", ".join(dict.fromkeys(e["field"] for e in errors))
        return JSONResponse(
            status_code=422,
            content={
                "detail": {
                    "code": "VALIDATION_ERROR",
                    "message": f"Geçersiz veya eksik alan: {fields}",
                    "errors": errors,
                }
            },
        )

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
