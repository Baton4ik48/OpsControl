from app.services.vault_client import VaultClient, VaultAuthError, VaultReadError
from app.services.postgres import get_vault_path_by_server_port
from app.logging import get_logger

logger = get_logger("credentials")


class InvalidMasterPassword(Exception):
    pass


class CredentialsNotFound(Exception):
    pass


def show_credentials(server_id: int, port: int, username: str, master_password: str):
    logger.info(
        f"Show credentials request server_id={server_id} port={port} user={username}"
    )

    vault = VaultClient()

    # 1. Логин в Vault
    try:
        token = vault.login_userpass(username, master_password)
        logger.info("Vault login OK")
    except VaultAuthError:
        logger.warning("Vault login FAILED")
        raise InvalidMasterPassword()

    # 2. Получаем путь из БД
    vault_path = get_vault_path_by_server_port(server_id, port)
    if not vault_path:
        raise CredentialsNotFound()

    logger.info(f"Vault path found: {vault_path}")

    # 3. Читаем секрет
    try:
        secret = vault.read_kv_v2(token, vault_path)
        logger.info("Vault secret read OK")
    except VaultReadError:
        raise CredentialsNotFound()

    return {
        "username": secret["username"],
        "password": secret["password"],
    }

