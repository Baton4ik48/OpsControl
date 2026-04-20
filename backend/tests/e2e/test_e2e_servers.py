import os
import requests
import pytest

BASE_URL = os.getenv("BACKEND_URL", "http://backend:8000") + "/api"


@pytest.fixture(scope="module")
def branch_id():
    resp = requests.post(f"{BASE_URL}/branches", json={"name": "e2e-servers-branch"})
    branch_id = resp.json()["data"]["id"]
    yield branch_id
    requests.delete(f"{BASE_URL}/branches/{branch_id}")


@pytest.fixture
def server(branch_id):
    resp = requests.post(
        f"{BASE_URL}/servers",
        json={
            "branch_id": branch_id,
            "name": "e2e-srv",
            "ip": "10.0.0.1",
            "device_type": "linux",
        },
    )
    server_id = resp.json()["data"]["id"]
    yield server_id
    requests.delete(f"{BASE_URL}/servers/{server_id}")


# ============================================
# GET /api/servers/by-branch/{id}
# ============================================


@pytest.mark.e2e
def test_get_servers_returns_list(branch_id):
    resp = requests.get(f"{BASE_URL}/servers/by-branch/{branch_id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)


@pytest.mark.e2e
def test_get_servers_contains_created(branch_id, server):
    resp = requests.get(f"{BASE_URL}/servers/by-branch/{branch_id}")

    ids = [s["id"] for s in resp.json()["data"]]
    assert server in ids


# ============================================
# POST /api/servers
# ============================================


@pytest.mark.e2e
def test_create_server_returns_id(branch_id):
    resp = requests.post(
        f"{BASE_URL}/servers",
        json={
            "branch_id": branch_id,
            "name": "e2e-create",
            "ip": "10.0.0.2",
            "device_type": "linux",
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["data"]["id"], int)

    requests.delete(f"{BASE_URL}/servers/{body['data']['id']}")


@pytest.mark.e2e
def test_create_server_invalid_ip(branch_id):
    resp = requests.post(
        f"{BASE_URL}/servers",
        json={
            "branch_id": branch_id,
            "name": "bad",
            "ip": "not-an-ip",
            "device_type": "linux",
        },
    )

    assert resp.status_code == 422


@pytest.mark.e2e
def test_create_server_invalid_device_type(branch_id):
    resp = requests.post(
        f"{BASE_URL}/servers",
        json={
            "branch_id": branch_id,
            "name": "bad",
            "ip": "10.0.0.3",
            "device_type": "unknown",
        },
    )

    assert resp.status_code == 422


# ============================================
# PUT /api/servers/{id}
# ============================================


@pytest.mark.e2e
def test_update_server(branch_id, server):
    resp = requests.put(
        f"{BASE_URL}/servers/{server}",
        json={"name": "e2e-srv-updated", "ip": "10.0.0.99", "device_type": "cisco"},
    )

    assert resp.status_code == 200
    assert resp.json()["success"] is True

    servers = requests.get(f"{BASE_URL}/servers/by-branch/{branch_id}").json()["data"]
    updated = next(s for s in servers if s["id"] == server)
    assert updated["name"] == "e2e-srv-updated"
    assert updated["ip"] == "10.0.0.99"
    assert updated["device_type"] == "cisco"


@pytest.mark.e2e
def test_update_server_not_found():
    resp = requests.put(
        f"{BASE_URL}/servers/999999",
        json={"name": "nope", "ip": "1.2.3.4", "device_type": "linux"},
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Server not found"


# ============================================
# DELETE /api/servers/{id}
# ============================================


@pytest.mark.e2e
def test_delete_server(branch_id):
    create_resp = requests.post(
        f"{BASE_URL}/servers",
        json={
            "branch_id": branch_id,
            "name": "e2e-to-delete",
            "ip": "10.0.0.5",
            "device_type": "linux",
        },
    )
    server_id = create_resp.json()["data"]["id"]

    resp = requests.delete(f"{BASE_URL}/servers/{server_id}")
    assert resp.status_code == 200

    servers = requests.get(f"{BASE_URL}/servers/by-branch/{branch_id}").json()["data"]
    assert not any(s["id"] == server_id for s in servers)


@pytest.mark.e2e
def test_delete_server_not_found():
    resp = requests.delete(f"{BASE_URL}/servers/999999")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Server not found"
