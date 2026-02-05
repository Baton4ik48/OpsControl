import requests
from psycopg2 import OperationalError
from app.services.postgres import pool
from app.config import settings


def get_overall_status() -> str:
    postgres_ok = check_postgres()
    vault_ok = check_vault()

    if postgres_ok and vault_ok:
        return "ok"

    return "degraded"

def check_postgres() -> bool:
    conn = None
    try:
        conn = pool.getconn()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
        return True

    except OperationalError:
        return False

    except Exception:
        return False

    finally:
        if conn:
            try:
                pool.putconn(conn)
            except Exception:
                pass

def check_vault() -> bool:
    try:
        r = requests.get(
            f"{settings.VAULT_ADDR}/v1/sys/health",
            timeout=1,
        )
        return r.status_code == 200
    except Exception:
        return False
