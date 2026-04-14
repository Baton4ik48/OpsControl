from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.services.credentials import (
    show_credentials,
    verify_admin_password,
    upsert_credentials,
    rotate_credentials,
    InvalidMasterPassword,
    CredentialsNotFound,
    TooManyLoginAttempts,
    RotateError,
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


class VerifyAdminRequest(BaseModel):
    username: str
    master_password: str


class UpsertCredentialsRequest(BaseModel):
    server_id: int
    port: int
    username: str
    password: str


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


@router.post("/verify-admin")
def verify_admin_api(
    data: VerifyAdminRequest,
    request: Request,
):
    client_ip = request.client.host

    try:
        verify_admin_password(
            username=data.username,
            master_password=data.master_password,
            client_ip=client_ip,
        )

        return {"success": True}

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


@router.post("/upsert")
def upsert_credentials_api(data: UpsertCredentialsRequest):
    try:
        vault_path = upsert_credentials(
            server_id=data.server_id,
            port=data.port,
            username=data.username,
            password=data.password,
        )

        return {
            "success": True,
            "data": {"vault_path": vault_path}
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class RotateCredentialsRequest(BaseModel):
    server_id: int
    ssh_port: int
    new_password: str
    username: str
    master_password: str
    mnemonic: str = ""


@router.post("/rotate")
def rotate_credentials_api(data: RotateCredentialsRequest, request: Request):
    client_ip = request.client.host

    try:
        rotate_credentials(
            server_id=data.server_id,
            ssh_port=data.ssh_port,
            new_password=data.new_password,
            username=data.username,
            master_password=data.master_password,
            client_ip=client_ip,
            mnemonic=data.mnemonic,
        )
        return {"success": True}

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
            content={"error_code": "INVALID_MASTER_PASSWORD"}
        )

    except RotateError as e:
        return JSONResponse(
            status_code=422,
            content={"error_code": "ROTATE_FAILED", "detail": str(e)}
        )
