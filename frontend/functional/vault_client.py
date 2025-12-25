import hvac

class VaultClient:
    def __init__(self, url: str, ca_cert: str):
        self.client = hvac.Client(
            url=url,
            verify=ca_cert
        )

    def login_approle(self, role_id: str, secret_id: str):
        return self.client.auth.approle.login(
            role_id=role_id,
            secret_id=secret_id
        )

    def is_authenticated(self) -> bool:
        return self.client.is_authenticated()

    def read_secret(self, path: str) -> dict:
        return self.client.secrets.kv.v2.read_secret_version(
            path=path
        )["data"]["data"]
