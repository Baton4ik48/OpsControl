from fastapi import APIRouter, HTTPException
from app.services.db.branches import (
    load_branches,
    create_branch,
    delete_branch,
    update_branch
)

router = APIRouter(prefix="/branches", tags=["branches"])


def ensure_found(affected: int, entity: str):
    if affected == 0:
        raise HTTPException(status_code=404, detail=f"{entity} not found")


@router.get("")
def get_branches():
    rows = load_branches()
    return {
        "success": True,
        "data": [{"id": r[0], "name": r[1]} for r in rows]
    }


@router.post("")
def create_branch_api(name: str):
    new_id = create_branch(name)
    return {
        "success": True,
        "data": {"id": new_id}
    }


@router.put("/{branch_id}")
def update_branch_api(branch_id: int, new_name: str):
    affected = update_branch(branch_id, new_name)
    ensure_found(affected, "Branch")
    return {"success": True, "data": None}


@router.delete("/{branch_id}")
def delete_branch_api(branch_id: int):
    affected = delete_branch(branch_id)
    ensure_found(affected, "Branch")
    return {"success": True, "data": None}