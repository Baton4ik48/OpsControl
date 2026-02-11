import requests
from app.config import settings


class VaultAuthError(Exception):
    pass


class VaultReadError(Exception):
    pass


class VaultClient:
    def __init__(self):
        self.addr = settings.VAULT_ADDR.rstrip("/")
        self.auth_mount = settings.VAULT_AUTH_METHOD
        self.backend_token = settings.VAULT_TOKEN

    # =============================
    # USER LOGIN (GUI)
    # =============================

    def login_userpass(self, username: str, password: str) -> str:
        username = username.lower()

        url = (
            f"{self.addr}"
            f"/v1/auth/{self.auth_mount}/login/{username}"
        )

        resp = requests.post(
            url,
            json={"password": password},
            headers={"Content-Type": "application/json"},
            timeout=settings.VAULT_HTTP_TIMEOUT,
        )

        if resp.status_code != 200:
            raise VaultAuthError(resp.text)

        return resp.json()["auth"]["client_token"]

    # =============================
    # READ KV WITH USER TOKEN
    # =============================

    def read_kv_v2(self, token: str, vault_path: str) -> dict:
        """
        vault_path: credentials/server_253/port_22
        """

        if not vault_path.startswith("credentials/"):
            raise VaultReadError("Invalid vault path")

        path = vault_path.replace("credentials/", "")

        url = f"{self.addr}/v1/credentials/data/{path}"

        resp = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
            },
            timeout=settings.VAULT_HTTP_TIMEOUT,
        )

        if resp.status_code != 200:
            raise VaultReadError(resp.text)

        return resp.json()["data"]["data"]


    # =============================
    # READ DATABASE CREDS (backend)
    # =============================

    def read_database_creds(self, role_name: str) -> dict:
        url = f"{self.addr}/v1/database/creds/{role_name}"

        resp = requests.get(
            url,
            headers={
                "X-Vault-Token": self.backend_token
            },
            timeout=settings.VAULT_HTTP_TIMEOUT,
        )

        if resp.status_code != 200:
            raise VaultReadError(resp.text)

        return resp.json()["data"]
