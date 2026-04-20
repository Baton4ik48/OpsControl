import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.services.db.pool_db import init_pool, close_pool, ServiceUnavailableError
from app.services.vault_renewer import vault_renew_loop
from app.api.router import router as api_router
from app.middleware.allowed_network import AllowedNetworkMiddleware
from app.config import settings

logger = logging.getLogger("startup")


@asynccontextmanager
async def lifespan(app: FastAPI):
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
    close_pool()


app = FastAPI(lifespan=lifespan)


@app.exception_handler(ServiceUnavailableError)
async def service_unavailable_handler(request: Request, exc: ServiceUnavailableError):
    return JSONResponse(
        status_code=503,
        content={
            "error_code": "SERVICE_UNAVAILABLE",
            "detail": str(exc),
        },
    )


app.add_middleware(
    AllowedNetworkMiddleware,
    allowed_networks=settings.ALLOWED_NETWORKS,
    trusted_proxies=settings.TRUSTED_PROXIES,
)

app.include_router(api_router)
