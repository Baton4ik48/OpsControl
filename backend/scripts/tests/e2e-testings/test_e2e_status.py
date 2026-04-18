import os
import requests
import pytest

BASE_URL = os.getenv("BACKEND_URL", "http://backend:8000") + "/api"


@pytest.mark.e2e
def test_status_all_ok():
    """Все сервисы живые → status=ok, postgres=ok, vault=ok"""
    resp = requests.get(f"{BASE_URL}/status")

    assert resp.status_code == 200

    body = resp.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"
    assert body["data"]["postgres"] == "ok"
    assert body["data"]["vault"] == "ok"


@pytest.mark.e2e
def test_status_response_structure():
    """Структура ответа содержит все обязательные поля"""
    resp = requests.get(f"{BASE_URL}/status")
    body = resp.json()

    assert "success" in body
    assert "data" in body
    assert "status" in body["data"]
    assert "postgres" in body["data"]
    assert "vault" in body["data"]
