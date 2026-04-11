from app.services.vault_client import get_vault_client, VaultClient, VaultAuthError, VaultReadError
from app.services.db.credentials import (
    get_vault_path_by_server_port,
    upsert_vault_path,
    touch_credentials_updated_at,
)
from app.services.ssh_rotate import rotate_linux_password, SSHRotateError
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

def verify_admin_password(username: str, master_password: str, client_ip: str) -> None:
    throttle_key = f"{username.lower()}:{client_ip}"

    if settings.LOGIN_THROTTLE_ENABLED:
        try:
            throttle.check(throttle_key)
        except TooManyAttempts:
            retry_after = throttle.time_until_unblock(throttle_key)
            raise TooManyLoginAttempts(retry_after)

    vault = get_vault_client()

    try:
        vault.login_userpass(username.lower(), master_password)
        logger.info("Vault admin verify OK")

        if settings.LOGIN_THROTTLE_ENABLED:
            throttle.reset(throttle_key)

    except VaultAuthError:
        if settings.LOGIN_THROTTLE_ENABLED:
            throttle.register_fail(throttle_key)

        logger.warning("Vault admin verify FAILED")
        raise InvalidMasterPassword()


def upsert_credentials(server_id: int, port: int, username: str, password: str) -> str:
    vault_path = f"credentials/servers/{server_id}/{port}"

    vault = get_vault_client()
    vault.write_kv_v2(vault_path, {"username": username, "password": password})
    logger.info(f"Vault write OK: {vault_path}")

    upsert_vault_path(server_id, port, vault_path)
    logger.info(f"DB upsert OK: server_id={server_id} port={port}")

    return vault_path


def show_credentials(
    server_id: int,
    port: int,
    username: str,
    master_password: str,
    client_ip: str,
):
    throttle_key = f"{username.lower()}:{client_ip}"

    if settings.LOGIN_THROTTLE_ENABLED:
        try:
            throttle.check(throttle_key)
        except TooManyAttempts:
            retry_after = throttle.time_until_unblock(throttle_key)
            raise TooManyLoginAttempts(retry_after)

    vault = get_vault_client()

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

    vault_path = get_vault_path_by_server_port(server_id, port)
    if not vault_path:
        raise CredentialsNotFound()

    logger.info(f"Vault path found: {vault_path}")

    try:
        secret = vault.read_kv_v2(token, vault_path)
        logger.info("Vault secret read OK")
    except VaultReadError:
        raise CredentialsNotFound()

    return {
        "username": secret["username"],
        "password": secret["password"],
    }


class RotateError(Exception):
    pass


def rotate_credentials(
    server_id: int,
    host: str,
    ssh_port: int,
    new_password: str,
    username: str,
    master_password: str,
    client_ip: str,
) -> None:
    """
    Полный цикл ротации пароля:
    1. Верифицирует мастер-пароль
    2. Читает текущие SSH-креды из Vault (AppRole)
    3. Подключается по SSH и меняет пароль
    4. Пишет новый пароль в Vault
    5. Обновляет updated_at в Postgres
    """
    # 1. Проверяем мастер-пароль
    verify_admin_password(username, master_password, client_ip)

    vault_path = get_vault_path_by_server_port(server_id, ssh_port)
    if not vault_path:
        raise RotateError("Учётные данные для этого порта не найдены в БД")

    # 2. Читаем текущие креды через AppRole
    vault = get_vault_client()
    try:
        token = vault._get_backend_token()
        current = vault.read_kv_v2(token, vault_path)
    except VaultReadError as e:
        raise RotateError(f"Не удалось прочитать текущие креды из Vault: {e}")

    current_username = current["username"]
    current_password = current["password"]

    # 3. SSH — меняем пароль
    try:
        rotate_linux_password(
            host=host,
            username=current_username,
            current_password=current_password,
            new_password=new_password,
            port=ssh_port,
        )
    except SSHRotateError as e:
        raise RotateError(str(e))

    # 4. Пишем новый пароль в Vault
    try:
        vault.write_kv_v2(vault_path, {
            "username": current_username,
            "password": new_password,
        })
    except VaultReadError as e:
        raise RotateError(f"Пароль сменён на сервере, но не удалось записать в Vault: {e}")

    # 5. Обновляем updated_at
    touch_credentials_updated_at(server_id, ssh_port)

    logger.info(f"Password rotation complete: server_id={server_id} host={host}:{ssh_port}")