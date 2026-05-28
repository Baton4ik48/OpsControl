from fastapi import APIRouter, HTTPException
from psycopg2 import errors as pg_errors
from app.services.db.ports_db import (
    load_ports,
    create_port,
    delete_port,
    update_port,
    update_vault_path,
    report_port_result,
    delete_credentials,
    update_port_comment,
)
from pydantic import BaseModel

router = APIRouter(prefix="/ports", tags=["ports"])


def ensure_found(affected: int, entity: str):
    if affected == 0:
        raise HTTPException(status_code=404, detail=f"{entity} not found")


class PortUpdate(BaseModel):
    new_port: int


class VaultPathUpdate(BaseModel):
    vault_path: str


class PortResult(BaseModel):
    ok: bool


class CommentUpdate(BaseModel):
    comment: str


# ==========================
# READ
# ==========================


@router.get("/by-server/{server_id}")
def get_ports(server_id: int):
    return {"success": True, "data": load_ports(server_id)}


# ==========================
# CREATE
# ==========================


@router.post("/{server_id}/{port}")
def create_port_api(server_id: int, port: int):
    create_port(server_id, port)
    return {"success": True, "data": None}


# ==========================
# UPDATE PORT NUMBER
# ==========================


@router.put("/{server_id}/{old_port}")
def update_port_api(server_id: int, old_port: int, payload: PortUpdate):
    try:
        affected = update_port(server_id, old_port, payload.new_port)
    except pg_errors.UniqueViolation:
        raise HTTPException(
            status_code=409, detail="Port already exists for this server"
        )
    ensure_found(affected, "Port")
    return {"success": True, "data": None}


# ==========================
# UPDATE VAULT PATH
# ==========================


@router.put("/{server_id}/{port}/vault-path")
def update_vault_path_api(server_id: int, port: int, payload: VaultPathUpdate):
    affected = update_vault_path(server_id, port, payload.vault_path)
    ensure_found(affected, "Credentials")
    return {"success": True, "data": None}


# ==========================
# DELETE
# ==========================


@router.delete("/{server_id}/{port}")
def delete_port_api(server_id: int, port: int):
    affected = delete_port(server_id, port)
    ensure_found(affected, "Port")
    return {"success": True, "data": None}


@router.delete("/{server_id}/{port}/credentials")
def delete_credentials_api(server_id: int, port: int):
    delete_credentials(server_id, port)
    return {"success": True, "data": None}


# ==========================
# UPDATE COMMENT
# ==========================


@router.put("/{server_id}/{port}/comment")
def update_port_comment_api(server_id: int, port: int, payload: CommentUpdate):
    affected = update_port_comment(server_id, port, payload.comment)
    ensure_found(affected, "Port")
    return {"success": True, "data": None}


# ==========================
# REPORT RESULT
# ==========================


@router.post("/{server_id}/{port}/result")
def report_port_result_api(server_id: int, port: int, payload: PortResult):
    affected = report_port_result(server_id, port, payload.ok)
    ensure_found(affected, "Port")
    return {"success": True, "data": None}
