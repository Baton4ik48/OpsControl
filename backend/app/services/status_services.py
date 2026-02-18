import requests
from psycopg2 import OperationalError
from app.services import postgres
from app.config import settings


def get_overall_status() -> str:
    postgres_ok = check_postgres()
    vault_ok = check_vault()

    # print(f"Postgres {postgres_ok}")
    # print(f"vault{vault_ok}")
    
    if postgres_ok and vault_ok:
        return "ok"

    return "degraded"

def check_postgres() -> bool:
    if not postgres.is_ready():
        return False

    conn = None
    try:
        conn = postgres.pool.getconn()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
        return True

    except Exception:
        return False

    finally:
        if conn:
            try:
                postgres.pool.putconn(conn)
            except Exception:
                pass


def check_vault() -> bool:
    try:
        r = requests.get(
            f"{settings.VAULT_ADDR}/v1/sys/health",
            timeout=settings.VAULT_HTTP_TIMEOUT,)
        return r.status_code == 200
    except Exception:
        return False
