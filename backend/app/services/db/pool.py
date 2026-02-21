from psycopg2.pool import SimpleConnectionPool
from psycopg2 import OperationalError, InterfaceError, errors
from app.config import settings
from app.services.db_credentials import get_db_credentials
import time
import logging

logger = logging.getLogger("postgres")

pool: SimpleConnectionPool | None = None


def init_pool(retries: int = 5, delay: int = 2):
    global pool
    creds = get_db_credentials()

    for attempt in range(1, retries + 1):
        try:
            pool = SimpleConnectionPool(
                1,
                10,
                host=creds.host,
                port=creds.port,
                dbname=creds.dbname,
                user=creds.user,
                password=creds.password,
                connect_timeout=settings.POSTGRES_CONNECT_TIMEOUT,
                options=f"-c statement_timeout={settings.POSTGRES_QUERY_TIMEOUT * 1000}",
            )
            logger.info("PostgreSQL pool initialized")
            return
        except OperationalError as e:
            logger.warning(f"Attempt {attempt}: {e}")
            time.sleep(delay)

    raise RuntimeError("PostgreSQL unavailable")


def close_pool():
    global pool
    if pool:
        pool.closeall()
        pool = None


def _execute(fn, retries: int = 1):
    global pool
    last_exc = None

    for _ in range(retries + 1):
        conn = None
        try:
            if pool is None:
                init_pool()

            conn = pool.getconn()
            return fn(conn)

        except (OperationalError,
                InterfaceError,
                errors.InsufficientPrivilege,
                errors.InvalidAuthorizationSpecification) as e:

            last_exc = e
            close_pool()
            init_pool()

        finally:
            if conn:
                pool.putconn(conn)

    raise last_exc