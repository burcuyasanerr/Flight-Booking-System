"""
API testleri gerçek bir PostgreSQL üzerinde çalışır.

Testler `flight_booking_test` adında ayrı bir veritabanı kurar, `schema.sql` ve
`seed.sql` ile doldurur, iş bitince siler. Asıl `flight_booking` veritabanına
dokunulmaz. PostgreSQL'e bağlanılamazsa testler atlanır.

Çalıştırma (proje kök klasöründe):

    python -m pytest backend/tests -v
"""

import os
from pathlib import Path

import pytest

TEST_DB = os.environ.get("TEST_DB_NAME", "flight_booking_test")
# Uygulama import edilmeden önce ayarlanmalı: DatabaseConfig değerleri import anında okunur.
os.environ["DB_NAME"] = TEST_DB
os.environ["LOCK_CLEANER_ENABLED"] = "false"

import psycopg2  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.main import app  # noqa: E402
from backend.services import db_manager  # noqa: E402

DATABASE_DIR = Path(__file__).resolve().parents[2] / "database"


def _admin_connection(dbname: str):
    cfg = db_manager.config
    conn = psycopg2.connect(
        host=cfg.host, port=cfg.port, user=cfg.user, password=cfg.password, dbname=dbname, connect_timeout=5
    )
    conn.autocommit = True
    return conn


def load_schema_and_seed():
    """Veritabanını schema.sql + seed.sql ile baştan kurar (schema.sql önce her şeyi siler)."""
    conn = _admin_connection(TEST_DB)
    try:
        with conn.cursor() as cursor:
            for name in ("schema.sql", "seed.sql"):
                cursor.execute((DATABASE_DIR / name).read_text(encoding="utf-8"))
    finally:
        conn.close()


@pytest.fixture(scope="session")
def test_database():
    try:
        conn = _admin_connection("postgres")
    except psycopg2.OperationalError as exc:
        pytest.skip(f"PostgreSQL'e bağlanılamadı, API testleri atlandı: {exc}")

    with conn.cursor() as cursor:
        cursor.execute(f'DROP DATABASE IF EXISTS "{TEST_DB}" WITH (FORCE);')
        cursor.execute(f'CREATE DATABASE "{TEST_DB}" ENCODING \'UTF8\' TEMPLATE template0;')
    load_schema_and_seed()

    yield

    db_manager.close_pool()
    with conn.cursor() as cursor:
        cursor.execute(f'DROP DATABASE IF EXISTS "{TEST_DB}" WITH (FORCE);')
    conn.close()


@pytest.fixture(scope="session")
def client(test_database):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def fresh_db(client):
    """Veriyi değiştiren testlerden önce örnek verileri sıfırlar."""
    load_schema_and_seed()
    yield
