import pytest
from unittest.mock import patch, Mock
import requests

from app.services.vault_client import (
    VaultClient,
    VaultReadError,
)


class TestVaultDatabaseCreds:

    def test_read_creds_success(self):
        vault = VaultClient()

        with patch("app.services.vault_client.requests.get") as mock_get, patch.object(
            vault, "_get_backend_token", return_value="test-token"
        ):
            mock_resp = Mock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "data": {"username": "db_user", "password": "secret"},
                "lease_id": "lease-123",
                "lease_duration": 3600,
            }
            mock_get.return_value = mock_resp

            result = vault.read_database_creds()

            assert result == {"username": "db_user", "password": "secret"}

            args, kwargs = mock_get.call_args
            assert args[0] == "http://vault:8200/v1/database/creds/test-db-role"
            assert kwargs["headers"]["X-Vault-Token"] == "test-token"
            assert kwargs["timeout"] == vault.http_timeout

    def test_read_creds_forbidden(self):
        vault = VaultClient()

        with patch("app.services.vault_client.requests.get") as mock_get, patch.object(
            vault, "_get_backend_token", return_value="test-token"
        ):
            mock_resp = Mock()
            mock_resp.status_code = 403
            mock_resp.text = "permission denied"
            mock_get.return_value = mock_resp

            with pytest.raises(VaultReadError):
                vault.read_database_creds()

    def test_read_creds_malformed_response(self):
        vault = VaultClient()

        with patch("app.services.vault_client.requests.get") as mock_get, patch.object(
            vault, "_get_backend_token", return_value="test-token"
        ):
            mock_resp = Mock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"data": {}}  # нет username
            mock_get.return_value = mock_resp

            with pytest.raises(VaultReadError, match="Malformed Vault response"):
                vault.read_database_creds()

    def test_read_creds_uses_backend_token(self):
        vault = VaultClient()

        with patch("app.services.vault_client.requests.get") as mock_get, patch.object(
            vault, "_get_backend_token", return_value="backend-token"
        ) as mock_token:
            mock_resp = Mock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "data": {"username": "db_user", "password": "secret"},
                "lease_id": "lease-123",
                "lease_duration": 3600,
            }
            mock_get.return_value = mock_resp

            vault.read_database_creds()

            mock_token.assert_called_once()
            _, kwargs = mock_get.call_args
            assert kwargs["headers"]["X-Vault-Token"] == "backend-token"

    def test_read_creds_network_error(self):
        """Сетевая ошибка → VaultReadError"""
        vault = VaultClient()

        with patch("app.services.vault_client.requests.get") as mock_get, patch.object(
            vault, "_get_backend_token", return_value="test-token"
        ):
            mock_get.side_effect = requests.exceptions.ConnectionError()

            with pytest.raises(VaultReadError):
                vault.read_database_creds()
