import pytest


@pytest.fixture(autouse=True)
def settings_fixture(monkeypatch):
    # Vault (название продукта, не переводится)
    monkeypatch.setattr(
        "app.services.vault_client.settings.VAULT_ADDR", "http://vault:8200"
    )
    monkeypatch.setattr("app.services.vault_client.settings.VAULT_HTTP_TIMEOUT", 5)
    monkeypatch.setattr("app.services.vault_client.settings.VAULT_ROLE_ID", "test-role")
    monkeypatch.setattr(
        "app.services.vault_client.settings.VAULT_SECRET_ID", "test-secret"
    )
    monkeypatch.setattr(
        "app.services.vault_client.settings.VAULT_DATABASE_ROLE_NAME", "test-db-role"
    )

    # DB creds
    monkeypatch.setattr(
        "app.services.vault_db_creds.settings.POSTGRES_HOST", "localhost"
    )
    monkeypatch.setattr("app.services.vault_db_creds.settings.POSTGRES_PORT", 5432)
    monkeypatch.setattr("app.services.vault_db_creds.settings.POSTGRES_DB", "db")
    monkeypatch.setattr("app.services.vault_db_creds.settings.POSTGRES_USER", "user")
    monkeypatch.setattr(
        "app.services.vault_db_creds.settings.POSTGRES_PASSWORD", "pass"
    )
