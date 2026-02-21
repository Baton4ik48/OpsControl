from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.services.credentials import (
    show_credentials,
    InvalidMasterPassword,
    CredentialsNotFound,
    TooManyLoginAttempts,
)

router = APIRouter(
    prefix="/credentials",
    tags=["credentials"]
)


class ShowCredentialsRequest(BaseModel):
    server_id: int
    port: int
    username: str
    master_password: str


@router.post("/show")
def show_credentials_api(
    data: ShowCredentialsRequest,
    request: Request,
):
    client_ip = request.client.host

    try:
        creds = show_credentials(
            server_id=data.server_id,
            port=data.port,
            username=data.username,
            master_password=data.master_password,
            client_ip=client_ip,
        )

        return {
            "success": True,
            "data": creds
        }

    except TooManyLoginAttempts as e:
        return JSONResponse(
            status_code=429,
            content={
                "error_code": "LOGIN_THROTTLED",
                "retry_after": e.retry_after_seconds,
            }
        )

    except InvalidMasterPassword:
        return JSONResponse(
            status_code=403,
            content={
                "error_code": "INVALID_MASTER_PASSWORD"
            }
        )

    except CredentialsNotFound:
        raise HTTPException(
            status_code=404,
            detail="Credentials not found"
        )
    

