import pytest
from unittest.mock import patch
from app.services.vault_client import VaultClient


class TestVaultBackendToken:

    def test_first_login_creates_token(self):
        """Первый вызов → вызывает _approle_login и сохраняет токен"""
        vault = VaultClient()

        with patch.object(
            vault, "_approle_login", return_value="token123"
        ) as mock_login:
            token = vault._get_backend_token()

            assert token == "token123"
            assert vault._backend_token == "token123"
            mock_login.assert_called_once()

    def test_second_call_renews_token(self):
        """Если токен есть и renew успешен → возвращается тот же токен"""
        vault = VaultClient()
        vault._backend_token = "existing_token"

        with patch.object(
            vault, "_renew_token", return_value=True
        ) as mock_renew, patch.object(vault, "_approle_login") as mock_login:

            token = vault._get_backend_token()

            assert token == "existing_token"
            mock_renew.assert_called_once()
            mock_login.assert_not_called()

    def test_renew_failed_triggers_relogin(self):
        """Если renew не удался → вызывается _approle_login"""
        vault = VaultClient()
        vault._backend_token = "old_token"

        with patch.object(
            vault, "_renew_token", return_value=False
        ) as mock_renew, patch.object(
            vault, "_approle_login", return_value="new_token"
        ) as mock_login:

            token = vault._get_backend_token()

            assert token == "new_token"
            assert vault._backend_token == "new_token"
            mock_renew.assert_called_once()
            mock_login.assert_called_once()

    def test_token_is_cached_between_calls(self):
        """Токен кешируется и не вызывает login повторно"""
        vault = VaultClient()

        with patch.object(
            vault, "_approle_login", return_value="cached_token"
        ) as mock_login, patch.object(vault, "_renew_token", return_value=True):

            token1 = vault._get_backend_token()
            token2 = vault._get_backend_token()

            assert token1 == "cached_token"
            assert token2 == "cached_token"
            assert mock_login.call_count == 1
