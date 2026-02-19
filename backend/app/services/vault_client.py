import requests
from app.config import settings


class VaultAuthError(Exception):
    pass


class VaultReadError(Exception):
    pass


class VaultClient:
    def __init__(self):
        self.addr = settings.VAULT_ADDR.rstrip("/")
        self.http_timeout = settings.VAULT_HTTP_TIMEOUT
        self.role_id = settings.VAULT_ROLE_ID
        self.secret_id = settings.VAULT_SECRET_ID

        self._backend_token = None

    # ==========================================
    # APPROLE LOGIN (для backend)
    # ==========================================

    def _approle_login(self) -> str:
        url = f"{self.addr}/v1/auth/approle/login"

        resp = requests.post(
            url,
            json={
                "role_id": self.role_id,
                "secret_id": self.secret_id,
            },
            timeout=self.http_timeout,
        )

        if resp.status_code != 200:
            raise VaultAuthError(resp.text)

        return resp.json()["auth"]["client_token"]

    def _get_backend_token(self) -> str:
        if not self._backend_token:
            self._backend_token = self._approle_login()
        return self._backend_token

    # ==========================================
    # USER LOGIN (GUI → Vault userpass)
    # ==========================================

    def login_userpass(self, username: str, password: str) -> str:
        username = username.lower()

        url = (
            f"{self.addr}"
            f"/v1/auth/userpass/login/{username}"
        )

        resp = requests.post(
            url,
            json={"password": password},
            timeout=self.http_timeout,
        )

        if resp.status_code != 200:
            raise VaultAuthError(resp.text)

        return resp.json()["auth"]["client_token"]

    # ==========================================
    # READ KV (user token)
    # ==========================================

    def read_kv_v2(self, token: str, vault_path: str) -> dict:
        if not vault_path.startswith("credentials/"):
            raise VaultReadError("Invalid vault path")

        path = vault_path.replace("credentials/", "")
        url = f"{self.addr}/v1/credentials/data/{path}"

        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=self.http_timeout,
        )

        if resp.status_code != 200:
            raise VaultReadError(resp.text)

        return resp.json()["data"]["data"]

    # ==========================================
    # DATABASE CREDS (backend token)
    # ==========================================

    def read_database_creds(self, role_name: str) -> dict:
        token = self._get_backend_token()

        url = f"{self.addr}/v1/database/creds/{role_name}"

        resp = requests.get(
            url,
            headers={"X-Vault-Token": token},
            timeout=self.http_timeout,
        )

        if resp.status_code != 200:
            raise VaultReadError(resp.text)

        return resp.json()["data"]
