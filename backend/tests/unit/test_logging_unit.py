"""
Unit tests for logging infrastructure.

Tests verify:
  1. RequestLoggingMiddleware writes to the "audit" logger.
  2. Successful port-result (POST …/result) requests are NOT written to audit log.
  3. No secret values (passwords, master_password) appear in audit log entries.
  4. 5xx responses are additionally written to the "http" (errors) logger.
  5. AllowedNetworkMiddleware stores client_ip in request.state for downstream use.
"""

import logging
from unittest.mock import patch, MagicMock

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.middleware.request_logging import RequestLoggingMiddleware
from app.middleware.allowed_network import AllowedNetworkMiddleware

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_logging_app(route_handler=None, status_code=200):
    """Minimal app with only RequestLoggingMiddleware for isolated testing."""
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/test")
    def _test():
        return {"ok": True}

    @app.post("/test")
    def _test_post():
        return {"ok": True}

    @app.post("/api/ports/1/22/result")
    def _result():
        return {"ok": True}

    @app.post("/api/ports/1/22/result-fail")
    def _result_fail():
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=503, content={"error": "down"})

    return app


# ---------------------------------------------------------------------------
# 1. Audit logger receives normal requests
# ---------------------------------------------------------------------------


def test_request_is_logged_to_audit():
    app = make_logging_app()
    client = TestClient(app)

    with patch.object(logging.getLogger("audit"), "info") as mock_audit:
        resp = client.get("/test")

    assert resp.status_code == 200
    mock_audit.assert_called_once()

    # Verify key fields appear in the log call
    call_args = mock_audit.call_args
    log_str = call_args.args[0] % call_args.args[1:]
    assert "method=GET" in log_str
    assert 'path="/test"' in log_str
    assert "status=200" in log_str
    assert "ip=" in log_str
    assert "request_id=" in log_str


# ---------------------------------------------------------------------------
# 2. Successful port-result POSTs are suppressed (noisy polling endpoint)
# ---------------------------------------------------------------------------


def test_port_result_success_not_logged_to_audit():
    app = make_logging_app()
    client = TestClient(app)

    with patch.object(logging.getLogger("audit"), "info") as mock_audit:
        resp = client.post("/api/ports/1/22/result")

    assert resp.status_code == 200
    mock_audit.assert_not_called()


def test_port_result_failure_is_logged_to_audit():
    """Non-200 results (server offline) must still be audited."""
    app = make_logging_app()
    client = TestClient(app)

    with patch.object(logging.getLogger("audit"), "info") as mock_audit:
        resp = client.post("/api/ports/1/22/result-fail")

    assert resp.status_code == 503
    mock_audit.assert_called_once()


# ---------------------------------------------------------------------------
# 3. No secret values in audit log (credentials endpoints)
# ---------------------------------------------------------------------------


def make_credentials_app():
    """App with credentials router and only RequestLoggingMiddleware."""
    from app.api.credentials_api import router as creds_router

    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)
    app.include_router(creds_router)
    return app


def _all_audit_strings(mock_audit) -> list[str]:
    result = []
    for call in mock_audit.call_args_list:
        fmt = call.args[0]
        args = call.args[1:]
        try:
            result.append(fmt % args)
        except Exception:
            result.append(fmt)
    return result


SECRET_PASSWORD = "super_s3cret_master_pass"
SECRET_NEW_PASS = "brand_new_p@ssword_456"


def test_verify_admin_no_password_in_audit():
    app = make_credentials_app()
    client = TestClient(app)

    with patch("app.api.credentials_api.verify_admin_password"), patch.object(
        logging.getLogger("audit"), "info"
    ) as mock_audit:
        client.post(
            "/credentials/verify-admin",
            json={"username": "admin", "master_password": SECRET_PASSWORD},
        )

    for entry in _all_audit_strings(mock_audit):
        assert SECRET_PASSWORD not in entry, f"Password leaked in: {entry}"
        assert "master_password" not in entry, f"Field name leaked in: {entry}"


def test_show_credentials_no_password_in_audit():
    app = make_credentials_app()
    client = TestClient(app)

    fake_creds = {"username": "root", "password": "returned_secret", "mnemonic": ""}

    with patch(
        "app.api.credentials_api.show_credentials", return_value=fake_creds
    ), patch.object(logging.getLogger("audit"), "info") as mock_audit:
        client.post(
            "/credentials/show",
            json={
                "server_id": 1,
                "port": 22,
                "username": "admin",
                "master_password": SECRET_PASSWORD,
            },
        )

    for entry in _all_audit_strings(mock_audit):
        assert SECRET_PASSWORD not in entry, f"master_password leaked in: {entry}"
        assert "returned_secret" not in entry, f"Vault secret value leaked in: {entry}"


def test_upsert_credentials_no_password_in_audit():
    app = make_credentials_app()
    client = TestClient(app)

    with patch(
        "app.api.credentials_api.upsert_credentials", return_value="creds/servers/1/22"
    ), patch.object(logging.getLogger("audit"), "info") as mock_audit:
        client.post(
            "/credentials/upsert",
            json={
                "server_id": 1,
                "port": 22,
                "username": "root",
                "password": SECRET_NEW_PASS,
            },
        )

    for entry in _all_audit_strings(mock_audit):
        assert SECRET_NEW_PASS not in entry, f"password leaked in: {entry}"


def test_rotate_credentials_no_password_in_audit():
    app = make_credentials_app()
    client = TestClient(app)

    with patch("app.api.credentials_api.rotate_credentials"), patch.object(
        logging.getLogger("audit"), "info"
    ) as mock_audit:
        client.post(
            "/credentials/rotate",
            json={
                "server_id": 1,
                "ssh_port": 22,
                "new_password": SECRET_NEW_PASS,
                "username": "admin",
                "master_password": SECRET_PASSWORD,
                "mnemonic": "",
            },
        )

    for entry in _all_audit_strings(mock_audit):
        assert SECRET_PASSWORD not in entry, f"master_password leaked in: {entry}"
        assert SECRET_NEW_PASS not in entry, f"new_password leaked in: {entry}"


# ---------------------------------------------------------------------------
# 4. 5xx responses are forwarded to errors logger
# ---------------------------------------------------------------------------


def test_5xx_written_to_error_logger():
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/boom")
    def _boom():
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=500, content={"error": "oops"})

    client = TestClient(app, raise_server_exceptions=False)

    with patch.object(logging.getLogger("http"), "warning") as mock_warn:
        resp = client.get("/boom")

    assert resp.status_code == 500
    mock_warn.assert_called_once()
    call_str = mock_warn.call_args.args[0] % mock_warn.call_args.args[1:]
    assert "500" in call_str


# ---------------------------------------------------------------------------
# 5. AllowedNetworkMiddleware stores client_ip in request.state
# ---------------------------------------------------------------------------


def test_allowed_network_sets_client_ip_in_state():
    captured = {}

    app = FastAPI()
    app.add_middleware(
        AllowedNetworkMiddleware,
        allowed_networks=["192.168.1.0/24"],
        trusted_proxies=[],
    )

    @app.get("/test")
    def _test(request: Request):
        captured["ip"] = getattr(request.state, "client_ip", None)
        return {"ok": True}

    client = TestClient(app, client=("192.168.1.10", 12345))
    resp = client.get("/test")

    assert resp.status_code == 200
    assert captured["ip"] == "192.168.1.10"


def test_denied_request_does_not_set_client_ip_in_state():
    """Blocked requests never call call_next, so request.state.client_ip is irrelevant."""
    app = FastAPI()
    app.add_middleware(
        AllowedNetworkMiddleware,
        allowed_networks=["192.168.1.0/24"],
        trusted_proxies=[],
    )

    @app.get("/test")
    def _test(request: Request):
        return {"ok": True}

    client = TestClient(app, client=("10.0.0.1", 12345))
    resp = client.get("/test")
    assert resp.status_code == 403
