from app.services.db.pool_db import execute, ServiceUnavailableError
from app.services.vault_client import VaultSealedError, VaultUnavailableError


def get_overall_status() -> str:
    """Возвращает: 'ok' | 'degraded' | 'unavailable'"""
    postgres_ok = check_postgres()
    vault_status = check_vault()

    if postgres_ok and vault_status == "ok":
        return "ok"

    if not postgres_ok and vault_status in ("offline", "sealed"):
        return "unavailable"

    return "degraded"


def check_postgres() -> bool:
    try:

        def work(conn):
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
            cur.close()

        execute(work)
        return True

    except (ServiceUnavailableError, Exception):
        return False


def check_vault() -> str:
    """Возвращает: 'ok' | 'sealed' | 'offline'"""
    try:
        from app.services.vault_client import get_vault_client

        get_vault_client().check_sealed()
        return "ok"
    except VaultSealedError:
        return "sealed"
    except (VaultUnavailableError, Exception):
        return "offline"
