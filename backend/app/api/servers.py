from fastapi import APIRouter, HTTPException
from app.services.db.servers import (
    load_servers,
    create_server,
    delete_server,
    update_server_name,
    update_server_ip
)

router = APIRouter(prefix="/servers", tags=["servers"])


def ensure_found(affected: int, entity: str):
    if affected == 0:
        raise HTTPException(status_code=404, detail=f"{entity} not found")


@router.get("/by-branch/{branch_id}")
def get_servers(branch_id: int):
    rows = load_servers(branch_id)
    return {
        "success": True,
        "data": [{"id": r[0], "name": r[1], "ip": r[2]} for r in rows]
    }


@router.post("")
def create_server_api(branch_id: int, name: str, ip: str):
    new_id = create_server(branch_id, name, ip)
    return {"success": True, "data": {"id": new_id}}


@router.put("/{server_id}/name")
def update_server_name_api(server_id: int, new_name: str):
    affected = update_server_name(server_id, new_name)
    ensure_found(affected, "Server")
    return {"success": True, "data": None}


@router.put("/{server_id}/ip")
def update_server_ip_api(server_id: int, new_ip: str):
    affected = update_server_ip(server_id, new_ip)
    ensure_found(affected, "Server")
    return {"success": True, "data": None}


@router.delete("/{server_id}")
def delete_server_api(server_id: int):
    affected = delete_server(server_id)
    ensure_found(affected, "Server")
    return {"success": True, "data": None}