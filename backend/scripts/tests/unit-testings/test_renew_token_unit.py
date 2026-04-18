from unittest.mock import patch, Mock
import requests
from app.services.vault_client import VaultClient


class TestVaultTokenRenew:

    def test_renew_token_success(self):
        vault = VaultClient()
        vault._backend_token = "test-token"

        with patch("app.services.vault_client.requests.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"auth": {"lease_duration": 3600}}
            mock_post.return_value = mock_response

            result = vault._renew_token()

            assert result is True
            mock_post.assert_called_once_with(
                "http://vault:8200/v1/auth/token/renew-self",
                headers={"X-Vault-Token": "test-token"},
                timeout=5,
            )

    def test_renew_token_failure(self):
        vault = VaultClient()
        vault._backend_token = "test-token"

        with patch("app.services.vault_client.requests.post") as mock_post:
            mock_post.return_value.status_code = 403

            result = vault._renew_token()
            assert result is False

    def test_renew_token_malformed_response(self):
        """200 но нет auth.lease_duration → False, не KeyError наружу"""
        vault = VaultClient()
        vault._backend_token = "test-token"

        with patch("app.services.vault_client.requests.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"auth": {}}
            mock_post.return_value = mock_response

            result = vault._renew_token()
            assert result is False

    def test_renew_token_invalid_json(self):
        """200 но невалидный JSON → False, не ValueError наружу"""
        vault = VaultClient()
        vault._backend_token = "test-token"

        with patch("app.services.vault_client.requests.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_post.return_value = mock_response

            result = vault._renew_token()
            assert result is False

    def test_renew_token_connection_error(self):
        """Сетевая ошибка → False, не ConnectionError наружу"""
        vault = VaultClient()
        vault._backend_token = "test-token"

        with patch("app.services.vault_client.requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.ConnectionError()

            result = vault._renew_token()
            assert result is False

    def test_renew_token_timeout(self):
        """Таймаут → False, не Timeout наружу"""
        vault = VaultClient()
        vault._backend_token = "test-token"

        with patch("app.services.vault_client.requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.Timeout()

            result = vault._renew_token()
            assert result is False
