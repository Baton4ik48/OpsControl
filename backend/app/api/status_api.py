from fastapi import APIRouter
from app.services.status_services import check_postgres, check_vault

router = APIRouter(prefix="/status", tags=["status"])


@router.get("")
def get_status():
    postgres_ok = check_postgres()
    vault_status = check_vault()

    if postgres_ok and vault_status == "ok":
        overall = "ok"
    elif not postgres_ok and vault_status in ("offline", "sealed"):
        overall = "unavailable"
    else:
        overall = "degraded"

    return {
        "success": True,
        "data": {"status": overall},
    }
