from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, IPvAnyAddress

from app.services.db.servers import (
    load_servers,
    create_server,
    delete_server,
    update_server
)

router = APIRouter(prefix="/servers", tags=["servers"])


# ==========================
# Pydantic models
# ==========================

class ServerCreate(BaseModel):
    branch_id: int
    name: str
    ip: IPvAnyAddress


class ServerUpdate(BaseModel):
    name: str
    ip: IPvAnyAddress


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
        "data": [{"id": r[0], "name": r[1], "ip": r[2]} for r in rows]
    }


# ==========================
# CREATE
# ==========================

@router.post("")
def create_server_api(payload: ServerCreate):
    new_id = create_server(
        payload.branch_id,
        payload.name,
        str(payload.ip)
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
        str(payload.ip)
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