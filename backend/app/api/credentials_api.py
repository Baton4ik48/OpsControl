import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.services.credentials import (
    show_credentials,
    verify_admin_password,
    upsert_credentials,
    rotate_credentials,
    export_all_credentials,
    InvalidMasterPassword,
    CredentialsNotFound,
    TooManyLoginAttempts,
    RotateError,
)

logger = logging.getLogger("credentials.api")
_audit = logging.getLogger("audit")

router = APIRouter(prefix="/credentials", tags=["credentials"])


def _ctx(request: Request) -> tuple[str, str]:
    """Возвращает (client_ip, request_id) из request.state, с fallback-значениями."""
    ip = getattr(request.state, "client_ip", None) or (
        request.client.host if request.client else "unknown"
    )
    rid = getattr(request.state, "request_id", "-")
    return ip, rid


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
    client_ip, request_id = _ctx(request)

    try:
        creds = show_credentials(
            server_id=data.server_id,
            port=data.port,
            username=data.username,
            master_password=data.master_password,
            client_ip=client_ip,
        )

        # Авторизация в Vault прошла → username подтверждён
        request.state.actor = data.username

        _audit.info(
            "action=read_credentials server_id=%s port=%s username=%s result=ok"
            " ip=%s request_id=%s",
            data.server_id,
            data.port,
            data.username,
            client_ip,
            request_id,
        )
        return {"success": True, "data": creds}

    except TooManyLoginAttempts as e:
        _audit.info(
            "action=read_credentials server_id=%s port=%s username=%s result=throttled"
            " ip=%s request_id=%s",
            data.server_id,
            data.port,
            data.username,
            client_ip,
            request_id,
        )
        return JSONResponse(
            status_code=429,
            content={
                "error_code": "LOGIN_THROTTLED",
                "retry_after": e.retry_after_seconds,
            },
        )

    except InvalidMasterPassword:
        _audit.info(
            "action=read_credentials server_id=%s port=%s username=%s result=invalid_password"
            " ip=%s request_id=%s",
            data.server_id,
            data.port,
            data.username,
            client_ip,
            request_id,
        )
        return JSONResponse(
            status_code=403, content={"error_code": "INVALID_MASTER_PASSWORD"}
        )

    except CredentialsNotFound:
        raise HTTPException(status_code=404, detail="Credentials not found")


@router.post("/verify-admin")
def verify_admin_api(
    data: VerifyAdminRequest,
    request: Request,
):
    client_ip, request_id = _ctx(request)

    try:
        verify_admin_password(
            username=data.username,
            master_password=data.master_password,
            client_ip=client_ip,
        )

        # Авторизация в Vault прошла → username подтверждён
        request.state.actor = data.username

        _audit.info(
            "action=verify_admin username=%s result=ok ip=%s request_id=%s",
            data.username,
            client_ip,
            request_id,
        )
        return {"success": True}

    except TooManyLoginAttempts as e:
        _audit.info(
            "action=verify_admin username=%s result=throttled ip=%s request_id=%s",
            data.username,
            client_ip,
            request_id,
        )
        return JSONResponse(
            status_code=429,
            content={
                "error_code": "LOGIN_THROTTLED",
                "retry_after": e.retry_after_seconds,
            },
        )

    except InvalidMasterPassword:
        _audit.info(
            "action=verify_admin username=%s result=invalid_password ip=%s request_id=%s",
            data.username,
            client_ip,
            request_id,
        )
        return JSONResponse(
            status_code=403, content={"error_code": "INVALID_MASTER_PASSWORD"}
        )


@router.post("/upsert")
def upsert_credentials_api(data: UpsertCredentialsRequest, request: Request):
    client_ip, request_id = _ctx(request)

    try:
        vault_path = upsert_credentials(
            server_id=data.server_id,
            port=data.port,
            username=data.username,
            password=data.password,
        )

        _audit.info(
            "action=upsert_credentials server_id=%s port=%s username=%s"
            " vault_path=%s ip=%s request_id=%s",
            data.server_id,
            data.port,
            data.username,
            vault_path,
            client_ip,
            request_id,
        )
        return {"success": True, "data": {"vault_path": vault_path}}

    except Exception as e:
        logger.error(
            "upsert_credentials failed server_id=%s port=%s: %s",
            data.server_id,
            data.port,
            e,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal server error")


class RotateCredentialsRequest(BaseModel):
    server_id: int
    ssh_port: int
    new_password: str
    username: str
    master_password: str
    mnemonic: str = ""


@router.post("/rotate")
def rotate_credentials_api(data: RotateCredentialsRequest, request: Request):
    client_ip, request_id = _ctx(request)

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

        # Авторизация в Vault прошла → username подтверждён
        request.state.actor = data.username

        _audit.info(
            "action=rotate_credentials server_id=%s port=%s username=%s result=ok"
            " ip=%s request_id=%s",
            data.server_id,
            data.ssh_port,
            data.username,
            client_ip,
            request_id,
        )
        return {"success": True}

    except TooManyLoginAttempts as e:
        _audit.info(
            "action=rotate_credentials server_id=%s port=%s username=%s result=throttled"
            " ip=%s request_id=%s",
            data.server_id,
            data.ssh_port,
            data.username,
            client_ip,
            request_id,
        )
        return JSONResponse(
            status_code=429,
            content={
                "error_code": "LOGIN_THROTTLED",
                "retry_after": e.retry_after_seconds,
            },
        )

    except InvalidMasterPassword:
        _audit.info(
            "action=rotate_credentials server_id=%s port=%s username=%s"
            " result=invalid_password ip=%s request_id=%s",
            data.server_id,
            data.ssh_port,
            data.username,
            client_ip,
            request_id,
        )
        return JSONResponse(
            status_code=403, content={"error_code": "INVALID_MASTER_PASSWORD"}
        )

    except RotateError as e:
        logger.warning(
            "rotate_credentials failed server_id=%s port=%s: %s",
            data.server_id,
            data.ssh_port,
            e,
        )
        _audit.info(
            "action=rotate_credentials server_id=%s port=%s username=%s result=failed"
            " ip=%s request_id=%s",
            data.server_id,
            data.ssh_port,
            data.username,
            client_ip,
            request_id,
        )
        return JSONResponse(
            status_code=422,
            content={
                "error_code": "ROTATE_FAILED",
                "detail": "Credential rotation failed",
            },
        )


class ExportAllCredentialsRequest(BaseModel):
    username: str
    master_password: str


@router.post("/export-all")
def export_all_credentials_api(
    data: ExportAllCredentialsRequest,
    request: Request,
):
    client_ip, request_id = _ctx(request)

    try:
        entries = export_all_credentials(
            username=data.username,
            master_password=data.master_password,
            client_ip=client_ip,
        )

        request.state.actor = data.username

        _audit.info(
            "action=export_all_credentials username=%s count=%d result=ok"
            " ip=%s request_id=%s",
            data.username,
            len(entries),
            client_ip,
            request_id,
        )
        return {"success": True, "data": entries}

    except TooManyLoginAttempts as e:
        _audit.info(
            "action=export_all_credentials username=%s result=throttled"
            " ip=%s request_id=%s",
            data.username,
            client_ip,
            request_id,
        )
        return JSONResponse(
            status_code=429,
            content={
                "error_code": "LOGIN_THROTTLED",
                "retry_after": e.retry_after_seconds,
            },
        )

    except InvalidMasterPassword:
        _audit.info(
            "action=export_all_credentials username=%s result=invalid_password"
            " ip=%s request_id=%s",
            data.username,
            client_ip,
            request_id,
        )
        return JSONResponse(
            status_code=403, content={"error_code": "INVALID_MASTER_PASSWORD"}
        )

    except Exception as e:
        logger.error("export_all_credentials failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
