from fastapi import APIRouter, UploadFile, File
from app.services.db.import_service import preview_import, apply_import

router = APIRouter(prefix="/import", tags=["import"])


@router.post("/preview")
async def bulk_preview(file: UploadFile = File(...)):
    result = preview_import(file.file)
    return {"success": True, "data": result}


@router.post("/apply")
async def bulk_apply(file: UploadFile = File(...)):
    result = apply_import(file.file)
    return {"success": True, "data": result}