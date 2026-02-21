from fastapi import APIRouter
from app.services.db.tree import load_tree

router = APIRouter(
    prefix="/tree",
    tags=["tree"]
)

@router.get("")
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
                "vault_path": r[10]
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