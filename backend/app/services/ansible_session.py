import secrets
import time

_TTL_SECONDS = 600  # 10 минут

_sessions: dict[str, tuple[str, float]] = {}  # token -> (username, expires_at)


def issue_session(username: str) -> tuple[str, int]:
    _cleanup()
    token = secrets.token_urlsafe(32)
    _sessions[token] = (username, time.monotonic() + _TTL_SECONDS)
    return token, _TTL_SECONDS


def verify_session(token: str) -> str | None:
    _cleanup()
    entry = _sessions.get(token)
    if not entry:
        return None
    username, expires_at = entry
    if time.monotonic() > expires_at:
        _sessions.pop(token, None)
        return None
    return username


def _cleanup() -> None:
    now = time.monotonic()
    expired = [t for t, (_, exp) in _sessions.items() if exp < now]
    for t in expired:
        _sessions.pop(t, None)
