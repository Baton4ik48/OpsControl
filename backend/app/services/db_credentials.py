import logging
from dataclasses import dataclass

from app.config import settings
from app.services.vault_client import (
    get_vault_client,
    VaultSealedError,
    VaultUnavailableError,
    VaultAuthError,
    VaultReadError,
)

logger = logging.getLogger("db-creds")


@dataclass
class DBCreds:
    host: str
    port: int
    dbname: str
    user: str
    password: str


def _static_creds() -> DBCreds:
    return DBCreds(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        dbname=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
    )


def _get_dynamic_db_creds() -> DBCreds:
    vault = get_vault_client()
    try:
        data = vault.read_database_creds()
    except VaultSealedError as e:
        logger.error("Vault запечатан — невозможно получить DB creds: %s", e)
        raise
    except VaultAuthError as e:
        logger.error(
            "Vault AppRole: неверные role_id/secret_id в .env — "
            "обновите VAULT_ROLE_ID / VAULT_SECRET_ID и перезапустите бэкенд. Ошибка: %s",
            e,
        )
        raise
    except VaultReadError as e:
        logger.error("Vault: не удалось прочитать DB creds (database role?): %s", e)
        raise
    except VaultUnavailableError as e:
        logger.error("Vault недоступен: %s", e)
        raise
    except Exception as e:
        logger.error("Неожиданная ошибка при получении DB creds из Vault: %s", e)
        raise

    return DBCreds(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        dbname=settings.POSTGRES_DB,
        user=data["username"],
        password=data["password"],
    )


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
