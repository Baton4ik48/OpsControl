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
        self.database_role = settings.VAULT_DATABASE_ROLE_NAME

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

        data = resp.json()
        token = data["auth"]["client_token"]
        ttl = data["auth"]["lease_duration"]

        print(f"\n[DEBUG] AppRole token issued:")
        print(f"        token = {token}")
        print(f"        ttl   = {ttl}s\n")

        return token

    def _get_backend_token(self) -> str:
        # если токена нет — логинимся
        if not self._backend_token:
            self._backend_token = self._approle_login()
            return self._backend_token

        # пытаемся renew (для periodic token)
        if self._renew_token():
            return self._backend_token

        # renew не прошёл — логинимся заново
        print("[VAULT] Token renew failed → relogin")
        self._backend_token = self._approle_login()
        return self._backend_token

    def _renew_token(self) -> bool:
        url = f"{self.addr}/v1/auth/token/renew-self"

        resp = requests.post(
            url,
            headers={"X-Vault-Token": self._backend_token},
            timeout=self.http_timeout,
        )

        if resp.status_code == 200:
            ttl = resp.json()["auth"]["lease_duration"]
            print(f"[VAULT] Backend token renewed (ttl={ttl}s)")
            return True

        return False
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

    def read_database_creds(self) -> dict:
        token = self._get_backend_token()

        url = f"{self.addr}/v1/database/creds/{self.database_role}"

        resp = requests.get(
            url,
            headers={"X-Vault-Token": token},
            timeout=self.http_timeout,
        )

        if resp.status_code != 200:
            raise VaultReadError(resp.text)
        
        body = resp.json()

        username = body["data"]["username"]
        lease_id = body["lease_id"]
        ttl = body["lease_duration"]

        print(f"\n[VAULT] NEW DB CREDS ISSUED")
        print(f"        username = {username}")
        print(f"        lease_id = {lease_id}")
        print(f"        ttl      = {ttl}s\n")

        return body["data"]

