import pytest
from unittest.mock import patch
import requests
from app.services.vault_client import (
    VaultClient,
    VaultSealedError,
    VaultUnavailableError,
    VaultAuthError,
)


class TestVaultAppRoleLogin:

    # ========== ОСНОВНЫЕ СЦЕНАРИИ ==========

    def test_login_when_vault_sealed(self):
        """Vault запечатан → VaultSealedError, логин не вызывается"""
        vault = VaultClient()

        with patch("app.services.vault_client.requests.get") as mock_get, patch(
            "app.services.vault_client.requests.post"
        ) as mock_post:

            mock_get.return_value.status_code = 503

            with pytest.raises(VaultSealedError):
                vault._approle_login()

            mock_post.assert_not_called()

    def test_login_when_vault_connection_error(self):
        """Vault недоступен по сети → VaultUnavailableError"""
        vault = VaultClient()

        with patch("app.services.vault_client.requests.get") as mock_get, patch(
            "app.services.vault_client.requests.post"
        ) as mock_post:

            mock_get.side_effect = requests.exceptions.ConnectionError()

            with pytest.raises(VaultUnavailableError):
                vault._approle_login()

            mock_post.assert_not_called()

    def test_login_successful(self):
        """Успешный логин → возвращает токен"""
        vault = VaultClient()

        with patch("app.services.vault_client.requests.get") as mock_get, patch(
            "app.services.vault_client.requests.post"
        ) as mock_post:

            mock_get.return_value.status_code = 200

            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {
                "auth": {"client_token": "s.abc123", "lease_duration": 3600}
            }

            token = vault._approle_login()

            assert token == "s.abc123"
            mock_post.assert_called_once()

    def test_login_bad_credentials(self):
        """Неверные role_id/secret_id → VaultAuthError"""
        vault = VaultClient()

        with patch("app.services.vault_client.requests.get") as mock_get, patch(
            "app.services.vault_client.requests.post"
        ) as mock_post:

            mock_get.return_value.status_code = 200
            mock_post.return_value.status_code = 400

            with pytest.raises(VaultAuthError):
                vault._approle_login()

    def test_login_server_error(self):
        """Vault вернул 500 → VaultUnavailableError"""
        vault = VaultClient()

        with patch("app.services.vault_client.requests.get") as mock_get, patch(
            "app.services.vault_client.requests.post"
        ) as mock_post:

            mock_get.return_value.status_code = 200
            mock_post.return_value.status_code = 500
            mock_post.return_value.text = "Internal Server Error"

            with pytest.raises(VaultUnavailableError):
                vault._approle_login()

    def test_login_malformed_json_response(self):
        """Vault вернул 200 но сломанный JSON → VaultUnavailableError"""
        vault = VaultClient()

        with patch("app.services.vault_client.requests.get") as mock_get, patch(
            "app.services.vault_client.requests.post"
        ) as mock_post:

            mock_get.return_value.status_code = 200
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.side_effect = ValueError("Invalid JSON")

            with pytest.raises(VaultUnavailableError):
                vault._approle_login()

    def test_login_missing_token_in_response(self):
        """Vault вернул 200 но без токена → VaultUnavailableError"""
        vault = VaultClient()

        with patch("app.services.vault_client.requests.get") as mock_get, patch(
            "app.services.vault_client.requests.post"
        ) as mock_post:

            mock_get.return_value.status_code = 200
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {"auth": {}}  # нет client_token

            with pytest.raises(VaultUnavailableError):
                vault._approle_login()

    def test_login_timeout_during_auth(self):
        """Таймаут во время логина → VaultUnavailableError"""
        vault = VaultClient()

        with patch("app.services.vault_client.requests.get") as mock_get, patch(
            "app.services.vault_client.requests.post"
        ) as mock_post:

            mock_get.return_value.status_code = 200
            mock_post.side_effect = requests.exceptions.Timeout()

            with pytest.raises(VaultUnavailableError):
                vault._approle_login()
