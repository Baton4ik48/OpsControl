from pathlib import Path
import os
import yaml
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent

APP_ENV = os.getenv("APP_ENV", "dev")

load_dotenv(
    dotenv_path=BASE_DIR / ".env",
    override=(APP_ENV == "dev")
)

print("ENV VAULT_ADDR =", os.getenv("VAULT_ADDR"))
print("ENV VAULT_AUTH_METHOD =", os.getenv("VAULT_AUTH_METHOD"))
print("ENV POSTGRES_HOST =", os.getenv("POSTGRES_HOST"))
print("ENV POSTGRES_PORT =", os.getenv("POSTGRES_PORT"))
print("ENV USE_VAULT_DB_CREDS =", os.getenv("USE_VAULT_DB_CREDS"))




BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "config.yaml"

class Settings:
    def __init__(self):
        self.VAULT_ADDR = os.getenv("VAULT_ADDR", "localhost")
        self.VAULT_AUTH_METHOD = os.getenv("VAULT_AUTH_METHOD")
        self.VAULT_HTTP_TIMEOUT = int(os.getenv("VAULT_HTTP_TIMEOUT", 1))
        self.VAULT_TOKEN = os.getenv("VAULT_TOKEN")
        
        self.POSTGRES_HOST = os.getenv("POSTGRES_HOST")
        self.POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", 5432))
        self.POSTGRES_DB = os.getenv("POSTGRES_DB")
        self.DB_CREDS_MODE = os.getenv("DB_CREDS_MODE", "static").lower()
        self.POSTGRES_USER = os.getenv("POSTGRES_USER")
        self.POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
        self.POSTGRES_CONNECT_TIMEOUT = int(os.getenv("POSTGRES_CONNECT_TIMEOUT", 1))
        self.POSTGRES_QUERY_TIMEOUT = int(os.getenv("POSTGRES_QUERY_TIMEOUT", 3))

        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)

        self.ALLOWED_NETWORKS = yaml_data["security"].get("allowed_networks", [])

        login = yaml_data["security"]["login_throttle"]
        self.LOGIN_THROTTLE_ENABLED = login["enabled"]
        self.LOGIN_MAX_ATTEMPTS = login.get("max_attempts", 3)
        self.LOGIN_BLOCK_SECONDS = login.get("block_seconds", 120)

settings = Settings()
