"""
Production logging setup. Called once at import time via _configure_once().

Two file sinks:
  errors.log  — WARNING / ERROR / CRITICAL with full tracebacks (RotatingFileHandler)
  audit.log   — all allowed HTTP requests + sensitive business events (TimedRotatingFileHandler)

The "audit" logger has propagate=False so audit records go ONLY to audit.log
and never appear in errors.log or console.

All other loggers propagate normally to root → console + errors.log.
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

    # Console: INFO+ (dev / docker logs / uvicorn captures this)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(_FMT))
    root.addHandler(console)

    # errors.log: WARNING+ with rotation (10 MB × 5 archives)
    err_handler = logging.handlers.RotatingFileHandler(
        _LOG_DIR / "errors.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    err_handler.setLevel(logging.WARNING)
    err_handler.setFormatter(logging.Formatter(_FMT))
    root.addHandler(err_handler)

    # audit logger: isolated, no propagation → only goes to audit.log
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
