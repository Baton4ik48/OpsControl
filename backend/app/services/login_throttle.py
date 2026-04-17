import time
from collections import defaultdict
from app.config import settings


class TooManyAttempts(Exception):
    pass


class LoginThrottle:
    def __init__(self, max_attempts: int, block_seconds: int):
        self.max_attempts = max_attempts
        self.block_seconds = block_seconds
        self.failed = defaultdict(list)

    def check(self, key: str):
        now = time.time()

        self.failed[key] = [
            ts for ts in self.failed[key] if now - ts < self.block_seconds
        ]

        if len(self.failed[key]) >= self.max_attempts:
            raise TooManyAttempts()

    def register_fail(self, key: str):
        self.failed[key].append(time.time())

    def reset(self, key: str):
        self.failed.pop(key, None)

    def time_until_unblock(self, key: str) -> int:
        if key not in self.failed or not self.failed[key]:
            return 0

        oldest = min(self.failed[key])
        now = time.time()

        remaining = self.block_seconds - (now - oldest)
        return max(0, int(remaining))


throttle = LoginThrottle(
    max_attempts=settings.LOGIN_MAX_ATTEMPTS,
    block_seconds=settings.LOGIN_BLOCK_SECONDS,
)
