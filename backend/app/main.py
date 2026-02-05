from fastapi import FastAPI
from app.api.api_database import router as db_router
from app.api.api_status import router as status_router
from app.api.api_credentials import router as credentials_router
from app.middleware.allowed_network import AllowedNetworkMiddleware
from app.config import settings

allowed_networks = settings.YAML["security"]["allowed_networks"]

app = FastAPI()

app.add_middleware(
    AllowedNetworkMiddleware,
    allowed_networks=allowed_networks
)

app.include_router(status_router)
app.include_router(db_router)
app.include_router(credentials_router)