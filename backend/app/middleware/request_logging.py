"""
Middleware для HTTP-аудита запросов.

Выполняется ВНУТРИ AllowedNetworkMiddleware (который снаружи) — видит только запросы,
прошедшие проверку сети.

Пишет одну строку на запрос в логгер "audit" → audit.log.
Ответы 5xx дополнительно дублируются в логгер "http" → errors.log.

Подавление высокочастотных запросов:
  POST /…/result (обновление статуса порта) — фронтенд шлёт 100+ таких запросов
  за один poll-цикл (по одному на каждый сервер). Успешные 200 молча отбрасываются
  чтобы audit.log оставался читаемым. Ошибки (не 200) по-прежнему логируются.
"""

import time
import uuid
import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

_audit = logging.getLogger("audit")
_log = logging.getLogger("http")

_RESULT_SUFFIX = "/result"


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = uuid.uuid4().hex[:8]
        request.state.request_id = request_id

        t0 = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - t0) * 1000)

        method = request.method
        path = request.url.path
        status = response.status_code

        # Подавляем успешные port-result пинги — слишком много шума в audit.log
        if method == "POST" and path.endswith(_RESULT_SUFFIX) and status == 200:
            return response

        # client_ip устанавливается AllowedNetworkMiddleware до нас
        client_ip = getattr(request.state, "client_ip", None) or (
            request.client.host if request.client else "unknown"
        )
        actor = getattr(request.state, "actor", "anonymous")
        agent = request.headers.get("user-agent", "")[:200]

        _audit.info(
            'method=%s path="%s" status=%d duration_ms=%d ip=%s request_id=%s actor=%s agent="%s"',
            method,
            path,
            status,
            duration_ms,
            client_ip,
            request_id,
            actor,
            agent,
        )

        if status >= 500:
            _log.warning(
                "HTTP %d %s %s — duration_ms=%d ip=%s request_id=%s",
                status,
                method,
                path,
                duration_ms,
                client_ip,
                request_id,
            )

        return response
