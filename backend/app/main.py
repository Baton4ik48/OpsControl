from fastapi import FastAPI
from app.middleware.allowed_user import AllowedNetworkMiddleware
from app.config import settings

app = FastAPI()

allowed_networks = settings.YAML["security"]["allowed_networks"]

app.add_middleware(
    AllowedNetworkMiddleware,
    allowed_networks=allowed_networks
)

@app.get("/health")
def health():
    return {
        "status": "ok",
        "env": settings.YAML["app"]["name"]
    }
