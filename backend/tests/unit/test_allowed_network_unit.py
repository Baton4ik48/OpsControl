import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from app.middleware.allowed_network import AllowedNetworkMiddleware


def create_app(allowed_networks, trusted_proxies=None):
    app = FastAPI()

    app.add_middleware(
        AllowedNetworkMiddleware,
        allowed_networks=allowed_networks,
        trusted_proxies=trusted_proxies or [],
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


# -----------------------
# TRUSTED PROXY — X-Real-IP
# -----------------------

NGINX_IP = "172.18.0.5"
NGINX_SUBNET = "172.18.0.0/16"


def test_trusted_proxy_allows_real_client():
    """Request through trusted nginx: X-Real-IP is used and allowed client passes."""
    app = create_app(["192.168.1.0/24"], trusted_proxies=[NGINX_IP])
    client = TestClient(app, client=(NGINX_IP, 80))

    resp = client.get("/test", headers={"X-Real-IP": "192.168.1.10"})
    assert resp.status_code == 200


def test_trusted_proxy_blocks_real_client():
    """Request through trusted nginx: X-Real-IP is used and disallowed client is blocked."""
    app = create_app(["192.168.1.0/24"], trusted_proxies=[NGINX_IP])
    client = TestClient(app, client=(NGINX_IP, 80))

    resp = client.get("/test", headers={"X-Real-IP": "10.0.0.99"})
    assert resp.status_code == 403
    assert resp.json()["client_ip"] == "10.0.0.99"


def test_trusted_proxy_subnet_cidr():
    """trusted_proxies accepts CIDR notation."""
    app = create_app(["192.168.1.0/24"], trusted_proxies=[NGINX_SUBNET])
    client = TestClient(app, client=("172.18.3.7", 80))

    resp = client.get("/test", headers={"X-Real-IP": "192.168.1.55"})
    assert resp.status_code == 200


def test_untrusted_source_x_real_ip_ignored():
    """X-Real-IP from a non-proxy source must be ignored (anti-spoofing)."""
    # Attacker's real IP is 10.0.0.99 (blocked), but they send X-Real-IP: 192.168.1.10
    app = create_app(["192.168.1.0/24"], trusted_proxies=[NGINX_IP])
    client = TestClient(app, client=("10.0.0.99", 12345))

    resp = client.get("/test", headers={"X-Real-IP": "192.168.1.10"})
    # Must be blocked: 10.0.0.99 is not a trusted proxy → X-Real-IP ignored
    assert resp.status_code == 403
    assert resp.json()["client_ip"] == "10.0.0.99"


def test_trusted_proxy_no_x_real_ip_header_uses_connection_host():
    """Trusted proxy without X-Real-IP falls back to connection host."""
    app = create_app(["172.18.0.0/16"], trusted_proxies=[NGINX_IP])
    client = TestClient(app, client=(NGINX_IP, 80))

    # No X-Real-IP — connection host (nginx IP) is used and is in allowed range
    resp = client.get("/test")
    assert resp.status_code == 200


def test_trusted_proxy_invalid_x_real_ip_uses_connection_host():
    """If X-Real-IP is malformed, connection host is used as fallback."""
    app = create_app(["172.18.0.0/16"], trusted_proxies=[NGINX_IP])
    client = TestClient(app, client=(NGINX_IP, 80))

    resp = client.get("/test", headers={"X-Real-IP": "not-an-ip"})
    # Falls back to nginx IP (172.18.0.5) which is in 172.18.0.0/16 → allowed
    assert resp.status_code == 200


def test_x_forwarded_for_never_trusted_even_from_proxy():
    """X-Forwarded-For must never be used, even from a trusted proxy."""
    app = create_app(["192.168.1.0/24"], trusted_proxies=[NGINX_IP])
    client = TestClient(app, client=(NGINX_IP, 80))

    # No X-Real-IP; XFF contains allowed IP — must still be blocked
    # because without X-Real-IP we fall back to nginx connection IP (172.18.x)
    # which is NOT in 192.168.1.0/24
    resp = client.get("/test", headers={"X-Forwarded-For": "192.168.1.10"})
    assert resp.status_code == 403


def test_no_trusted_proxies_configured_uses_connection_host():
    """Without trusted_proxies config, X-Real-IP is always ignored."""
    app = create_app(["192.168.1.0/24"], trusted_proxies=[])
    client = TestClient(app, client=("10.0.0.1", 12345))

    resp = client.get("/test", headers={"X-Real-IP": "192.168.1.10"})
    assert resp.status_code == 403
    assert resp.json()["client_ip"] == "10.0.0.1"


def test_ipv4_mapped_ipv6_trusted_proxy():
    """IPv4-mapped IPv6 proxy address is recognized as trusted."""
    app = create_app(["192.168.1.0/24"], trusted_proxies=[NGINX_IP])
    # nginx connects as ::ffff:172.18.0.5
    client = TestClient(app, client=(f"::ffff:{NGINX_IP}", 80))

    resp = client.get("/test", headers={"X-Real-IP": "192.168.1.20"})
    assert resp.status_code == 200
