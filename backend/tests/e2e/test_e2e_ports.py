import os
import requests
import pytest

BASE_URL = os.getenv("BACKEND_URL", "http://backend:8000") + "/api"


@pytest.fixture(scope="module")
def server_id():
    branch_resp = requests.post(
        f"{BASE_URL}/branches", json={"name": "e2e-ports-branch"}
    )
    branch_id = branch_resp.json()["data"]["id"]

    server_resp = requests.post(
        f"{BASE_URL}/servers",
        json={
            "branch_id": branch_id,
            "name": "e2e-ports-srv",
            "ip": "10.1.0.1",
            "device_type": "linux",
        },
    )
    server_id = server_resp.json()["data"]["id"]

    yield server_id

    requests.delete(f"{BASE_URL}/servers/{server_id}")
    requests.delete(f"{BASE_URL}/branches/{branch_id}")


@pytest.fixture
def port(server_id):
    requests.post(f"{BASE_URL}/ports/{server_id}/2222")
    yield 2222
    requests.delete(f"{BASE_URL}/ports/{server_id}/2222")


# ============================================
# GET /api/ports/by-server/{id}
# ============================================


@pytest.mark.e2e
def test_get_ports_returns_list(server_id):
    resp = requests.get(f"{BASE_URL}/ports/by-server/{server_id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)


@pytest.mark.e2e
def test_get_ports_contains_created(server_id, port):
    resp = requests.get(f"{BASE_URL}/ports/by-server/{server_id}")

    ports = [p["port"] for p in resp.json()["data"]]
    assert 2222 in ports


# ============================================
# POST /api/ports/{server_id}/{port}
# ============================================


@pytest.mark.e2e
def test_create_port(server_id):
    resp = requests.post(f"{BASE_URL}/ports/{server_id}/3333")

    assert resp.status_code == 200
    assert resp.json()["success"] is True

    requests.delete(f"{BASE_URL}/ports/{server_id}/3333")


# ============================================
# PUT /api/ports/{server_id}/{old_port}
# ============================================


@pytest.mark.e2e
def test_update_port_number(server_id):
    requests.post(f"{BASE_URL}/ports/{server_id}/4444")

    resp = requests.put(
        f"{BASE_URL}/ports/{server_id}/4444",
        json={"new_port": 4445},
    )
    assert resp.status_code == 200

    ports = [
        p["port"]
        for p in requests.get(f"{BASE_URL}/ports/by-server/{server_id}").json()["data"]
    ]
    assert 4445 in ports
    assert 4444 not in ports

    requests.delete(f"{BASE_URL}/ports/{server_id}/4445")


@pytest.mark.e2e
def test_update_port_migrates_vault_path(server_id):
    """vault_path must survive a port number change."""
    requests.post(f"{BASE_URL}/ports/{server_id}/8880")
    requests.put(
        f"{BASE_URL}/ports/{server_id}/8880/vault-path",
        json={"vault_path": "credentials/servers/e2e/8880"},
    )

    resp = requests.put(
        f"{BASE_URL}/ports/{server_id}/8880",
        json={"new_port": 8881},
    )
    assert resp.status_code == 200

    ports = requests.get(f"{BASE_URL}/ports/by-server/{server_id}").json()["data"]
    assert any(p["port"] == 8881 for p in ports)
    assert all(p["port"] != 8880 for p in ports)

    requests.delete(f"{BASE_URL}/ports/{server_id}/8881")


@pytest.mark.e2e
def test_update_port_conflict_returns_409(server_id):
    """Changing to an already-occupied port must return 409; original credentials survive."""
    requests.post(f"{BASE_URL}/ports/{server_id}/9990")
    requests.post(f"{BASE_URL}/ports/{server_id}/9991")
    requests.put(
        f"{BASE_URL}/ports/{server_id}/9990/vault-path",
        json={"vault_path": "credentials/servers/e2e/9990"},
    )

    resp = requests.put(
        f"{BASE_URL}/ports/{server_id}/9990",
        json={"new_port": 9991},
    )
    assert resp.status_code == 409

    requests.delete(f"{BASE_URL}/ports/{server_id}/9990")
    requests.delete(f"{BASE_URL}/ports/{server_id}/9991")


# ============================================
# PUT /api/ports/{server_id}/{port}/vault-path
# ============================================


@pytest.mark.e2e
def test_update_vault_path_set(server_id, port):
    resp = requests.put(
        f"{BASE_URL}/ports/{server_id}/2222/vault-path",
        json={"vault_path": "credentials/servers/1/2222"},
    )

    assert resp.status_code == 200
    assert resp.json()["success"] is True


@pytest.mark.e2e
def test_update_vault_path_clear(server_id, port):
    requests.put(
        f"{BASE_URL}/ports/{server_id}/2222/vault-path",
        json={"vault_path": "credentials/servers/1/2222"},
    )

    resp = requests.put(
        f"{BASE_URL}/ports/{server_id}/2222/vault-path",
        json={"vault_path": ""},
    )
    assert resp.status_code == 200


# ============================================
# POST /api/ports/{server_id}/{port}/result
# ============================================


@pytest.mark.e2e
def test_report_port_result_ok(server_id, port):
    resp = requests.post(
        f"{BASE_URL}/ports/{server_id}/2222/result",
        json={"ok": True},
    )

    assert resp.status_code == 200

    ports = requests.get(f"{BASE_URL}/ports/by-server/{server_id}").json()["data"]
    row = next(p for p in ports if p["port"] == 2222)
    assert row["last_success"] is not None


@pytest.mark.e2e
def test_report_port_result_fail(server_id, port):
    resp = requests.post(
        f"{BASE_URL}/ports/{server_id}/2222/result",
        json={"ok": False},
    )

    assert resp.status_code == 200

    ports = requests.get(f"{BASE_URL}/ports/by-server/{server_id}").json()["data"]
    row = next(p for p in ports if p["port"] == 2222)
    assert row["last_failure"] is not None


# ============================================
# DELETE /api/ports/{server_id}/{port}/credentials
# ============================================


@pytest.mark.e2e
def test_delete_credentials(server_id, port):
    requests.put(
        f"{BASE_URL}/ports/{server_id}/2222/vault-path",
        json={"vault_path": "credentials/servers/1/2222"},
    )

    resp = requests.delete(f"{BASE_URL}/ports/{server_id}/2222/credentials")
    assert resp.status_code == 200


# ============================================
# DELETE /api/ports/{server_id}/{port}
# ============================================


@pytest.mark.e2e
def test_delete_port(server_id):
    requests.post(f"{BASE_URL}/ports/{server_id}/5555")

    resp = requests.delete(f"{BASE_URL}/ports/{server_id}/5555")
    assert resp.status_code == 200

    ports = [
        p["port"]
        for p in requests.get(f"{BASE_URL}/ports/by-server/{server_id}").json()["data"]
    ]
    assert 5555 not in ports


@pytest.mark.e2e
def test_delete_port_not_found(server_id):
    resp = requests.delete(f"{BASE_URL}/ports/{server_id}/999999")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Port not found"
