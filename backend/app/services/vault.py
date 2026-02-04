import requests
from app.config import settings
from app.logging import get_logger

logger = get_logger("vault")

class VaultAuthError(Exception):
    pass


class VaultReadError(Exception):
    pass


def vault_login_userpass(username: str, password: str) -> str:
    url = f"{settings.VAULT_ADDR}/v1/auth/userpass/login/{username}"

    logger.info("Vault login attempt", extra={
        "addr": settings.VAULT_ADDR,
        "username": username,
    })

    resp = requests.post(
        url,
        json={"password": password},
        timeout=5,
    )

    logger.info("Vault login response", extra={
        "status": resp.status_code,
        "body": resp.text,
    })

    if resp.status_code != 200:
        raise VaultAuthError(resp.text)

    return resp.json()["auth"]["client_token"]


def vault_read_secret(token: str, vault_path: str) -> dict:

    print(f"vault_read_secret {settings.VAULT_ADDR}")
    """
    GET /v1/credentials/data/server_253/port_22
    """
    url = f"{settings.VAULT_ADDR}{vault_path}"

    resp = requests.get(
        url,
        headers={"X-Vault-Token": token},
        timeout=5,
    )

    if resp.status_code != 200:
        raise VaultReadError("Failed to read secret")

    return resp.json()["data"]["data"]
