"""
Настройка логирования. Вызывается один раз при импорте через _configure_once().

Два файловых обработчика:
  errors.log  — WARNING / ERROR / CRITICAL с трейсбэками (RotatingFileHandler)
  audit.log   — все допущенные HTTP-запросы + чувствительные события (TimedRotatingFileHandler)

Логгер "audit" имеет propagate=False — записи идут ТОЛЬКО в audit.log
и никогда не попадают в errors.log или консоль.

Все остальные логгеры propagate нормально до root → консоль + errors.log.
"""

import logging
import logging.handlers
from pathlib import Path

_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)

_FMT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
_AUDIT_FMT = "%(asctime)s | AUDIT | %(message)s"

_MARKER = "_opscontrol_configured"


def _configure_once() -> None:
    root = logging.getLogger()
    if getattr(root, _MARKER, False):
        return
    setattr(root, _MARKER, True)

    root.setLevel(logging.DEBUG)

    # Консоль: INFO+ (разработка / docker logs / uvicorn)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(_FMT))
    root.addHandler(console)

    # errors.log: WARNING+ с ротацией (10 МБ × 5 архивов)
    err_handler = logging.handlers.RotatingFileHandler(
        _LOG_DIR / "errors.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    err_handler.setLevel(logging.WARNING)
    err_handler.setFormatter(logging.Formatter(_FMT))
    root.addHandler(err_handler)

    # audit-логгер: изолирован, без propagation → только в audit.log
    audit_log = logging.getLogger("audit")
    audit_log.setLevel(logging.INFO)
    audit_log.propagate = False

    audit_handler = logging.handlers.TimedRotatingFileHandler(
        _LOG_DIR / "audit.log",
        when="midnight",
        backupCount=30,
        encoding="utf-8",
    )
    audit_handler.setLevel(logging.INFO)
    audit_handler.setFormatter(logging.Formatter(_AUDIT_FMT))
    audit_log.addHandler(audit_handler)


_configure_once()


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def get_audit_logger() -> logging.Logger:
    return logging.getLogger("audit")
