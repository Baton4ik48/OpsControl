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

_EXPORT_ENTRIES = [
    {
        "branch": "Москва",
        "server_name": "server-01",
        "ip": "10.0.0.1",
        "port": 22,
        "username": "root",
        "password": "secret",
        "mnemonic": "",
        "updated_at": "2024-01-15T10:00:00",
    }
]

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
    assert resp.json().get("detail") == "Internal server error"


def test_upsert_internal_details_not_leaked():
    """Raw exception text must never reach the client."""
    internal_msg = (
        "Vault недоступен по адресу http://vault-internal:8200 role_id=abc-secret"
    )
    with patch(
        "app.api.credentials_api.upsert_credentials",
        side_effect=Exception(internal_msg),
    ):
        resp = client.post(
            "/credentials/upsert",
            json={"server_id": 1, "port": 22, "username": "root", "password": "pass"},
        )

    body = str(resp.json())
    assert resp.status_code == 500
    assert "vault-internal" not in body
    assert "role_id" not in body
    assert "8200" not in body


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
    assert resp.json()["detail"] == "Credential rotation failed"


def test_rotate_internal_details_not_leaked():
    """Internal Vault/DB details inside RotateError must not reach the client."""
    internal_msg = (
        "Не удалось прочитать креды из Vault: http://vault:8201 403 Forbidden"
    )
    with patch(
        "app.api.credentials_api.rotate_credentials",
        side_effect=RotateError(internal_msg),
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

    body = str(resp.json())
    assert resp.status_code == 422
    assert "vault" not in body.lower() or "ROTATE_FAILED" in body
    assert "8201" not in body
    assert "Forbidden" not in body
    assert resp.json()["detail"] == "Credential rotation failed"


# ============================================
# POST /credentials/export-all
# ============================================


def test_export_all_success():
    with patch(
        "app.api.credentials_api.export_all_credentials",
        return_value=_EXPORT_ENTRIES,
    ):
        resp = client.post(
            "/credentials/export-all",
            json={"username": "admin", "master_password": "correct"},
        )

    assert resp.status_code == 200
    assert resp.json()["success"] is True
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["server_name"] == "server-01"
    assert data[0]["password"] == "secret"


def test_export_all_invalid_password():
    with patch(
        "app.api.credentials_api.export_all_credentials",
        side_effect=InvalidMasterPassword(),
    ):
        resp = client.post(
            "/credentials/export-all",
            json={"username": "admin", "master_password": "wrong"},
        )

    assert resp.status_code == 403
    assert resp.json()["error_code"] == "INVALID_MASTER_PASSWORD"


def test_export_all_throttled():
    with patch(
        "app.api.credentials_api.export_all_credentials",
        side_effect=TooManyLoginAttempts(retry_after_seconds=45),
    ):
        resp = client.post(
            "/credentials/export-all",
            json={"username": "admin", "master_password": "any"},
        )

    assert resp.status_code == 429
    assert resp.json()["error_code"] == "LOGIN_THROTTLED"
    assert resp.json()["retry_after"] == 45


def test_export_all_server_error():
    with patch(
        "app.api.credentials_api.export_all_credentials",
        side_effect=Exception("unexpected"),
    ):
        resp = client.post(
            "/credentials/export-all",
            json={"username": "admin", "master_password": "any"},
        )

    assert resp.status_code == 500
    assert resp.json().get("detail") == "Internal server error"


def test_export_all_internal_details_not_leaked():
    """Vault internals must not leak to the HTTP client."""
    with patch(
        "app.api.credentials_api.export_all_credentials",
        side_effect=Exception("vault://internal-host:8200 role=abc"),
    ):
        resp = client.post(
            "/credentials/export-all",
            json={"username": "admin", "master_password": "any"},
        )

    body = str(resp.json())
    assert resp.status_code == 500
    assert "internal-host" not in body
    assert "8200" not in body
    assert "role" not in body
