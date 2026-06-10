import os
import pytest

from app.services.db.branches_db import create_branch, delete_branch
from app.services.db.servers_db import create_server, delete_server
from app.services.db.ports_db import create_port, delete_port
from app.services.db.credentials_db import get_vault_path_by_server_port
from app.services.credentials import (
    upsert_credentials,
    show_credentials,
    verify_admin_password,
    rotate_credentials,
    InvalidMasterPassword,
    CredentialsNotFound,
)

# Тестовый admin — должен существовать в Vault userpass
# Настраивается через vault-init-dev.sh
VAULT_ADMIN_USER = os.getenv("VAULT_ADMIN_USER", "admin")
VAULT_ADMIN_PASSWORD = os.getenv("VAULT_ADMIN_PASSWORD", "admin")
CLIENT_IP = "127.0.0.1"


@pytest.fixture(scope="module")
def server_id():
    branch_id = create_branch("integ-creds-branch")
    srv_id = create_server(branch_id, "integ-creds-srv", "10.3.0.1", "linux")
    create_port(srv_id, 22)
    yield srv_id
    delete_port(srv_id, 22)
    delete_server(srv_id)
    delete_branch(branch_id)


@pytest.mark.integration
def test_verify_admin_password_success():
    """Верный мастер-пароль → не бросает исключение"""
    verify_admin_password(VAULT_ADMIN_USER, VAULT_ADMIN_PASSWORD, CLIENT_IP)


@pytest.mark.integration
def test_verify_admin_password_invalid():
    """Неверный пароль → InvalidMasterPassword"""
    with pytest.raises(InvalidMasterPassword):
        verify_admin_password(VAULT_ADMIN_USER, "wrong-password", CLIENT_IP)


@pytest.mark.integration
def test_upsert_credentials_writes_to_vault_and_db(server_id):
    vault_path = upsert_credentials(server_id, 22, "root", "secret123")

    assert vault_path == f"credentials/servers/{server_id}/22"

    # Проверяем что путь сохранён в БД
    path_in_db = get_vault_path_by_server_port(server_id, 22)
    assert path_in_db == vault_path


@pytest.mark.integration
def test_show_credentials_success(server_id):
    upsert_credentials(server_id, 22, "root", "secret123")

    result = show_credentials(
        server_id=server_id,
        port=22,
        username=VAULT_ADMIN_USER,
        master_password=VAULT_ADMIN_PASSWORD,
        client_ip=CLIENT_IP,
    )

    assert result["username"] == "root"
    assert result["password"] == "secret123"


@pytest.mark.integration
def test_show_credentials_invalid_password(server_id):
    with pytest.raises(InvalidMasterPassword):
        show_credentials(
            server_id=server_id,
            port=22,
            username=VAULT_ADMIN_USER,
            master_password="wrong",
            client_ip=CLIENT_IP,
        )


@pytest.mark.integration
def test_show_credentials_not_found(server_id):
    """Порт без credentials → CredentialsNotFound"""
    with pytest.raises(CredentialsNotFound):
        show_credentials(
            server_id=server_id,
            port=9999,
            username=VAULT_ADMIN_USER,
            master_password=VAULT_ADMIN_PASSWORD,
            client_ip=CLIENT_IP,
        )


@pytest.mark.integration
def test_rotate_credentials_updates_password(server_id):
    upsert_credentials(server_id, 22, "root", "old-password")

    rotate_credentials(
        server_id=server_id,
        ssh_port=22,
        new_password="new-password",
        username=VAULT_ADMIN_USER,
        master_password=VAULT_ADMIN_PASSWORD,
        client_ip=CLIENT_IP,
        mnemonic="test mnemonic",
    )

    result = show_credentials(
        server_id=server_id,
        port=22,
        username=VAULT_ADMIN_USER,
        master_password=VAULT_ADMIN_PASSWORD,
        client_ip=CLIENT_IP,
    )

    assert result["password"] == "new-password"
    assert result["mnemonic"] == "test mnemonic"
