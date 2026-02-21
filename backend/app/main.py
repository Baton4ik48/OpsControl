from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.services.db.pool import init_pool, close_pool
from app.api.router import router as api_router
from app.middleware.allowed_network import AllowedNetworkMiddleware
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_pool()
    yield
    close_pool()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    AllowedNetworkMiddleware,
    allowed_networks=settings.ALLOWED_NETWORKS,
)

app.include_router(api_router)