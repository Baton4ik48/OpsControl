import os
import requests
import pytest

BASE_URL = os.getenv("BACKEND_URL", "http://backend:8000") + "/api"


@pytest.mark.e2e
def test_get_tree_returns_list():
    resp = requests.get(f"{BASE_URL}/tree")

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)


@pytest.mark.e2e
def test_get_tree_contains_branch():
    branch_resp = requests.post(
        f"{BASE_URL}/branches", json={"name": "e2e-tree-branch"}
    )
    branch_id = branch_resp.json()["data"]["id"]

    tree = requests.get(f"{BASE_URL}/tree").json()["data"]
    ids = [b["id"] for b in tree]
    assert branch_id in ids

    requests.delete(f"{BASE_URL}/branches/{branch_id}")


@pytest.mark.e2e
def test_get_tree_nested_structure():
    """Ветка → сервер → порт — правильная вложенность в ответе"""
    branch_resp = requests.post(f"{BASE_URL}/branches", json={"name": "e2e-tree-full"})
    branch_id = branch_resp.json()["data"]["id"]

    server_resp = requests.post(
        f"{BASE_URL}/servers",
        json={
            "branch_id": branch_id,
            "name": "tree-srv",
            "ip": "10.3.0.1",
            "device_type": "linux",
        },
    )
    server_id = server_resp.json()["data"]["id"]

    requests.post(f"{BASE_URL}/ports/{server_id}/22")

    tree = requests.get(f"{BASE_URL}/tree").json()["data"]

    branch = next(b for b in tree if b["id"] == branch_id)
    assert branch["name"] == "e2e-tree-full"
    assert isinstance(branch["servers"], list)

    server = next(s for s in branch["servers"] if s["id"] == server_id)
    assert server["name"] == "tree-srv"
    assert server["ip"] == "10.3.0.1"
    assert isinstance(server["ports"], list)

    port = next(p for p in server["ports"] if p["port"] == 22)
    assert "last_success" in port
    assert "last_failure" in port
    assert "has_credentials" in port

    requests.delete(f"{BASE_URL}/ports/{server_id}/22")
    requests.delete(f"{BASE_URL}/servers/{server_id}")
    requests.delete(f"{BASE_URL}/branches/{branch_id}")
