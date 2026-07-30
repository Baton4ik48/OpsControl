from pathlib import Path
import os
import yaml
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "config.yaml"

APP_ENV = os.getenv("APP_ENV", "dev")

load_dotenv(dotenv_path=BASE_DIR / ".env", override=(APP_ENV == "dev"))


class Settings:
    def __init__(self):
        self.VAULT_ADDR = os.getenv("VAULT_ADDR", "http://localhost:8200")
        self.VAULT_AUTH_METHOD = os.getenv("VAULT_AUTH_METHOD")
        self.VAULT_HTTP_TIMEOUT = int(os.getenv("VAULT_HTTP_TIMEOUT", 5))
        self.VAULT_ROLE_ID = os.getenv("VAULT_ROLE_ID")
        self.VAULT_SECRET_ID = os.getenv("VAULT_SECRET_ID")
        self.VAULT_DATABASE_ROLE_NAME = os.getenv("VAULT_DATABASE_ROLE_NAME")

        self.POSTGRES_HOST = os.getenv("POSTGRES_HOST")
        self.POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", 5432))
        self.POSTGRES_DB = os.getenv("POSTGRES_DB")
        self.DB_CREDS_MODE = os.getenv("DB_CREDS_MODE", "static").lower()
        self.POSTGRES_USER = os.getenv("POSTGRES_USER")
        self.POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
        self.POSTGRES_CONNECT_TIMEOUT = int(os.getenv("POSTGRES_CONNECT_TIMEOUT", 4))
        self.POSTGRES_QUERY_TIMEOUT = int(os.getenv("POSTGRES_QUERY_TIMEOUT", 7))

        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)

        self.ALLOWED_NETWORKS = yaml_data["security"].get("allowed_networks", [])
        self.TRUSTED_PROXIES = yaml_data["security"].get("trusted_proxies", [])

        login = yaml_data["security"]["login_throttle"]
        self.LOGIN_THROTTLE_ENABLED = login["enabled"]
        self.LOGIN_MAX_ATTEMPTS = login.get("max_attempts", 3)
        self.LOGIN_BLOCK_SECONDS = login.get("block_seconds", 120)

    def validate(self) -> list[str]:
        """
        Возвращает список отсутствующих обязательных переменных окружения
        с учётом выбранного DB_CREDS_MODE. Вызывается на старте приложения —
        лучше упасть сразу с понятным сообщением, чем на первом запросе.
        """
        missing: list[str] = []

        def _require(name: str):
            if not getattr(self, name):
                missing.append(name)

        _require("POSTGRES_HOST")
        _require("POSTGRES_DB")

        if self.DB_CREDS_MODE in ("static", "auto"):
            # В auto-режиме static — обязательный fallback
            _require("POSTGRES_USER")
            _require("POSTGRES_PASSWORD")

        if self.DB_CREDS_MODE == "vault":
            _require("VAULT_ROLE_ID")
            _require("VAULT_SECRET_ID")
            _require("VAULT_DATABASE_ROLE_NAME")

        return missing


settings = Settings()
