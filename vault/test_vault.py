from functional.vault_client import VaultClient
import os


vault = VaultClient(
    url="https://localhost:8200",
    ca_cert="C:/Users/user/Desktop/AutoManager/project/bin/ca.crt"
)

vault.login_approle(
    role_id=os.environ["VAULT_ROLE_ID"],
    secret_id=os.environ["VAULT_SECRET_ID"]
)

print("AUTH:", vault.is_authenticated())

secret = vault.read_secret("infra/switches/switch1")
print(secret)
