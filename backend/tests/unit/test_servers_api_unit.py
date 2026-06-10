import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.api.servers_api import (
    _validate_host,
    ensure_found,
    ServerCreate,
    ServerUpdate,
    router,
)

_app_client = None


def _client():
    global _app_client
    if _app_client is None:
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        _app_client = TestClient(app, raise_server_exceptions=False)
    return _app_client


def test_validate_ipv4_valid():
    assert _validate_host("192.168.1.1") == "192.168.1.1"


def test_validate_domain_valid():
    assert _validate_host("example.com") == "example.com"


def test_validate_localhost():
    # ipaddress принимает localhost? нет → это домен → не проходит regex
    with pytest.raises(ValueError):
        _validate_host("localhost")


def test_validate_loopback_ip():
    # 127.0.0.1 — валидный IPv4
    assert _validate_host("127.0.0.1") == "127.0.0.1"


def test_validate_empty_string():
    with pytest.raises(ValueError):
        _validate_host("")


def test_validate_string_with_spaces():
    with pytest.raises(ValueError):
        _validate_host("192.168.1.1 test")


def test_validate_ip_with_mask():
    # ip_network не используется → ip_address падает → regex не матчится
    with pytest.raises(ValueError):
        _validate_host("192.168.1.0/24")


def test_validate_invalid_ip():
    with pytest.raises(ValueError):
        _validate_host("999.999.999.999")


def test_validate_invalid_domain():
    with pytest.raises(ValueError):
        _validate_host("invalid_domain")


def test_validate_subdomain():
    assert _validate_host("api.example.com") == "api.example.com"


def test_ensure_found_zero():
    with pytest.raises(HTTPException) as exc:
        ensure_found(0, "Server")

    assert exc.value.status_code == 404
    assert exc.value.detail == "Server not found"


def test_ensure_found_positive():
    # не должен бросать
    ensure_found(1, "Server")
    ensure_found(10, "Server")


@pytest.mark.parametrize(
    "device_type", ["linux", "windows", "nateks", "natex", "cisco"]
)
def test_server_create_valid_device_type(device_type):
    m = ServerCreate(branch_id=1, name="x", ip="1.2.3.4", device_type=device_type)
    assert m.device_type == device_type


def test_server_create_invalid_device_type():
    with pytest.raises(Exception):
        ServerCreate(branch_id=1, name="x", ip="1.2.3.4", device_type="unknown")


def test_server_create_default_device_type():
    m = ServerCreate(branch_id=1, name="x", ip="1.2.3.4")
    assert m.device_type == "linux"


def test_server_update_valid_device_type():
    m = ServerUpdate(name="x", ip="1.2.3.4", device_type="cisco")
    assert m.device_type == "cisco"


def test_server_update_invalid_device_type():
    with pytest.raises(Exception):
        ServerUpdate(name="x", ip="1.2.3.4", device_type="router")


def test_get_servers_by_branch():
    rows = [(1, "srv1", "10.0.0.1", "linux"), (2, "srv2", "10.0.0.2", "windows")]
    with patch("app.api.servers_api.load_servers", return_value=rows):
        resp = _client().get("/servers/by-branch/7")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert len(data["data"]) == 2
    assert data["data"][0] == {
        "id": 1,
        "name": "srv1",
        "ip": "10.0.0.1",
        "device_type": "linux",
    }


def test_create_server_api():
    with patch("app.api.servers_api.create_server", return_value=42):
        resp = _client().post(
            "/servers",
            json={
                "branch_id": 1,
                "name": "db01",
                "ip": "192.168.1.5",
                "device_type": "linux",
            },
        )
    assert resp.status_code == 200
    assert resp.json() == {"success": True, "data": {"id": 42}}


def test_create_server_api_invalid_device_type():
    resp = _client().post(
        "/servers",
        json={
            "branch_id": 1,
            "name": "db01",
            "ip": "192.168.1.5",
            "device_type": "bad",
        },
    )
    assert resp.status_code == 422


def test_update_server_api():
    with patch("app.api.servers_api.update_server", return_value=1):
        resp = _client().put(
            "/servers/5",
            json={"name": "new", "ip": "10.10.10.1", "device_type": "cisco"},
        )
    assert resp.status_code == 200
    assert resp.json() == {"success": True, "data": None}


def test_update_server_api_not_found():
    with patch("app.api.servers_api.update_server", return_value=0):
        resp = _client().put(
            "/servers/999",
            json={"name": "x", "ip": "1.2.3.4", "device_type": "linux"},
        )
    assert resp.status_code == 404


def test_delete_server_api():
    with patch("app.api.servers_api.delete_server", return_value=1):
        resp = _client().delete("/servers/8")
    assert resp.status_code == 200
    assert resp.json() == {"success": True, "data": None}


def test_delete_server_api_not_found():
    with patch("app.api.servers_api.delete_server", return_value=0):
        resp = _client().delete("/servers/999")
    assert resp.status_code == 404
