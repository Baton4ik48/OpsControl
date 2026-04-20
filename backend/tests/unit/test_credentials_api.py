from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.api.credentials_api import router
from app.services.credentials import (
    InvalidMasterPassword,
    CredentialsNotFound,
    TooManyLoginAttempts,
    RotateError,
)

app = FastAPI()
app.include_router(router)
client = TestClient(app, raise_server_exceptions=False)


# ============================================
# POST /credentials/verify-admin
# ============================================


def test_verify_admin_success():
    with patch("app.api.credentials_api.verify_admin_password"):
        resp = client.post(
            "/credentials/verify-admin",
            json={"username": "admin", "master_password": "correct"},
        )

    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_verify_admin_invalid_password():
    with patch(
        "app.api.credentials_api.verify_admin_password",
        side_effect=InvalidMasterPassword(),
    ):
        resp = client.post(
            "/credentials/verify-admin",
            json={"username": "admin", "master_password": "wrong"},
        )

    assert resp.status_code == 403
    assert resp.json()["error_code"] == "INVALID_MASTER_PASSWORD"


def test_verify_admin_throttled():
    with patch(
        "app.api.credentials_api.verify_admin_password",
        side_effect=TooManyLoginAttempts(retry_after_seconds=60),
    ):
        resp = client.post(
            "/credentials/verify-admin",
            json={"username": "admin", "master_password": "any"},
        )

    assert resp.status_code == 429
    assert resp.json()["error_code"] == "LOGIN_THROTTLED"
    assert resp.json()["retry_after"] == 60


# ============================================
# POST /credentials/show
# ============================================


def test_show_credentials_success():
    creds = {"username": "root", "password": "secret", "mnemonic": ""}

    with patch("app.api.credentials_api.show_credentials", return_value=creds):
        resp = client.post(
            "/credentials/show",
            json={
                "server_id": 1,
                "port": 22,
                "username": "admin",
                "master_password": "correct",
            },
        )

    assert resp.status_code == 200
    assert resp.json()["success"] is True
    assert resp.json()["data"] == creds


def test_show_credentials_invalid_password():
    with patch(
        "app.api.credentials_api.show_credentials",
        side_effect=InvalidMasterPassword(),
    ):
        resp = client.post(
            "/credentials/show",
            json={
                "server_id": 1,
                "port": 22,
                "username": "admin",
                "master_password": "wrong",
            },
        )

    assert resp.status_code == 403
    assert resp.json()["error_code"] == "INVALID_MASTER_PASSWORD"


def test_show_credentials_throttled():
    with patch(
        "app.api.credentials_api.show_credentials",
        side_effect=TooManyLoginAttempts(retry_after_seconds=30),
    ):
        resp = client.post(
            "/credentials/show",
            json={
                "server_id": 1,
                "port": 22,
                "username": "admin",
                "master_password": "any",
            },
        )

    assert resp.status_code == 429
    assert resp.json()["error_code"] == "LOGIN_THROTTLED"
    assert resp.json()["retry_after"] == 30


def test_show_credentials_not_found():
    with patch(
        "app.api.credentials_api.show_credentials",
        side_effect=CredentialsNotFound(),
    ):
        resp = client.post(
            "/credentials/show",
            json={
                "server_id": 1,
                "port": 22,
                "username": "admin",
                "master_password": "correct",
            },
        )

    assert resp.status_code == 404


# ============================================
# POST /credentials/upsert
# ============================================


def test_upsert_credentials_success():
    with patch(
        "app.api.credentials_api.upsert_credentials",
        return_value="credentials/servers/1/22",
    ):
        resp = client.post(
            "/credentials/upsert",
            json={"server_id": 1, "port": 22, "username": "root", "password": "pass"},
        )

    assert resp.status_code == 200
    assert resp.json()["success"] is True
    assert resp.json()["data"]["vault_path"] == "credentials/servers/1/22"


def test_upsert_credentials_server_error():
    with patch(
        "app.api.credentials_api.upsert_credentials",
        side_effect=Exception("vault unreachable"),
    ):
        resp = client.post(
            "/credentials/upsert",
            json={"server_id": 1, "port": 22, "username": "root", "password": "pass"},
        )

    assert resp.status_code == 500


# ============================================
# POST /credentials/rotate
# ============================================


def test_rotate_credentials_success():
    with patch("app.api.credentials_api.rotate_credentials"):
        resp = client.post(
            "/credentials/rotate",
            json={
                "server_id": 1,
                "ssh_port": 22,
                "new_password": "newpass",
                "username": "admin",
                "master_password": "correct",
                "mnemonic": "",
            },
        )

    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_rotate_credentials_invalid_password():
    with patch(
        "app.api.credentials_api.rotate_credentials",
        side_effect=InvalidMasterPassword(),
    ):
        resp = client.post(
            "/credentials/rotate",
            json={
                "server_id": 1,
                "ssh_port": 22,
                "new_password": "newpass",
                "username": "admin",
                "master_password": "wrong",
                "mnemonic": "",
            },
        )

    assert resp.status_code == 403
    assert resp.json()["error_code"] == "INVALID_MASTER_PASSWORD"


def test_rotate_credentials_throttled():
    with patch(
        "app.api.credentials_api.rotate_credentials",
        side_effect=TooManyLoginAttempts(retry_after_seconds=120),
    ):
        resp = client.post(
            "/credentials/rotate",
            json={
                "server_id": 1,
                "ssh_port": 22,
                "new_password": "newpass",
                "username": "admin",
                "master_password": "any",
                "mnemonic": "",
            },
        )

    assert resp.status_code == 429
    assert resp.json()["error_code"] == "LOGIN_THROTTLED"
    assert resp.json()["retry_after"] == 120


def test_rotate_credentials_rotate_error():
    with patch(
        "app.api.credentials_api.rotate_credentials",
        side_effect=RotateError("SSH failed"),
    ):
        resp = client.post(
            "/credentials/rotate",
            json={
                "server_id": 1,
                "ssh_port": 22,
                "new_password": "newpass",
                "username": "admin",
                "master_password": "correct",
                "mnemonic": "",
            },
        )

    assert resp.status_code == 422
    assert resp.json()["error_code"] == "ROTATE_FAILED"
    assert "SSH failed" in resp.json()["detail"]
