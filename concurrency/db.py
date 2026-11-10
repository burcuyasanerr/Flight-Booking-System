"""
Flight Ticket Purchasing System - Database Connection Manager
Eşzamanlı istekler için thread-safe bağlantı havuzu (ThreadedConnectionPool) yöneticisi.
"""

from contextlib import contextmanager
import logging
from typing import Generator, Optional
import psycopg2
from psycopg2.extensions import connection as PGConnection, cursor as PGCursor
from psycopg2.pool import ThreadedConnectionPool

try:
    from .config import DatabaseConfig, DEFAULT_DB_CONFIG
except ImportError:
    from config import DatabaseConfig, DEFAULT_DB_CONFIG

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    İş parçacığı güvenli (thread-safe) PostgreSQL bağlantı havuzu yöneticisi.
    """

    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DEFAULT_DB_CONFIG
        self._pool: Optional[ThreadedConnectionPool] = None

    def initialize_pool(self):
        """Bağlantı havuzunu başlatır."""
        if self._pool is None or self._pool.closed:
            try:
                self._pool = ThreadedConnectionPool(
                    minconn=self.config.min_conn,
                    maxconn=self.config.max_conn,
                    host=self.config.host,
                    port=self.config.port,
                    dbname=self.config.dbname,
                    user=self.config.user,
                    password=self.config.password,
                    connect_timeout=5,
                )
                logger.info(
                    "PostgreSQL bağlantı havuzu oluşturuldu. (Host: %s:%s, DB: %s)",
                    self.config.host,
                    self.config.port,
                    self.config.dbname,
                )
            except psycopg2.Error as err:
                logger.error("Bağlantı havuzu başlatılamadı: %s", err)
                raise

    def close_pool(self):
        """Havuzdaki tüm bağlantıları kapatır."""
        if self._pool and not self._pool.closed:
            self._pool.closeall()
            self._pool = None
            logger.info("PostgreSQL bağlantı havuzu kapatıldı.")

    @contextmanager
    def get_connection(self) -> Generator[PGConnection, None, None]:
        """
        Havuzdan bir bağlantı ödünç alır ve işlem bitiminde havuza iade eder.
        Hata durumunda otomatik ROLLBACK yapar.
        """
        if self._pool is None or self._pool.closed:
            self.initialize_pool()

        conn = self._pool.getconn()
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise
        finally:
            if not conn.closed:
                self._pool.putconn(conn)

    @contextmanager
    def get_cursor(self, commit: bool = True) -> Generator[PGCursor, None, None]:
        """
        Kullanıma hazır bir veritabanı imleci (cursor) sağlar.
        commit=True ise işlem başarıyla tamamlandığında commit() çağrılır.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
                if commit:
                    conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                cursor.close()

    def check_connection(self) -> bool:
        """Veritabanı bağlantısının aktif olup olmadığını test eder."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT 1;")
                return cursor.fetchone()[0] == 1
        except Exception as ex:
            logger.warning("Veritabanı bağlantı testi başarısız: %s", ex)
            return False


# Varsayılan singleton veritabanı yöneticisi örneği
db_manager = DatabaseManager()
