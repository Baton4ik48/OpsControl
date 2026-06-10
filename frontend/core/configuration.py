import os
from dotenv import load_dotenv
from pathlib import Path
from core.config.user_settings import UserSettings

FRONTEND_DIR = Path(__file__).resolve().parent.parent

APP_ENV = os.getenv("APP_ENV", "dev")

load_dotenv(dotenv_path=FRONTEND_DIR / ".env", override=(APP_ENV == "dev"))

print("ENV BACKEND_SCHEME =", os.getenv("BACKEND_SCHEME"))
print("ENV BACKEND_HOST =", os.getenv("BACKEND_HOST"))
print("ENV BACKEND_PORT =", os.getenv("BACKEND_PORT"))

class Settings:
    def __init__(self):
        self._user = UserSettings()

        self._env_scheme = os.getenv("BACKEND_SCHEME", "http")
        self._env_host = os.getenv("BACKEND_HOST", "localhost")
        self._env_port = int(os.getenv("BACKEND_PORT", 8443))

    @property
    def BACKEND_BASE_URL(self) -> str:
        if self._user.get("backend_override_enabled"):
            scheme = self._user.get("backend_scheme") or self._env_scheme
            host = self._user.get("backend_host") or self._env_host
            port = self._user.get("backend_port") or self._env_port
        else:
            scheme = self._env_scheme
            host = self._env_host
            port = self._env_port

        return f"{scheme}://{host}:{port}"

settings = Settings()
