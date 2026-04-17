import pytest

from app.services.status_services import get_overall_status, check_postgres, check_vault
from app.services.vault_client import VaultUnavailableError, VaultSealedError

# ============================================
# OVERALL STATUS
# ============================================


@pytest.mark.parametrize(
    "pg,vault,expected",
    [
        (True, "ok", "ok"),
        (True, "sealed", "degraded"),
        (True, "offline", "degraded"),
        (False, "ok", "degraded"),
    ],
)
def test_overall_status(pg, vault, expected, monkeypatch):
    monkeypatch.setattr("app.services.status_services.check_postgres", lambda: pg)
    monkeypatch.setattr("app.services.status_services.check_vault", lambda: vault)

    assert get_overall_status() == expected


# ============================================
# POSTGRES
# ============================================


@pytest.mark.parametrize(
    "raises,expected",
    [
        (None, True),
        (Exception("db error"), False),
    ],
)
def test_check_postgres(raises, expected, monkeypatch):
    def mock_execute(fn):
        if raises is not None:
            raise raises

    monkeypatch.setattr("app.services.status_services._execute", mock_execute)

    assert check_postgres() is expected


def test_check_postgres_service_unavailable(monkeypatch):
    """ServiceUnavailableError явно → False"""
    from app.services.db.pool_db import ServiceUnavailableError

    monkeypatch.setattr(
        "app.services.status_services._execute",
        lambda fn: (_ for _ in ()).throw(ServiceUnavailableError()),
    )

    assert check_postgres() is False


# ============================================
# VAULT
# ============================================


@pytest.mark.parametrize(
    "behavior,expected",
    [
        ("ok", "ok"),
        ("sealed", "sealed"),
        ("offline", "offline"),
    ],
)
def test_check_vault(behavior, expected, monkeypatch):

    class MockClient:
        def check_sealed(self):
            if behavior == "sealed":
                raise VaultSealedError()
            elif behavior == "offline":
                raise VaultUnavailableError()
            return None

    monkeypatch.setattr(
        "app.services.vault_client.get_vault_client", lambda: MockClient()
    )

    assert check_vault() == expected
