from app.services.vault_client import VaultClient, VaultAuthError, VaultReadError
from app.services.db.credentials import get_vault_path_by_server_port
from app.services.login_throttle import throttle, TooManyAttempts
from app.config import settings
from app.logging import get_logger

logger = get_logger("credentials")


class InvalidMasterPassword(Exception):
    pass


class CredentialsNotFound(Exception):
    pass

class TooManyLoginAttempts(Exception):
    def __init__(self, retry_after_seconds: int):
        self.retry_after_seconds = retry_after_seconds

def show_credentials(
    server_id: int,
    port: int,
    username: str,
    master_password: str,
    client_ip: str,
):
    throttle_key = f"{username.lower()}:{client_ip}"

    # Throttle (если включён)
    if settings.LOGIN_THROTTLE_ENABLED:
        try:
            throttle.check(throttle_key)
        except TooManyAttempts:
            retry_after = throttle.time_until_unblock(throttle_key)
            raise TooManyLoginAttempts(retry_after)

    vault = VaultClient()

    # ЛОГИН В VAULT
    try:
        token = vault.login_userpass(username.lower(), master_password)
        logger.info("Vault login OK")

        if settings.LOGIN_THROTTLE_ENABLED:
            throttle.reset(throttle_key)

    except VaultAuthError:
        if settings.LOGIN_THROTTLE_ENABLED:
            throttle.register_fail(throttle_key)

        logger.warning("Vault login FAILED")
        raise InvalidMasterPassword()

    # Получаем путь
    vault_path = get_vault_path_by_server_port(server_id, port)
    if not vault_path:
        raise CredentialsNotFound()

    logger.info(f"Vault path found: {vault_path}")

    # Читаем секрет
    try:
        secret = vault.read_kv_v2(token, vault_path)
        logger.info("Vault secret read OK")
    except VaultReadError:
        raise CredentialsNotFound()

    return {
        "username": secret["username"],
        "password": secret["password"],
    }
