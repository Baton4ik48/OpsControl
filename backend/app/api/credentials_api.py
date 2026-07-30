import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.api.errors import set_audit_context
from app.services.credentials import (
    show_credentials,
    verify_admin_password,
    upsert_credentials,
    rotate_credentials,
    export_all_credentials,
    CredentialsNotFound,
    RotateError,
    InvalidMasterPassword,
    TooManyLoginAttempts,
)

# 429 (троттлинг) и 403 (неверный мастер-пароль) обрабатываются глобально —
# см. app/api/errors.py; здесь только happy path и специфичные ошибки.

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


def _audit_ok(request: Request) -> None:
    """Пишет audit-запись об успехе, используя контекст из set_audit_context."""
    action = request.state.audit_action
    fields = request.state.audit_fields
    ip, rid = _ctx(request)

    parts = [f"action={action}"]
    parts += [f"{k}={v}" for k, v in fields.items()]
    parts += ["result=ok", f"ip={ip}", f"request_id={rid}"]
    _audit.info(" ".join(parts))


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


class RotateCredentialsRequest(BaseModel):
    server_id: int
    ssh_port: int
    new_password: str
    username: str
    master_password: str
    mnemonic: str = ""


class ExportAllCredentialsRequest(BaseModel):
    username: str
    master_password: str


@router.post("/show")
def show_credentials_api(data: ShowCredentialsRequest, request: Request):
    client_ip, _ = _ctx(request)
    set_audit_context(
        request,
        "read_credentials",
        server_id=data.server_id,
        port=data.port,
        username=data.username,
    )

    try:
        creds = show_credentials(
            server_id=data.server_id,
            port=data.port,
            username=data.username,
            master_password=data.master_password,
            client_ip=client_ip,
        )
    except CredentialsNotFound:
        raise HTTPException(status_code=404, detail="Credentials not found")

    # Авторизация в Vault прошла → username подтверждён
    request.state.actor = data.username
    _audit_ok(request)
    return {"success": True, "data": creds}


@router.post("/verify-admin")
def verify_admin_api(data: VerifyAdminRequest, request: Request):
    client_ip, _ = _ctx(request)
    set_audit_context(request, "verify_admin", username=data.username)

    verify_admin_password(
        username=data.username,
        master_password=data.master_password,
        client_ip=client_ip,
    )

    request.state.actor = data.username
    _audit_ok(request)
    return {"success": True}


@router.post("/upsert")
def upsert_credentials_api(data: UpsertCredentialsRequest, request: Request):
    set_audit_context(
        request,
        "upsert_credentials",
        server_id=data.server_id,
        port=data.port,
        username=data.username,
    )

    try:
        vault_path = upsert_credentials(
            server_id=data.server_id,
            port=data.port,
            username=data.username,
            password=data.password,
        )
    except Exception as e:
        logger.error(
            "upsert_credentials failed server_id=%s port=%s: %s",
            data.server_id,
            data.port,
            e,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal server error")

    request.state.audit_fields["vault_path"] = vault_path
    _audit_ok(request)
    return {"success": True, "data": {"vault_path": vault_path}}


@router.post("/rotate")
def rotate_credentials_api(data: RotateCredentialsRequest, request: Request):
    client_ip, _ = _ctx(request)
    set_audit_context(
        request,
        "rotate_credentials",
        server_id=data.server_id,
        port=data.ssh_port,
        username=data.username,
    )

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
            _ctx(request)[1],
        )
        return JSONResponse(
            status_code=422,
            content={
                "error_code": "ROTATE_FAILED",
                "detail": "Credential rotation failed",
            },
        )

    request.state.actor = data.username
    _audit_ok(request)
    return {"success": True}


@router.post("/export-all")
def export_all_credentials_api(data: ExportAllCredentialsRequest, request: Request):
    client_ip, _ = _ctx(request)
    set_audit_context(request, "export_all_credentials", username=data.username)

    try:
        entries = export_all_credentials(
            username=data.username,
            master_password=data.master_password,
            client_ip=client_ip,
        )
    except (TooManyLoginAttempts, InvalidMasterPassword):
        # Обрабатываются глобальными хендлерами (429 / 403)
        raise
    except Exception as e:
        logger.error("export_all_credentials failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

    request.state.actor = data.username
    request.state.audit_fields["count"] = len(entries)
    _audit_ok(request)
    return {"success": True, "data": entries}
