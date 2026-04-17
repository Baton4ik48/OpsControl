import pytest
from unittest.mock import patch
import requests

from app.services.vault_client import (
    VaultClient,
    VaultAuthError,
    VaultUnavailableError,
)


class TestVaultUserpassLogin:

    def test_login_success(self):
        vault = VaultClient()

        with patch("app.services.vault_client.requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {
                "auth": {"client_token": "user.token.123"}
            }

            token = vault.login_userpass("User", "pass")

            assert token == "user.token.123"

            args, kwargs = mock_post.call_args
            assert args[0] == "http://vault:8200/v1/auth/userpass/login/user"
            assert kwargs["json"] == {"password": "pass"}
            assert kwargs["timeout"] == 5

    def test_login_bad_credentials(self):
        vault = VaultClient()

        with patch("app.services.vault_client.requests.post") as mock_post:
            mock_post.return_value.status_code = 403
            mock_post.return_value.text = "permission denied"

            with pytest.raises(VaultAuthError):
                vault.login_userpass("user", "wrong")

    def test_login_username_lowercase(self):
        vault = VaultClient()

        with patch("app.services.vault_client.requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {
                "auth": {"client_token": "token"}
            }

            vault.login_userpass("ADMIN", "pass")

            args, _ = mock_post.call_args
            assert "/userpass/login/admin" in args[0]

    # ===== ошибки по контракту =====

    def test_login_vault_unavailable(self):
        vault = VaultClient()

        with patch("app.services.vault_client.requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.ConnectionError()

            with pytest.raises(VaultUnavailableError):
                vault.login_userpass("user", "pass")

    def test_login_timeout(self):
        vault = VaultClient()

        with patch("app.services.vault_client.requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.Timeout()

            with pytest.raises(VaultUnavailableError):
                vault.login_userpass("user", "pass")

    def test_login_invalid_json(self):
        vault = VaultClient()

        with patch("app.services.vault_client.requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.side_effect = ValueError()

            with pytest.raises(VaultUnavailableError):
                vault.login_userpass("user", "pass")

    def test_login_missing_token(self):
        vault = VaultClient()

        with patch("app.services.vault_client.requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {"auth": {}}

            with pytest.raises(VaultAuthError):
                vault.login_userpass("user", "pass")
