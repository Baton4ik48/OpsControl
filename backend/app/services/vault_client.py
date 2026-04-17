import requests
from app.config import settings


class VaultAuthError(Exception):
    pass


class VaultReadError(Exception):
    pass


class VaultSealedError(Exception):
    """Vault запечатан — нужна ручная операция unseal."""

    pass


class VaultUnavailableError(Exception):
    """Vault недоступен по сети или вернул неожиданный статус."""

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

    def check_sealed(self) -> None:
        """Бросает VaultSealedError или VaultUnavailableError если Vault недоступен."""
        try:
            resp = requests.get(
                f"{self.addr}/v1/sys/health",
                timeout=self.http_timeout,
            )
        except requests.exceptions.ConnectionError:
            raise VaultUnavailableError(f"Vault недоступен по адресу {self.addr}")
        except requests.exceptions.Timeout:
            raise VaultUnavailableError(f"Vault не ответил за {self.http_timeout}с")

        # 200 = healthy, 429 = standby (тоже ОК), 501 = не инициализирован, 503 = запечатан
        if resp.status_code == 503:
            raise VaultSealedError("Vault запечатан (sealed) — выполните unseal")
        if resp.status_code == 501:
            raise VaultUnavailableError("Vault не инициализирован")
        if resp.status_code not in (200, 429, 472, 473):
            raise VaultUnavailableError(f"Vault /sys/health вернул {resp.status_code}")

    def _approle_login(self) -> str:
        self.check_sealed()

        url = f"{self.addr}/v1/auth/approle/login"

        try:
            resp = requests.post(
                url,
                json={
                    "role_id": self.role_id,
                    "secret_id": self.secret_id,
                },
                timeout=self.http_timeout,
            )
        except requests.exceptions.RequestException as e:
            raise VaultUnavailableError(f"Не удалось подключиться к Vault: {e}")

        # Обработка HTTP-статусов
        if resp.status_code == 400:
            raise VaultAuthError(
                "AppRole: неверный role_id или secret_id — проверьте .env"
            )
        if resp.status_code != 200:
            raise VaultUnavailableError(
                f"AppRole login вернул {resp.status_code}: {resp.text}"
            )

        try:
            data = resp.json()
            token = data["auth"]["client_token"]
            ttl = data["auth"]["lease_duration"]
        except (ValueError, KeyError) as e:
            # ValueError - битый JSON, KeyError - нет нужного поля
            raise VaultUnavailableError(f"Некорректный ответ Vault: {e}")

        print("\n[DEBUG] AppRole token issued:")
        print(f"        token = {token}")
        print(f"        ttl   = {ttl}s\n")

        return token

    def _get_backend_token(self) -> str:
        if not self._backend_token:
            self._backend_token = self._approle_login()
            return self._backend_token

        if self._renew_token():
            return self._backend_token

        print("[VAULT] Token renew failed → relogin")
        self._backend_token = self._approle_login()
        return self._backend_token

    def _renew_token(self) -> bool:
        url = f"{self.addr}/v1/auth/token/renew-self"

        try:
            resp = requests.post(
                url,
                headers={"X-Vault-Token": self._backend_token},
                timeout=self.http_timeout,
            )
        except requests.exceptions.RequestException:
            return False

        if resp.status_code != 200:
            return False

        try:
            ttl = resp.json()["auth"]["lease_duration"]
        except (ValueError, KeyError):
            return False

        print(f"[VAULT] Backend token renewed (ttl={ttl}s)")
        return True

    # ==========================================
    # USER LOGIN (GUI → Vault userpass)
    # ==========================================

    def login_userpass(self, username: str, password: str) -> str:
        username = username.lower()
        url = f"{self.addr}/v1/auth/userpass/login/{username}"

        try:
            resp = requests.post(
                url,
                json={"password": password},
                timeout=self.http_timeout,
            )
        except requests.exceptions.RequestException as e:
            raise VaultUnavailableError(f"Vault недоступен: {e}") from e

        if resp.status_code != 200:
            raise VaultAuthError(resp.text)

        try:
            data = resp.json()
        except ValueError as e:
            raise VaultUnavailableError("Некорректный JSON от Vault") from e

        try:
            return data["auth"]["client_token"]
        except KeyError as e:
            raise VaultAuthError("Vault не вернул client_token") from e

    # ==========================================
    # READ KV (user token)
    # ==========================================
    def read_kv_v2(self, token: str, vault_path: str) -> dict:
        if not vault_path.startswith("credentials/"):
            raise VaultReadError("Invalid vault path")

        path = vault_path.replace("credentials/", "")
        url = f"{self.addr}/v1/credentials/data/{path}"

        try:
            resp = requests.get(
                url,
                headers={"X-Vault-Token": token},
                timeout=self.http_timeout,
            )
        except requests.exceptions.Timeout:
            raise VaultReadError(f"Vault не ответил за {self.http_timeout}с")
        except requests.exceptions.RequestException as e:
            raise VaultReadError(f"Vault недоступен: {e}") from e

        if resp.status_code != 200:
            raise VaultReadError(resp.text)

        if not resp.content:
            raise VaultReadError("Пустой ответ от Vault")

        try:
            data = resp.json()
        except ValueError as e:
            raise VaultReadError("Vault вернул невалидный JSON") from e

        try:
            return data["data"]["data"]
        except KeyError as e:
            raise VaultReadError("Некорректная структура ответа Vault") from e

    # ==========================================
    # WRITE KV (backend AppRole token)
    # ==========================================

    def write_kv_v2(self, vault_path: str, data: dict) -> None:
        if not vault_path.startswith("credentials/"):
            raise VaultReadError("Invalid vault path")

        token = self._get_backend_token()
        path = vault_path.replace("credentials/", "")
        url = f"{self.addr}/v1/credentials/data/{path}"

        try:
            resp = requests.post(
                url,
                headers={"X-Vault-Token": token},
                json={"data": data},
                timeout=self.http_timeout,
            )
        except requests.exceptions.RequestException as e:
            raise VaultReadError(f"Vault недоступен: {e}") from e

        if resp.status_code not in (200, 204):
            raise VaultReadError(resp.text)

    # ==========================================
    # DATABASE CREDS (backend token)
    # ==========================================

    def read_database_creds(self) -> dict:
        token = self._get_backend_token()
        url = f"{self.addr}/v1/database/creds/{self.database_role}"

        try:
            resp = requests.get(
                url,
                headers={"X-Vault-Token": token},
                timeout=self.http_timeout,
            )
        except requests.exceptions.RequestException as e:
            raise VaultReadError(f"Vault недоступен: {e}") from e

        if resp.status_code != 200:
            raise VaultReadError(resp.text)

        try:
            body = resp.json()
            username = body["data"]["username"]
            lease_id = body["lease_id"]
            ttl = body["lease_duration"]
        except (ValueError, KeyError) as e:
            raise VaultReadError(f"Malformed Vault response: {e}") from e

        print("\n[VAULT] NEW DB CREDS ISSUED")
        print(f"        username = {username}")
        print(f"        lease_id = {lease_id}")
        print(f"        ttl      = {ttl}s\n")

        return body["data"]


_vault_instance = None


def get_vault_client() -> VaultClient:
    global _vault_instance
    if _vault_instance is None:
        _vault_instance = VaultClient()
    return _vault_instance
