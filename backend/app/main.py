from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api import health
from app.api.api_database import router as db_router
from app.middleware.allowed_network import AllowedNetworkMiddleware
from app.config import settings
from app.api.api_database import router as db_router

allowed_networks = settings.YAML["security"]["allowed_networks"]


app = FastAPI()

app.add_middleware(
    AllowedNetworkMiddleware,
    allowed_networks=allowed_networks
)

app.include_router(health.router)
app.include_router(db_router)