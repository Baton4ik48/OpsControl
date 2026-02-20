import logging
from dataclasses import dataclass

from app.config import settings
from app.services.vault_client import VaultClient

logger = logging.getLogger("db-creds")


# ===============================
# MODEL
# ===============================

@dataclass
class DBCreds:
    host: str
    port: int
    dbname: str
    user: str
    password: str


# ===============================
# STATIC CREDS
# ===============================

def _static_creds() -> DBCreds:
    return DBCreds(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        dbname=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
    )


# ===============================
# VAULT CREDS
# ===============================

def _get_dynamic_db_creds() -> DBCreds:
    vault = VaultClient()

    data = vault.read_database_creds()

    return DBCreds(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        dbname=settings.POSTGRES_DB,
        user=data["username"],
        password=data["password"],
    )


# ===============================
# PUBLIC ENTRYPOINT
# ===============================

def get_db_credentials() -> DBCreds:
    mode = settings.DB_CREDS_MODE

    if mode == "static":
        logger.info("DB creds mode: static")
        return _static_creds()

    if mode == "vault":
        logger.info("DB creds mode: vault")
        return _get_dynamic_db_creds()

    if mode == "auto":
        logger.info("DB creds mode: auto")
        try:
            return _get_dynamic_db_creds()
        except Exception as e:
            logger.warning(
                "Vault unavailable, falling back to static creds: %s",
                e,
            )
            return _static_creds()

    raise RuntimeError(f"Invalid DB_CREDS_MODE: {mode}")
