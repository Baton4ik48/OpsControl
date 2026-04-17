import pytest
from unittest.mock import patch
import requests
from app.services.vault_client import VaultClient, VaultReadError


class TestVaultWriteKV:

    @pytest.mark.parametrize(
        "status_code,data",
        [
            (200, {"a": 1}),
            (204, {"b": 2}),
        ],
    )
    def test_write_success(self, status_code, data):
        vault = VaultClient()
        with patch(
            "app.services.vault_client.requests.post"
        ) as mock_post, patch.object(
            vault, "_get_backend_token", return_value="token123"
        ) as mock_token:
            mock_post.return_value.status_code = status_code

            vault.write_kv_v2("credentials/my-secret", data)

            mock_token.assert_called_once()
            args, kwargs = mock_post.call_args
            assert args[0] == "http://vault:8200/v1/credentials/data/my-secret"
            assert kwargs["headers"]["X-Vault-Token"] == "token123"
            assert kwargs["json"] == {"data": data}
            assert kwargs["timeout"] == 5

    def test_invalid_path(self):
        vault = VaultClient()
        with pytest.raises(VaultReadError) as exc:
            vault.write_kv_v2("wrong-path", {"a": 1})
        assert "Invalid vault path" in str(exc.value)

    def test_write_forbidden_403(self):
        vault = VaultClient()
        with patch(
            "app.services.vault_client.requests.post"
        ) as mock_post, patch.object(
            vault, "_get_backend_token", return_value="token123"
        ):
            mock_post.return_value.status_code = 403
            mock_post.return_value.text = "permission denied"

            with pytest.raises(VaultReadError) as exc:
                vault.write_kv_v2("credentials/my-secret", {"a": 1})

            assert "permission denied" in str(exc.value)

    def test_write_server_error_500(self):
        vault = VaultClient()
        with patch(
            "app.services.vault_client.requests.post"
        ) as mock_post, patch.object(
            vault, "_get_backend_token", return_value="token123"
        ):
            mock_post.return_value.status_code = 500
            mock_post.return_value.text = "Internal Server Error"

            with pytest.raises(VaultReadError) as exc:
                vault.write_kv_v2("credentials/my-secret", {"a": 1})

            assert "Internal Server Error" in str(exc.value)

    def test_write_network_error(self):
        """Сетевая ошибка → VaultReadError (не сырой RequestException)"""
        vault = VaultClient()

        with patch(
            "app.services.vault_client.requests.post"
        ) as mock_post, patch.object(
            vault, "_get_backend_token", return_value="token123"
        ):
            mock_post.side_effect = requests.exceptions.ConnectionError()

            with pytest.raises(VaultReadError):
                vault.write_kv_v2("credentials/x", {"a": 1})
