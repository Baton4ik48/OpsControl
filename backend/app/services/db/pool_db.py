from psycopg2.pool import SimpleConnectionPool
from psycopg2 import OperationalError, InterfaceError, errors
from app.config import settings
from app.services.vault_db_creds import get_db_credentials
from app.metrics import db_pool_reinit_total
import threading
import time
import logging

logger = logging.getLogger("postgres")

pool: SimpleConnectionPool | None = None

# Эндпоинты синхронные → FastAPI выполняет их в тредпуле, поэтому
# создание/закрытие глобального пула должно быть сериализовано.
_pool_lock = threading.RLock()


class ServiceUnavailableError(Exception):
    """Поднимается когда PostgreSQL или Vault недоступны — возвращаем 503."""

    pass


def init_pool(retries: int = 5, delay: int = 2) -> bool:
    """
    Инициализирует пул подключений к PostgreSQL.
    Никогда не бросает исключений — при ошибке логирует причину и возвращает False.
    Возвращает True при успехе. Если пул уже создан другим потоком — не пересоздаёт.
    """
    global pool

    with _pool_lock:
        if pool is not None:
            return True

        # Получаем учётные данные (может обращаться к Vault)
        try:
            creds = get_db_credentials()
        except Exception as e:
            logger.error("Не удалось получить учётные данные для БД: %s", e)
            pool = None
            return False

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
                return True
            except OperationalError as e:
                logger.warning(
                    "Попытка %d/%d подключения к PostgreSQL: %s", attempt, retries, e
                )
                time.sleep(delay)

        logger.error(
            "PostgreSQL недоступен после %d попыток — бэкенд работает без БД. "
            "Запросы к БД будут возвращать 503 до восстановления соединения.",
            retries,
        )
        pool = None
        return False


def close_pool():
    global pool
    with _pool_lock:
        if pool:
            pool.closeall()
            pool = None


def _reset_pool(expected: SimpleConnectionPool | None):
    """
    Пересоздаёт пул после ошибки соединения.

    Пересоздание происходит только если пул всё ещё тот, на котором
    случилась ошибка: без этой проверки несколько потоков, одновременно
    поймавших ошибку, по очереди закрывали бы уже новый рабочий пул.
    """
    global pool
    with _pool_lock:
        if pool is not expected:
            return
        close_pool()
        init_pool()
    db_pool_reinit_total.inc()


def execute(fn, retries: int = 1):
    last_exc = None

    for attempt in range(retries + 1):
        conn = None
        local_pool = pool

        try:
            if local_pool is None:
                init_pool()
                local_pool = pool

            if local_pool is None:
                raise ServiceUnavailableError(
                    "PostgreSQL недоступен — повторите запрос позже"
                )

            conn = local_pool.getconn()
            result = fn(conn)
            return result

        except ServiceUnavailableError:
            raise

        except errors.UndefinedTable as e:
            logger.error("Схема БД не инициализирована: %s", e)
            raise ServiceUnavailableError("База данных не инициализирована")

        except (
            OperationalError,
            InterfaceError,
            errors.InvalidAuthorizationSpecification,
            errors.InsufficientPrivilege,
        ) as e:
            last_exc = e
            logger.warning(
                "Pool error (attempt %d): %s: %s", attempt + 1, type(e).__name__, e
            )

            if conn:
                try:
                    local_pool.putconn(conn, close=True)
                    conn = None
                except Exception:
                    pass

            _reset_pool(local_pool)
            continue

        finally:
            if conn:
                try:
                    local_pool.putconn(conn)
                except Exception:
                    pass

    raise ServiceUnavailableError(
        f"PostgreSQL недоступен после {retries + 1} попыток: {last_exc}"
    )
