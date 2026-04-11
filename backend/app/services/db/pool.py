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
            print("⚠️ POOL RECREATE TRIGGERED:", type(e), e)
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
        local_pool = pool

        try:
            if local_pool is None:
                init_pool()
                local_pool = pool

            conn = local_pool.getconn()
            result = fn(conn)
            return result

        except (
            OperationalError,
            InterfaceError,
            errors.InvalidAuthorizationSpecification,
            errors.InsufficientPrivilege,
        ) as e:

            last_exc = e
            logger.warning(f"Pool error, recreating: {type(e).__name__}: {e}")

            if conn:
                try:
                    local_pool.putconn(conn, close=True)
                except Exception:
                    pass

            close_pool()
            init_pool()
            continue

        finally:
            if conn:
                try:
                    local_pool.putconn(conn)
                except Exception:
                    pass

    raise last_exc