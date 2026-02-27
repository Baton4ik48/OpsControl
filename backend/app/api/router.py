from fastapi import APIRouter
from app.api import branches, servers, ports, credentials, status, tree, imports

router = APIRouter(prefix="/api")

router.include_router(branches.router)
router.include_router(servers.router)
router.include_router(ports.router)
router.include_router(credentials.router)
router.include_router(status.router)
router.include_router(tree.router)
router.include_router(imports.router)