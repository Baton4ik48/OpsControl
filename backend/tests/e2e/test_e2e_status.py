import os
import requests
import pytest

BASE_URL = os.getenv("BACKEND_URL", "http://backend:8000") + "/api"

VALID_STATUSES = {"ok", "degraded", "unavailable"}


@pytest.mark.e2e
def test_status_all_ok():
    """Все сервисы живые → status=ok"""
    resp = requests.get(f"{BASE_URL}/status")

    assert resp.status_code == 200

    body = resp.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"


@pytest.mark.e2e
def test_status_response_structure():
    """Ответ содержит только success и data.status — без названий сервисов"""
    resp = requests.get(f"{BASE_URL}/status")
    body = resp.json()

    assert "success" in body
    assert "data" in body
    assert "status" in body["data"]
    assert body["data"]["status"] in VALID_STATUSES

    assert "postgres" not in body["data"]
    assert "vault" not in body["data"]
