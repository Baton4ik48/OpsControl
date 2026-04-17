from app.services import vault_client


class TestGetVaultClient:

    def test_get_vault_client_creates_new_if_none(self, monkeypatch):
        """Первый вызов создает новый инстанс нужного типа"""
        monkeypatch.setattr(vault_client, "_vault_instance", None)

        client = vault_client.get_vault_client()

        assert isinstance(client, vault_client.VaultClient)

    def test_get_vault_client_singleton(self, monkeypatch):
        """Повторные вызовы возвращают тот же инстанс"""
        monkeypatch.setattr(vault_client, "_vault_instance", None)

        client1 = vault_client.get_vault_client()
        client2 = vault_client.get_vault_client()

        assert client1 is client2
