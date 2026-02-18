from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.services.postgres import init_pool, close_pool
from app.api.api_database import router as db_router
from app.api.api_status import router as status_router
from app.api.api_credentials import router as credentials_router
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


app.include_router(status_router)
app.include_router(db_router)
app.include_router(credentials_router)
