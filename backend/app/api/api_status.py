from fastapi import APIRouter

from app.services.status_services import get_overall_status

router = APIRouter(prefix="/api")


@router.get("/status")
def status():
    return {
        "status": get_overall_status()
    }
