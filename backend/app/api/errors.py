"""
Глобальные обработчики доменных исключений.

Убирают из эндпоинтов копипасту try/except для троттлинга и неверного
мастер-пароля: эндпоинт описывает только happy path, а 429/403 и
audit-запись о неудаче формируются здесь.

Эндпоинт перед вызовом сервиса задаёт контекст через set_audit_context() —
он попадает в audit.log при любом исходе.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.services.credentials import InvalidMasterPassword, TooManyLoginAttempts

_audit = logging.getLogger("audit")


def set_audit_context(request: Request, action: str, **fields) -> None:
    """Сохраняет action и его параметры для audit-записи об отказе."""
    request.state.audit_action = action
    request.state.audit_fields = fields


def _audit_failure(request: Request, result: str) -> None:
    action = getattr(request.state, "audit_action", "unknown")
    fields = getattr(request.state, "audit_fields", {})

    ip = getattr(request.state, "client_ip", None) or (
        request.client.host if request.client else "unknown"
    )
    rid = getattr(request.state, "request_id", "-")

    parts = [f"action={action}"]
    parts += [f"{k}={v}" for k, v in fields.items()]
    parts += [f"result={result}", f"ip={ip}", f"request_id={rid}"]
    _audit.info(" ".join(parts))


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(TooManyLoginAttempts)
    async def too_many_attempts_handler(request: Request, exc: TooManyLoginAttempts):
        _audit_failure(request, "throttled")
        return JSONResponse(
            status_code=429,
            content={
                "error_code": "LOGIN_THROTTLED",
                "retry_after": exc.retry_after_seconds,
            },
        )

    @app.exception_handler(InvalidMasterPassword)
    async def invalid_master_password_handler(
        request: Request, exc: InvalidMasterPassword
    ):
        _audit_failure(request, "invalid_password")
        return JSONResponse(
            status_code=403, content={"error_code": "INVALID_MASTER_PASSWORD"}
        )
