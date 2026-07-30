from fastapi import APIRouter
from app.api import (
    branches_api,
    credentials_api,
    inventory_api,
    ports_api,
    servers_api,
    status_api,
    tree_api,
)

router = APIRouter(prefix="/api")

router.include_router(branches_api.router)
router.include_router(servers_api.router)
router.include_router(ports_api.router)
router.include_router(credentials_api.router)
router.include_router(status_api.router)
router.include_router(tree_api.router)
router.include_router(inventory_api.router)
