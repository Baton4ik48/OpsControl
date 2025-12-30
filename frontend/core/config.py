import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    BACKEND_SCHEME = os.getenv("BACKEND_SCHEME", "http")
    BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
    BACKEND_PORT = int(os.getenv("BACKEND_PORT", 8443))

    @property
    def BACKEND_BASE_URL(self) -> str:
        return f"{self.BACKEND_SCHEME}://{self.BACKEND_HOST}:{self.BACKEND_PORT}"

settings = Settings()
