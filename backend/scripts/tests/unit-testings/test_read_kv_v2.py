import pytest
from unittest.mock import patch, Mock
import requests
from app.services.vault_client import VaultClient, VaultReadError


class TestVaultReadKV:

    def test_read_success(self):
        """Успешное чтение → возвращает данные"""
        vault = VaultClient()

        with patch("app.services.vault_client.requests.get") as mock_get:
            mock_resp = Mock()
            mock_resp.status_code = 200
            mock_resp.content = b'{"data": {"data": {}}}'
            mock_resp.json.return_value = {
                "data": {"data": {"username": "test", "password": "secret"}}
            }
            mock_get.return_value = mock_resp

            result = vault.read_kv_v2("test-token", "credentials/my-path")

            assert result == {"username": "test", "password": "secret"}

            mock_get.assert_called_once_with(
                "http://vault:8200/v1/credentials/data/my-path",
                headers={"X-Vault-Token": "test-token"},
                timeout=5,
            )

    def test_invalid_path_no_credentials_prefix(self):
        """Путь без 'credentials/' → VaultReadError"""
        vault = VaultClient()

        with pytest.raises(VaultReadError) as exc:
            vault.read_kv_v2("token", "wrong-path/my-secret")

        assert "Invalid vault path" in str(exc.value)

    def test_read_not_found_404(self):
        """404 → VaultReadError"""
        vault = VaultClient()

        with patch("app.services.vault_client.requests.get") as mock_get:
            mock_resp = Mock()
            mock_resp.status_code = 404
            mock_resp.text = "not found"
            mock_get.return_value = mock_resp

            with pytest.raises(VaultReadError):
                vault.read_kv_v2("token", "credentials/missing")

            mock_get.assert_called_once_with(
                "http://vault:8200/v1/credentials/data/missing",
                headers={"X-Vault-Token": "token"},
                timeout=5,
            )

    def test_read_forbidden_403(self):
        """403 → VaultReadError"""
        vault = VaultClient()

        with patch("app.services.vault_client.requests.get") as mock_get:
            mock_resp = Mock()
            mock_resp.status_code = 403
            mock_resp.text = "forbidden"
            mock_get.return_value = mock_resp

            with pytest.raises(VaultReadError):
                vault.read_kv_v2("token", "credentials/secret")

    def test_read_malformed_response(self):
        """200 но неверная структура JSON → VaultReadError"""
        vault = VaultClient()

        with patch("app.services.vault_client.requests.get") as mock_get:
            mock_resp = Mock()
            mock_resp.status_code = 200
            mock_resp.content = b"{}"
            mock_resp.json.return_value = {}  # нет data
            mock_get.return_value = mock_resp

            with pytest.raises(VaultReadError):
                vault.read_kv_v2("token", "credentials/broken")

    def test_read_empty_response_body(self):
        """200 но пустое тело ответа → VaultReadError"""
        vault = VaultClient()

        with patch("app.services.vault_client.requests.get") as mock_get:
            mock_resp = Mock()
            mock_resp.status_code = 200
            mock_resp.content = b""
            mock_get.return_value = mock_resp

            with pytest.raises(VaultReadError, match="Пустой ответ"):
                vault.read_kv_v2("token", "credentials/empty")

    def test_read_connection_error(self):
        """Сетевая ошибка → VaultReadError"""
        vault = VaultClient()

        with patch("app.services.vault_client.requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError()

            with pytest.raises(VaultReadError):
                vault.read_kv_v2("token", "credentials/secret")

    def test_read_timeout(self):
        """Таймаут → VaultReadError (отдельная ветка в коде)"""
        vault = VaultClient()

        with patch("app.services.vault_client.requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout()

            with pytest.raises(VaultReadError):
                vault.read_kv_v2("token", "credentials/x")
