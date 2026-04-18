import pytest
from unittest.mock import patch
import requests
from app.services.vault_client import (
    VaultClient,
    VaultUnavailableError,
    VaultSealedError,
)


class TestVaultCheckSealed:

    # ============================================
    # OK состояния (без исключений)
    # ============================================

    @pytest.mark.parametrize("code", [200, 429, 472, 473])
    def test_check_sealed_ok(self, code):
        vault = VaultClient()

        with patch("app.services.vault_client.requests.get") as mock_get:
            mock_get.return_value.status_code = code

            assert vault.check_sealed() is None

    # ============================================
    # Ошибки Vault
    # ============================================

    def test_check_sealed_503_sealed(self):
        vault = VaultClient()

        with patch("app.services.vault_client.requests.get") as mock_get:
            mock_get.return_value.status_code = 503

            with pytest.raises(VaultSealedError):
                vault.check_sealed()

    def test_check_sealed_501_not_initialized(self):
        vault = VaultClient()

        with patch("app.services.vault_client.requests.get") as mock_get:
            mock_get.return_value.status_code = 501

            with pytest.raises(VaultUnavailableError):
                vault.check_sealed()

    def test_check_sealed_unexpected_status(self):
        vault = VaultClient()

        with patch("app.services.vault_client.requests.get") as mock_get:
            mock_get.return_value.status_code = 418

            with pytest.raises(VaultUnavailableError):
                vault.check_sealed()

    # ============================================
    # Сетевые ошибки
    # ============================================

    @pytest.mark.parametrize(
        "exception",
        [
            requests.exceptions.ConnectionError(),
            requests.exceptions.Timeout(),
        ],
    )
    def test_check_sealed_network_errors(self, exception):
        vault = VaultClient()

        with patch("app.services.vault_client.requests.get") as mock_get:
            mock_get.side_effect = exception

            with pytest.raises(VaultUnavailableError):
                vault.check_sealed()
