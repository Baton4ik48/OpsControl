import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from app.middleware.allowed_network import AllowedNetworkMiddleware


def create_app(allowed_networks):
    app = FastAPI()

    app.add_middleware(
        AllowedNetworkMiddleware,
        allowed_networks=allowed_networks,
    )

    @app.get("/test")
    def test():
        return {"ok": True}

    return app


# -----------------------
# BASIC BEHAVIOR
# -----------------------


def test_allowed_ip_passes():
    app = create_app(["192.168.1.0/24"])
    client = TestClient(app, client=("192.168.1.10", 12345))

    response = client.get("/test")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_denied_ip_blocked():
    app = create_app(["192.168.1.0/24"])
    client = TestClient(app, client=("10.0.0.1", 12345))

    response = client.get("/test")

    assert response.status_code == 403
    assert response.json()["detail"] == "Access denied from this network"


def test_call_next_not_called_when_blocked():
    called = {"flag": False}

    app = FastAPI()

    @app.get("/test")
    def test():
        called["flag"] = True
        return {"ok": True}

    app.add_middleware(
        AllowedNetworkMiddleware,
        allowed_networks=["192.168.1.0/24"],
    )

    client = TestClient(app, client=("10.0.0.1", 12345))

    response = client.get("/test")

    assert response.status_code == 403
    assert called["flag"] is False


# -----------------------
# IPv4 / IPv6
# -----------------------


def test_ipv4_mapped_ipv6():
    app = create_app(["192.168.1.0/24"])
    client = TestClient(app, client=("::ffff:192.168.1.10", 12345))

    response = client.get("/test")

    assert response.status_code == 200


def test_ipv6_allowed():
    app = create_app(["2001:db8::/32"])
    client = TestClient(app, client=("2001:db8::1", 12345))

    response = client.get("/test")

    assert response.status_code == 200


def test_ipv6_denied():
    app = create_app(["2001:db8::/32"])
    client = TestClient(app, client=("2001:dead::1", 12345))

    response = client.get("/test")

    assert response.status_code == 403


# -----------------------
# NETWORK CONFIG
# -----------------------


def test_empty_allowed_networks_blocks_all():
    app = create_app([])
    client = TestClient(app, client=("192.168.1.10", 12345))

    response = client.get("/test")

    assert response.status_code == 403


def test_multiple_networks():
    app = create_app(["10.0.0.0/8", "192.168.1.0/24"])
    client = TestClient(app, client=("10.5.5.5", 12345))

    response = client.get("/test")

    assert response.status_code == 200


def test_single_ip_network():
    app = create_app(["192.168.1.10/32"])

    client_ok = TestClient(app, client=("192.168.1.10", 12345))
    client_fail = TestClient(app, client=("192.168.1.11", 12345))

    ok = client_ok.get("/test")
    fail = client_fail.get("/test")

    assert ok.status_code == 200
    assert fail.status_code == 403


def test_invalid_network_raises():
    app = create_app(["not-a-network"])
    client = TestClient(app)

    with pytest.raises(ValueError):
        client.get("/test")


# -----------------------
# HEADERS / SOURCE IP
# -----------------------


def test_x_forwarded_for_ignored():
    app = create_app(["192.168.1.0/24"])
    client = TestClient(app, client=("10.0.0.1", 12345))

    response = client.get(
        "/test",
        headers={"X-Forwarded-For": "192.168.1.10"},
    )

    # используется request.client.host
    assert response.status_code == 403


# -----------------------
# RESPONSE VALIDATION
# -----------------------


def test_response_contains_client_ip():
    app = create_app(["192.168.1.0/24"])
    client = TestClient(app, client=("10.0.0.5", 12345))

    response = client.get("/test")

    assert response.status_code == 403
    assert response.json()["client_ip"] == "10.0.0.5"


def test_allowed_response_not_modified():
    app = create_app(["192.168.1.0/24"])
    client = TestClient(app, client=("192.168.1.10", 12345))

    response = client.get("/test")

    assert response.status_code == 200
    assert "client_ip" not in response.json()
