import os
import time
import requests
import pytest

BASE_URL = os.getenv("BACKEND_URL", "http://backend:8000") + "/api"


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "e2e: end-to-end tests requiring full running stack"
    )


@pytest.fixture(scope="session", autouse=True)
def wait_for_backend():
    """Ждёт пока бэкенд полностью поднимется перед запуском тестов."""
    url = BASE_URL + "/status"
    for _ in range(30):
        try:
            resp = requests.get(url, timeout=2)
            if resp.status_code == 200:
                return
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(1)
    pytest.exit("Backend недоступен — e2e тесты не запущены")
