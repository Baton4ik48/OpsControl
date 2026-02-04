from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.credentials import (
    show_credentials,
    InvalidMasterPassword,
    CredentialsNotFound,
)

router = APIRouter(
    prefix="/api/credentials",
    tags=["credentials"]
)

class ShowCredentialsRequest(BaseModel):
    server_id: int
    port: int
    username: str
    master_password: str


@router.post("/show")
def api_show_credentials(data: ShowCredentialsRequest):
    try:
        creds = show_credentials(
            server_id=data.server_id,
            port=data.port,
            username=data.username,
            master_password=data.master_password,
        )
        return {"success": True, "data": creds}

    except InvalidMasterPassword:
        raise HTTPException(403, detail="Invalid master password")

    except CredentialsNotFound:
        raise HTTPException(404, detail="Credentials not found")
