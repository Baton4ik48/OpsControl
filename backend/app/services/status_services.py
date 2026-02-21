import requests
from app.services.db.pool import _execute
from app.config import settings


def get_overall_status() -> str:
    postgres_ok = check_postgres()
    vault_ok = check_vault()

    if postgres_ok and vault_ok:
        return "ok"

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

    except Exception:
        return False


# ==========================
# VAULT HEALTH
# ==========================

def check_vault() -> bool:
    try:
        r = requests.get(
            f"{settings.VAULT_ADDR}/v1/sys/health",
            timeout=settings.VAULT_HTTP_TIMEOUT,
        )
        return r.status_code == 200

    except Exception:
        return False