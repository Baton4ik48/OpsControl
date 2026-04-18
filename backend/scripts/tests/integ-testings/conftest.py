import pytest
from app.services.db.pool_db import init_pool, close_pool


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: integration tests requiring live services"
    )


@pytest.fixture(scope="session", autouse=True)
def db_pool():
    """Инициализирует реальный пул к Postgres перед всеми тестами."""
    ok = init_pool(retries=5, delay=2)
    if not ok:
        pytest.exit("Не удалось подключиться к PostgreSQL — тесты не запущены")
    yield
    close_pool()
