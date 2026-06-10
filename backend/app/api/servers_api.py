import ipaddress
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from app.services.db.servers_db import (
    load_servers,
    create_server,
    delete_server,
    update_server,
    update_server_comment,
)

router = APIRouter(prefix="/servers", tags=["servers"])

_DOMAIN_RE = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
)


def _validate_host(value: str) -> str:
    try:
        ipaddress.ip_address(value)
        return value
    except ValueError:
        pass
    if _DOMAIN_RE.match(value):
        return value
    raise ValueError(f"'{value}' не является корректным IP-адресом или доменным именем")


ALLOWED_DEVICE_TYPES = {"linux", "windows", "nateks", "natex", "cisco", "xclarity"}


class _ServerBase(BaseModel):
    name: str
    ip: str
    device_type: str = "linux"

    @field_validator("ip")
    @classmethod
    def validate_ip(cls, v):
        return _validate_host(v.strip())

    @field_validator("device_type")
    @classmethod
    def validate_device_type(cls, v):
        if v not in ALLOWED_DEVICE_TYPES:
            raise ValueError(f"device_type must be one of: {ALLOWED_DEVICE_TYPES}")
        return v


class ServerCreate(_ServerBase):
    branch_id: int


class ServerUpdate(_ServerBase):
    pass


class CommentUpdate(BaseModel):
    comment: str


def ensure_found(affected: int, entity: str):
    if affected == 0:
        raise HTTPException(status_code=404, detail=f"{entity} not found")


@router.get("/by-branch/{branch_id}")
def get_servers(branch_id: int):
    rows = load_servers(branch_id)
    return {
        "success": True,
        "data": [
            {"id": r[0], "name": r[1], "ip": r[2], "device_type": r[3]} for r in rows
        ],
    }


@router.post("")
def create_server_api(payload: ServerCreate):
    new_id = create_server(
        payload.branch_id,
        payload.name,
        payload.ip,
        payload.device_type,
    )
    return {"success": True, "data": {"id": new_id}}


@router.put("/{server_id}")  # атомарный
def update_server_api(server_id: int, payload: ServerUpdate):
    affected = update_server(
        server_id,
        payload.name,
        payload.ip,
        payload.device_type,
    )
    ensure_found(affected, "Server")
    return {"success": True, "data": None}


@router.put("/{server_id}/comment")
def update_server_comment_api(server_id: int, payload: CommentUpdate):
    affected = update_server_comment(server_id, payload.comment)
    ensure_found(affected, "Server")
    return {"success": True, "data": None}


@router.delete("/{server_id}")
def delete_server_api(server_id: int):
    affected = delete_server(server_id)
    ensure_found(affected, "Server")
    return {"success": True, "data": None}
