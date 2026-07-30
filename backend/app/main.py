import asyncio

# Должен быть первым: настраивает root-логгер и file handlers до остальных импортов
import app.logging  # noqa: F401

import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.services.db.pool_db import init_pool, close_pool, ServiceUnavailableError
from app.services.vault_renewer import vault_renew_loop
from app.api.errors import register_exception_handlers
from app.api.router import router as api_router
from app.middleware.allowed_network import AllowedNetworkMiddleware
from app.middleware.request_logging import RequestLoggingMiddleware
from app.config import settings

logger = logging.getLogger("startup")


@asynccontextmanager
async def lifespan(app: FastAPI):
    missing = settings.validate()
    if missing:
        raise RuntimeError(
            f"Отсутствуют обязательные переменные окружения: {', '.join(missing)}. "
            f"Проверьте .env (DB_CREDS_MODE={settings.DB_CREDS_MODE})."
        )

    # init_pool никогда не бросает — логирует ошибку и продолжает работу
    ok = init_pool()
    if not ok:
        logger.warning(
            "Бэкенд запущен без подключения к БД. "
            "Запросы к данным будут возвращать 503 до восстановления сервисов."
        )
    task = asyncio.create_task(vault_renew_loop())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
    close_pool()


app = FastAPI(lifespan=lifespan)

register_exception_handlers(app)


@app.exception_handler(ServiceUnavailableError)
async def service_unavailable_handler(request: Request, exc: ServiceUnavailableError):
    return JSONResponse(
        status_code=503,
        content={
            "error_code": "SERVICE_UNAVAILABLE",
            "detail": str(exc),
        },
    )


# Стек middleware (последний добавленный = внешний = выполняется первым):
#   AllowedNetworkMiddleware → определяет и проверяет IP клиента, блокирует запрещённые сети
#   RequestLoggingMiddleware → пишет все допущенные запросы в audit.log
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    AllowedNetworkMiddleware,
    allowed_networks=settings.ALLOWED_NETWORKS,
    trusted_proxies=settings.TRUSTED_PROXIES,
)

app.include_router(api_router)
