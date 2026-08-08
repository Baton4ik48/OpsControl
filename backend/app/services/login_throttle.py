import threading
import time
from collections import defaultdict
from app.config import settings
from app.metrics import login_failed_total, login_blocked_total


class TooManyAttempts(Exception):
    pass


class LoginThrottle:
    """
    Счётчик неудачных логинов по ключу "username:ip".

    Эндпоинты выполняются в тредпуле FastAPI, поэтому все операции
    над разделяемым словарём защищены блокировкой.
    """

    def __init__(self, max_attempts: int, block_seconds: int):
        self.max_attempts = max_attempts
        self.block_seconds = block_seconds
        self.failed: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def check(self, key: str):
        now = time.time()

        with self._lock:
            attempts = [
                ts for ts in self.failed.get(key, []) if now - ts < self.block_seconds
            ]
            if attempts:
                self.failed[key] = attempts
            else:
                self.failed.pop(key, None)

            if len(attempts) >= self.max_attempts:
                login_blocked_total.inc()
                raise TooManyAttempts()

    def register_fail(self, key: str):
        now = time.time()
        with self._lock:
            # Заодно выбрасываем истёкшие записи по всем ключам,
            # иначе словарь растёт бесконечно (ключи с неудачными
            # логинами без последующего успеха никогда не чистились)
            self._purge_expired(now)
            self.failed[key].append(now)
        login_failed_total.inc()

    def reset(self, key: str):
        with self._lock:
            self.failed.pop(key, None)

    def time_until_unblock(self, key: str) -> int:
        with self._lock:
            attempts = self.failed.get(key)
            if not attempts:
                return 0

            oldest = min(attempts)
            remaining = self.block_seconds - (time.time() - oldest)
            return max(0, int(remaining))

    def _purge_expired(self, now: float):
        # Вызывается только под self._lock
        for key in list(self.failed):
            alive = [ts for ts in self.failed[key] if now - ts < self.block_seconds]
            if alive:
                self.failed[key] = alive
            else:
                del self.failed[key]


throttle = LoginThrottle(
    max_attempts=settings.LOGIN_MAX_ATTEMPTS,
    block_seconds=settings.LOGIN_BLOCK_SECONDS,
)
