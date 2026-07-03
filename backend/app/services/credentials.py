from app.services.vault_client import get_vault_client, VaultAuthError, VaultReadError
from app.services.db.credentials_db import (
    get_vault_path_by_server_port,
    upsert_vault_path,
    touch_credentials_updated_at,
    get_all_credentials_with_server_info,
)
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


class RotateError(Exception):
    pass


def _login_with_throttle(username: str, master_password: str, client_ip: str) -> str:
    """
    Единая точка аутентификации пользователя в Vault с учётом троттлинга.

    Возвращает пользовательский Vault-токен.
    Бросает TooManyLoginAttempts или InvalidMasterPassword.
    """
    username = username.lower()
    throttle_key = f"{username}:{client_ip}"

    if settings.LOGIN_THROTTLE_ENABLED:
        try:
            throttle.check(throttle_key)
        except TooManyAttempts:
            retry_after = throttle.time_until_unblock(throttle_key)
            raise TooManyLoginAttempts(retry_after)

    vault = get_vault_client()

    try:
        token = vault.login_userpass(username, master_password)
    except VaultAuthError:
        if settings.LOGIN_THROTTLE_ENABLED:
            throttle.register_fail(throttle_key)

        logger.warning("Vault login FAILED")
        raise InvalidMasterPassword()

    if settings.LOGIN_THROTTLE_ENABLED:
        throttle.reset(throttle_key)

    logger.info("Vault login OK")
    return token


def verify_admin_password(username: str, master_password: str, client_ip: str) -> None:
    _login_with_throttle(username, master_password, client_ip)


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
    token = _login_with_throttle(username, master_password, client_ip)

    vault_path = get_vault_path_by_server_port(server_id, port)
    if not vault_path:
        raise CredentialsNotFound()

    logger.info(f"Vault path found: {vault_path}")

    vault = get_vault_client()
    try:
        secret = vault.read_kv_v2(token, vault_path)
        logger.info("Vault secret read OK")
    except VaultReadError:
        raise CredentialsNotFound()

    return {
        "username": secret["username"],
        "password": secret["password"],
        "mnemonic": secret.get("mnemonic", ""),
    }


def export_all_credentials(
    username: str,
    master_password: str,
    client_ip: str,
) -> list[dict]:
    """
    Authenticates user against Vault, then reads every stored secret.
    Returns a list of dicts with branch/server/ip/port/username/password/mnemonic.
    Entries whose vault_path cannot be read are skipped with a warning.
    """
    token = _login_with_throttle(username, master_password, client_ip)

    vault = get_vault_client()
    rows = get_all_credentials_with_server_info()
    result = []
    for row in rows:
        try:
            secret = vault.read_kv_v2(token, row["vault_path"])
            result.append(
                {
                    "branch": row["branch"],
                    "server_name": row["server_name"],
                    "ip": row["ip"],
                    "port": row["port"],
                    "username": secret.get("username", ""),
                    "password": secret.get("password", ""),
                    "mnemonic": secret.get("mnemonic", ""),
                    "updated_at": row["updated_at"],
                }
            )
        except VaultReadError:
            logger.warning(
                "export_all: vault read skipped path=%s server=%s",
                row["vault_path"],
                row["server_name"],
            )

    logger.info("export_all done: %d entries returned", len(result))
    return result


def rotate_credentials(
    server_id: int,
    ssh_port: int,
    new_password: str,
    username: str,
    master_password: str,
    client_ip: str,
    mnemonic: str = "",
) -> None:
    """
    Сохраняет новый пароль в Vault после того, как фронтенд уже сменил его по SSH.
    1. Верифицирует мастер-пароль
    2. Читает vault_path из БД
    3. Получает текущий username из Vault (AppRole)
    4. Пишет новый пароль в Vault
    5. Обновляет updated_at в Postgres
    """
    # 1. Проверяем мастер-пароль
    verify_admin_password(username, master_password, client_ip)

    vault_path = get_vault_path_by_server_port(server_id, ssh_port)
    if not vault_path:
        raise RotateError("Учётные данные для этого порта не найдены в БД")

    # 2. Получаем текущий username из Vault (он не меняется)
    vault = get_vault_client()
    try:
        current = vault.read_kv_v2_as_backend(vault_path)
    except VaultReadError as e:
        logger.error("rotate: vault read failed path=%s: %s", vault_path, e)
        raise RotateError("Vault read error")

    current_username = current["username"]

    # 3. Пишем новый пароль и мнемонику в Vault
    try:
        vault.write_kv_v2(
            vault_path,
            {
                "username": current_username,
                "password": new_password,
                "mnemonic": mnemonic,
            },
        )
    except VaultReadError as e:
        logger.error("rotate: vault write failed path=%s: %s", vault_path, e)
        raise RotateError("Vault write error")

    # 4. Обновляем updated_at
    touch_credentials_updated_at(server_id, ssh_port)

    logger.info(f"Vault password updated: server_id={server_id} port={ssh_port}")
