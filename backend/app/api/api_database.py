from fastapi import APIRouter, HTTPException
from app.services.postgres import (
    load_tree,
    load_branches,
    load_servers,
    load_ports,
    update_server_name,
    update_server_ip,
    report_port_result,
)

router = APIRouter(prefix="/api", tags=["database"])


@router.get("/tree")
def get_tree():
    rows = load_tree()

    tree = {}
    for r in rows:
        bid = r[0]
        if bid not in tree:
            tree[bid] = {
                "id": bid,
                "name": r[1],
                "servers": {}
            }

        sid = r[2]
        if sid not in tree[bid]["servers"]:
            tree[bid]["servers"][sid] = {
                "id": sid,
                "name": r[3],
                "ip": r[4],
                "ports": []
            }
        if r[5] is not None:
            tree[bid]["servers"][sid]["ports"].append({
                "port": r[5],
                "last_success": r[6],
                "last_failure": r[7],
                
                "has_credentials": r[8] is not None,
                "credentials_updated_at": r[9],
            })
    return {
        "success": True,
        "data": [
            {
                "id": b["id"],
                "name": b["name"],
                "servers": list(b["servers"].values())
            }
            for b in tree.values()
        ]
    }


def ensure_found(affected: int, entity: str):
    if affected == 0:
        raise HTTPException(
            status_code=404,
            detail=f"{entity} not found"
        )


@router.get("/branches")
def get_branches():
    rows = load_branches()
    return {
        "success": True,
        "data": [{"id": r[0], "name": r[1]} for r in rows]
    }


@router.get("/branches/{branch_id}/servers")
def get_servers(branch_id: int):
    rows = load_servers(branch_id)
    return {
        "success": True,
        "data": [{"id": r[0], "name": r[1], "ip": r[2]} for r in rows]
    }


@router.get("/servers/{server_id}/ports")
def get_ports(server_id: int):
    return {
        "success": True,
        "data": load_ports(server_id)
    }


@router.put("/servers/{server_id}/name")
def update_server_name_api(server_id: int, new_name: str):
    affected = update_server_name(server_id, new_name)
    ensure_found(affected, "Server")
    return {"success": True}


@router.put("/servers/{server_id}/ip")
def update_server_ip_api(server_id: int, new_ip: str):
    affected = update_server_ip(server_id, new_ip)
    ensure_found(affected, "Server")
    return {"success": True}


@router.post("/ports/result")
def report_port_result_api(server_id: int, port: int, ok: bool):
    affected = report_port_result(server_id, port, ok)
    ensure_found(affected, "Port")
    return {"success": True}



