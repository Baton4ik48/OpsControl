import pytest
from fastapi import HTTPException

from app.api.servers_api import _validate_host, ensure_found

# ==========================
# _validate_host
# ==========================


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


# ==========================
# ensure_found
# ==========================


def test_ensure_found_zero():
    with pytest.raises(HTTPException) as exc:
        ensure_found(0, "Server")

    assert exc.value.status_code == 404
    assert exc.value.detail == "Server not found"


def test_ensure_found_positive():
    # не должен бросать
    ensure_found(1, "Server")
    ensure_found(10, "Server")
