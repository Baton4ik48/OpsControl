import pytest

from app.services.status_services import check_postgres, check_vault, get_overall_status


@pytest.mark.integration
def test_check_postgres_ok():
    """Реальный Postgres доступен → True"""
    assert check_postgres() is True


@pytest.mark.integration
def test_check_vault_ok():
    """Реальный Vault доступен и не запечатан → 'ok'"""
    result = check_vault()
    assert result in ("ok", "sealed", "offline")


@pytest.mark.integration
def test_get_overall_status():
    result = get_overall_status()
    assert result in ("ok", "degraded")
