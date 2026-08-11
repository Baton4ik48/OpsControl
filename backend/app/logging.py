"""
Настройка логирования. Вызывается один раз при импорте через _configure_once().

Консоль (StreamHandler) получает всё от DEBUG root'а и выше уровня INFO —
это касается и WARNING/ERROR/CRITICAL, отдельного файла под них больше нет.
Вывод идёт в stdout и собирается Docker-драйвером (см. logging: в compose).

audit.log — исключение: все допущенные HTTP-запросы + чувствительные события
(TimedRotatingFileHandler, хранится 30 дней). Ему нужна гарантированная
глубина хранения, поэтому он остаётся файлом на именованном volume,
а не полагается на ротацию Docker-логов.

Логгер "audit" имеет propagate=False — записи идут ТОЛЬКО в audit.log
и никогда не попадают в консоль.

Все остальные логгеры propagate нормально до root → консоль.
"""

import logging
import logging.handlers
import os
from pathlib import Path

_LOG_DIR = Path(os.getenv("LOG_DIR", "/app/logs"))

_FMT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
_AUDIT_FMT = "%(asctime)s | AUDIT | %(message)s"

_MARKER = "_opscontrol_configured"


def _configure_once() -> None:
    root = logging.getLogger()
    if getattr(root, _MARKER, False):
        return
    setattr(root, _MARKER, True)

    root.setLevel(logging.DEBUG)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(_FMT))
    root.addHandler(console)

    if not os.access(_LOG_DIR, os.W_OK):
        raise RuntimeError(
            f"Каталог для логов недоступен на запись: {_LOG_DIR}. "
            "Убедитесь, что он существует и доступен пользователю, "
            "от которого запущен процесс (создаётся в Dockerfile), "
            "либо укажите другой путь через переменную окружения LOG_DIR."
        )

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
