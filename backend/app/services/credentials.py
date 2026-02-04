from app.services.vault import (
    vault_login_userpass,
    vault_read_secret,
    VaultAuthError,
    VaultReadError,
)
from app.services.postgres import get_vault_path_by_server_port
from app.logging import get_logger

logger = get_logger("credentials")


class InvalidMasterPassword(Exception):
    pass


class CredentialsNotFound(Exception):
    pass


def show_credentials(server_id: int, port: int, username: str, master_password: str):
    logger.info(
        f"Show credentials request server_id={server_id} port={port} user={username}, master_password={master_password}"
    )

    # 1️⃣ Логинимся в Vault
    try:
        client_token = vault_login_userpass(username, master_password)
        logger.info("Vault login OK")
    except VaultAuthError as e:
        logger.warning(f"Vault login FAILED: {e}")
        raise InvalidMasterPassword()

    # 2️⃣ Получаем vault_path из БД
    vault_path = get_vault_path_by_server_port(server_id, port)
    if not vault_path:
        logger.warning("Vault path NOT FOUND in DB")
        raise CredentialsNotFound()

    logger.info(f"Vault path found: {vault_path}")

    # 3️⃣ Читаем секрет
    try:
        secret = vault_read_secret(client_token, vault_path)
        logger.info("Vault secret read OK")
    except VaultReadError as e:
        logger.warning(f"Vault secret read FAILED: {e}")
        raise CredentialsNotFound()

    # 4️⃣ Возвращаем GUI
    return {
        "username": secret["username"],
        "password": secret["password"],
    }
