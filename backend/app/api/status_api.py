from fastapi import APIRouter
from app.services.status_services import get_overall_status

router = APIRouter(prefix="/status", tags=["status"])


@router.get("")
def get_status():
    return {
        "success": True,
        "data": {"status": get_overall_status()},
    }
