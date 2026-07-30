import pytest
from unittest.mock import Mock, patch

from app.services.vault_db_creds import (
    _static_creds,
    _get_dynamic_db_creds,
    get_db_credentials,
    DBCreds,
)

from app.services.vault_client import (
    VaultReadError,
    VaultSealedError,
    VaultUnavailableError,
    VaultAuthError,
)


def test_static_creds():
    creds = _static_creds()

    assert isinstance(creds, DBCreds)
    assert creds.host == "localhost"
    assert creds.port == 5432
    assert creds.dbname == "db"
    assert creds.user == "user"
    assert creds.password == "pass"


def test_dynamic_creds_success():
    mock_vault = Mock()
    mock_vault.read_database_creds.return_value = {
        "username": "dyn_user",
        "password": "dyn_pass",
    }

    with patch("app.services.vault_db_creds.get_vault_client", return_value=mock_vault):
        creds = _get_dynamic_db_creds()

    assert creds.user == "dyn_user"
    assert creds.password == "dyn_pass"
    assert creds.host == "localhost"


def test_dynamic_creds_vault_read_error():
    mock_vault = Mock()
    mock_vault.read_database_creds.side_effect = VaultReadError()

    with patch("app.services.vault_db_creds.get_vault_client", return_value=mock_vault):
        with pytest.raises(VaultReadError):
            _get_dynamic_db_creds()


def test_dynamic_creds_vault_sealed():
    mock_vault = Mock()
    mock_vault.read_database_creds.side_effect = VaultSealedError()

    with patch("app.services.vault_db_creds.get_vault_client", return_value=mock_vault):
        with pytest.raises(VaultSealedError):
            _get_dynamic_db_creds()


def test_dynamic_creds_vault_unavailable():
    mock_vault = Mock()
    mock_vault.read_database_creds.side_effect = VaultUnavailableError()

    with patch("app.services.vault_db_creds.get_vault_client", return_value=mock_vault):
        with pytest.raises(VaultUnavailableError):
            _get_dynamic_db_creds()


def test_dynamic_creds_vault_auth_error():
    """VaultAuthError (неверный role_id/secret_id) → пробрасывается наружу"""
    mock_vault = Mock()
    mock_vault.read_database_creds.side_effect = VaultAuthError()

    with patch("app.services.vault_db_creds.get_vault_client", return_value=mock_vault):
        with pytest.raises(VaultAuthError):
            _get_dynamic_db_creds()


def test_dynamic_creds_unexpected_exception():
    mock_vault = Mock()
    mock_vault.read_database_creds.side_effect = Exception("Boom")

    with patch("app.services.vault_db_creds.get_vault_client", return_value=mock_vault):
        with pytest.raises(Exception) as exc:
            _get_dynamic_db_creds()

    assert "Boom" in str(exc.value)


def test_get_db_credentials_static_mode(monkeypatch):
    monkeypatch.setattr("app.services.vault_db_creds.settings.DB_CREDS_MODE", "static")

    creds = get_db_credentials()

    assert isinstance(creds, DBCreds)
    assert creds.user == "user"


def test_get_db_credentials_vault_mode(monkeypatch):
    monkeypatch.setattr("app.services.vault_db_creds.settings.DB_CREDS_MODE", "vault")

    with patch("app.services.vault_db_creds._get_dynamic_db_creds") as mock_dyn:
        mock_dyn.return_value = DBCreds("h", 1, "d", "dyn", "p")

        creds = get_db_credentials()

    mock_dyn.assert_called_once()
    assert creds.user == "dyn"


def test_get_db_credentials_auto_success(monkeypatch):
    monkeypatch.setattr("app.services.vault_db_creds.settings.DB_CREDS_MODE", "auto")

    with patch("app.services.vault_db_creds._get_dynamic_db_creds") as mock_dyn:
        mock_dyn.return_value = DBCreds("h", 1, "d", "dyn", "p")

        creds = get_db_credentials()

    assert creds.user == "dyn"


def test_get_db_credentials_auto_fallback(monkeypatch):
    monkeypatch.setattr("app.services.vault_db_creds.settings.DB_CREDS_MODE", "auto")

    with patch("app.services.vault_db_creds._get_dynamic_db_creds") as mock_dyn, patch(
        "app.services.vault_db_creds._static_creds"
    ) as mock_static:

        mock_dyn.side_effect = Exception("vault down")
        mock_static.return_value = DBCreds("h", 1, "d", "static", "p")

        creds = get_db_credentials()

    assert creds.user == "static"


def test_get_db_credentials_invalid_mode(monkeypatch):
    monkeypatch.setattr("app.services.vault_db_creds.settings.DB_CREDS_MODE", "invalid")

    with pytest.raises(RuntimeError):
        get_db_credentials()
