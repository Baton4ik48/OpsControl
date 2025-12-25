from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api import health
from app.middleware.allowed_network import AllowedNetworkMiddleware
from app.config import settings

allowed_networks = settings.YAML["security"]["allowed_networks"]


app = FastAPI()

app.add_middleware(
    AllowedNetworkMiddleware,
    allowed_networks=allowed_networks
)

app.include_router(health.router)