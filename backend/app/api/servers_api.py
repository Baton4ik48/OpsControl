import ipaddress
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from app.services.db.servers_db import (
    load_servers,
    create_server,
    delete_server,
    update_server,
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


# ==========================
# Pydantic models
# ==========================

ALLOWED_DEVICE_TYPES = {"linux", "windows", "nateks", "natex", "cisco", "xclarity"}


class ServerCreate(BaseModel):
    branch_id: int
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


class ServerUpdate(BaseModel):
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


def ensure_found(affected: int, entity: str):
    if affected == 0:
        raise HTTPException(status_code=404, detail=f"{entity} not found")


# ==========================
# READ
# ==========================


@router.get("/by-branch/{branch_id}")
def get_servers(branch_id: int):
    rows = load_servers(branch_id)
    return {
        "success": True,
        "data": [
            {"id": r[0], "name": r[1], "ip": r[2], "device_type": r[3]} for r in rows
        ],
    }


# ==========================
# CREATE
# ==========================


@router.post("")
def create_server_api(payload: ServerCreate):
    new_id = create_server(
        payload.branch_id,
        payload.name,
        payload.ip,
        payload.device_type,
    )
    return {"success": True, "data": {"id": new_id}}


# ==========================
# UPDATE (атомарный)
# ==========================


@router.put("/{server_id}")
def update_server_api(server_id: int, payload: ServerUpdate):
    affected = update_server(
        server_id,
        payload.name,
        payload.ip,
        payload.device_type,
    )
    ensure_found(affected, "Server")
    return {"success": True, "data": None}


# ==========================
# DELETE
# ==========================


@router.delete("/{server_id}")
def delete_server_api(server_id: int):
    affected = delete_server(server_id)
    ensure_found(affected, "Server")
    return {"success": True, "data": None}
