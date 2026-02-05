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


print("ENV BACKEND_HOST =", os.getenv("BACKEND_HOST"))
print("ENV BACKEND_PORT =", os.getenv("BACKEND_PORT"))
print("ENV VAULT_ADDR =", os.getenv("VAULT_ADDR"))
print("ENV VAULT_AUTH_METHOD =", os.getenv("VAULT_AUTH_METHOD"))
print("ENV POSTGRES_HOST =", os.getenv("POSTGRES_HOST"))
print("ENV POSTGRES_PORT =", os.getenv("POSTGRES_PORT"))



BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "config.yaml"

class Settings:
    BACKEND_HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
    BACKEND_PORT = int(os.getenv("BACKEND_PORT", 8443))

    VAULT_ADDR = os.getenv("VAULT_ADDR", "localhost")
    VAULT_AUTH_METHOD = os.getenv("VAULT_AUTH_METHOD")

    POSTGRES_HOST = os.getenv("POSTGRES_HOST")
    POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", 5432))
    POSTGRES_DB = os.getenv("POSTGRES_DB")
    POSTGRES_USER = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        YAML = yaml.safe_load(f)

    LOGIN_THROTTLE_ENABLED = YAML["security"]["login_throttle"]["enabled"]
    LOGIN_MAX_ATTEMPTS = YAML["security"]["login_throttle"].get("max_attempts", 3)
    LOGIN_BLOCK_SECONDS = YAML["security"]["login_throttle"].get("block_seconds", 120)


settings = Settings()
