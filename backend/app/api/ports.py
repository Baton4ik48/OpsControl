from fastapi import APIRouter, HTTPException
from app.services.db.ports import (
    load_ports,
    create_port,
    delete_port,
    update_port,
    update_vault_path,
    report_port_result
)

router = APIRouter(prefix="/ports", tags=["ports"])


def ensure_found(affected: int, entity: str):
    if affected == 0:
        raise HTTPException(status_code=404, detail=f"{entity} not found")


@router.get("/by-server/{server_id}")
def get_ports(server_id: int):
    return {
        "success": True,
        "data": load_ports(server_id)
    }


@router.post("")
def create_port_api(server_id: int, port: int):
    create_port(server_id, port)
    return {"success": True, "data": None}


@router.put("")
def update_port_api(server_id: int, old_port: int, new_port: int):
    affected = update_port(server_id, old_port, new_port)
    ensure_found(affected, "Port")
    return {"success": True, "data": None}


@router.delete("/{server_id}/{port}")
def delete_port_api(server_id: int, port: int):
    affected = delete_port(server_id, port)
    ensure_found(affected, "Port")
    return {"success": True, "data": None}


@router.put("/vault-path")
def update_vault_path_api(server_id: int, port: int, vault_path: str):
    affected = update_vault_path(server_id, port, vault_path)
    ensure_found(affected, "Credentials")
    return {"success": True, "data": None}


@router.post("/result")
def report_port_result_api(server_id: int, port: int, ok: bool):
    affected = report_port_result(server_id, port, ok)
    ensure_found(affected, "Port")
    return {"success": True, "data": None}