from fastapi import APIRouter
from app.services.status_services import check_postgres, check_vault

router = APIRouter(prefix="/status", tags=["status"])


@router.get("")
def get_status():
    postgres_ok = check_postgres()
    vault_status = check_vault()

    overall = "ok"
    if not postgres_ok or vault_status != "ok":
        overall = "degraded"
    if not postgres_ok and vault_status == "offline":
        overall = "offline"

    return {
        "success": True,
        "data": {
            "status": overall,
            "postgres": "ok" if postgres_ok else "offline",
            "vault": vault_status,
        },
    }
