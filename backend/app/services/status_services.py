from app.services.db.pool_db import _execute, ServiceUnavailableError
from app.services.vault_client import VaultSealedError, VaultUnavailableError


def get_overall_status() -> str:
    postgres_ok = check_postgres()
    vault_status = check_vault()

    if postgres_ok and vault_status == "ok":
        return "ok"

    if vault_status == "sealed":
        return "degraded"

    return "degraded"


# ==========================
# POSTGRES HEALTH
# ==========================


def check_postgres() -> bool:
    try:

        def work(conn):
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
            cur.close()

        _execute(work)
        return True

    except (ServiceUnavailableError, Exception):
        return False


# ==========================
# VAULT HEALTH
# ==========================


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
