import os
import requests
import pytest

BASE_URL = os.getenv("BACKEND_URL", "http://backend:8000") + "/api"

ADMIN_USER = os.getenv("VAULT_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("VAULT_ADMIN_PASSWORD", "admin")


@pytest.fixture(scope="module")
def server_id():
    branch_resp = requests.post(
        f"{BASE_URL}/branches", json={"name": "e2e-creds-branch"}
    )
    branch_id = branch_resp.json()["data"]["id"]

    server_resp = requests.post(
        f"{BASE_URL}/servers",
        json={
            "branch_id": branch_id,
            "name": "e2e-creds-srv",
            "ip": "10.2.0.1",
            "device_type": "linux",
        },
    )
    server_id = server_resp.json()["data"]["id"]

    requests.post(f"{BASE_URL}/ports/{server_id}/22")

    yield server_id

    requests.delete(f"{BASE_URL}/ports/{server_id}/22")
    requests.delete(f"{BASE_URL}/servers/{server_id}")
    requests.delete(f"{BASE_URL}/branches/{branch_id}")


@pytest.mark.e2e
def test_verify_admin_success():
    resp = requests.post(
        f"{BASE_URL}/credentials/verify-admin",
        json={"username": ADMIN_USER, "master_password": ADMIN_PASSWORD},
    )

    assert resp.status_code == 200
    assert resp.json()["success"] is True


@pytest.mark.e2e
def test_verify_admin_invalid_password():
    resp = requests.post(
        f"{BASE_URL}/credentials/verify-admin",
        json={"username": ADMIN_USER, "master_password": "wrong-password"},
    )

    assert resp.status_code == 403
    assert resp.json()["error_code"] == "INVALID_MASTER_PASSWORD"


@pytest.mark.e2e
def test_upsert_credentials(server_id):
    resp = requests.post(
        f"{BASE_URL}/credentials/upsert",
        json={
            "server_id": server_id,
            "port": 22,
            "username": "root",
            "password": "secret123",
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "vault_path" in body["data"]
    assert body["data"]["vault_path"] == f"credentials/servers/{server_id}/22"


@pytest.mark.e2e
def test_show_credentials_success(server_id):
    requests.post(
        f"{BASE_URL}/credentials/upsert",
        json={
            "server_id": server_id,
            "port": 22,
            "username": "root",
            "password": "secret123",
        },
    )

    resp = requests.post(
        f"{BASE_URL}/credentials/show",
        json={
            "server_id": server_id,
            "port": 22,
            "username": ADMIN_USER,
            "master_password": ADMIN_PASSWORD,
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["username"] == "root"
    assert body["data"]["password"] == "secret123"


@pytest.mark.e2e
def test_show_credentials_invalid_password(server_id):
    resp = requests.post(
        f"{BASE_URL}/credentials/show",
        json={
            "server_id": server_id,
            "port": 22,
            "username": ADMIN_USER,
            "master_password": "wrong",
        },
    )

    assert resp.status_code == 403
    assert resp.json()["error_code"] == "INVALID_MASTER_PASSWORD"


@pytest.mark.e2e
def test_show_credentials_not_found(server_id):
    resp = requests.post(
        f"{BASE_URL}/credentials/show",
        json={
            "server_id": server_id,
            "port": 9999,
            "username": ADMIN_USER,
            "master_password": ADMIN_PASSWORD,
        },
    )

    assert resp.status_code == 404


@pytest.mark.e2e
def test_rotate_credentials_updates_password(server_id):
    requests.post(
        f"{BASE_URL}/credentials/upsert",
        json={
            "server_id": server_id,
            "port": 22,
            "username": "root",
            "password": "old-password",
        },
    )

    rotate_resp = requests.post(
        f"{BASE_URL}/credentials/rotate",
        json={
            "server_id": server_id,
            "ssh_port": 22,
            "new_password": "new-password",
            "username": ADMIN_USER,
            "master_password": ADMIN_PASSWORD,
            "mnemonic": "e2e test mnemonic",
        },
    )
    assert rotate_resp.status_code == 200
    assert rotate_resp.json()["success"] is True

    show_resp = requests.post(
        f"{BASE_URL}/credentials/show",
        json={
            "server_id": server_id,
            "port": 22,
            "username": ADMIN_USER,
            "master_password": ADMIN_PASSWORD,
        },
    )
    data = show_resp.json()["data"]
    assert data["password"] == "new-password"
    assert data["mnemonic"] == "e2e test mnemonic"
