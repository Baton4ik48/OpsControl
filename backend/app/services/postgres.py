from psycopg2.pool import SimpleConnectionPool
from psycopg2 import OperationalError
from app.config import settings
import time
import logging
from app.services.db_credentials import get_db_credentials

logger = logging.getLogger("postgres")

# ==================================================
# CONNECTION POOL
# ==================================================
pool: SimpleConnectionPool | None = None



def init_pool(retries: int = 5, delay: int = 2):
    global pool
    creds = get_db_credentials()
    for attempt in range(1, retries + 1):
        try:
            pool = SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                host=creds.host,
                port=creds.port,
                dbname=creds.dbname,
                user=creds.user,
                password=creds.password,
                connect_timeout=settings.POSTGRES_CONNECT_TIMEOUT,
                options=f"-c statement_timeout={settings.POSTGRES_QUERY_TIMEOUT * 1000}",
                
            )
            logger.info("PostgreSQL pool initialized")
            return

        except OperationalError as e:
            logger.warning(
                f"PostgreSQL connection failed "
                f"(attempt {attempt}/{retries}): {e}"
            )
            time.sleep(delay)

    raise RuntimeError("PostgreSQL unavailable after retries")


def is_ready() -> bool:
    return pool is not None


def close_pool():
    global pool
    if pool:
        pool.closeall()
        pool = None


# ==================================================
# SAFE EXECUTOR (RETRY-BASED)
# ==================================================

def _execute(fn, retries: int = 1):
    last_exc = None

    for _ in range(retries + 1):
        conn = None
        try:
            conn = pool.getconn()
            return fn(conn)

        except OperationalError as e:
            last_exc = e
            if conn:
                pool.putconn(conn, close=True)
                conn = None

        finally:
            if conn:
                pool.putconn(conn)

    raise last_exc


# ==================================================
# READ OPERATIONS
# ==================================================

def load_branches():
    def work(conn):
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM branches ORDER BY name")
        rows = cur.fetchall()
        cur.close()
        return rows

    return _execute(work)


def load_servers(branch_id: int):
    def work(conn):
        cur = conn.cursor()
        cur.execute("""
            SELECT id, name, ip
            FROM servers
            WHERE branch_id = %s
            ORDER BY name
        """, (branch_id,))
        rows = cur.fetchall()
        cur.close()
        return rows

    return _execute(work)


def load_ports(server_id: int):
    def work(conn):
        cur = conn.cursor()
        cur.execute("""
            SELECT port, last_success, last_failure
            FROM ports
            WHERE server_id = %s
            ORDER BY port
        """, (server_id,))
        rows = cur.fetchall()
        cur.close()
        return [
            {
                "port": r[0],
                "last_success": r[1],
                "last_failure": r[2],
            }
            for r in rows
        ]

    return _execute(work)


def load_tree():
    def work(conn):
        cur = conn.cursor()
        cur.execute("""
            SELECT
                b.id,
                b.name,
                s.id,
                s.name,
                s.ip,
                p.port,
                p.last_success,
                p.last_failure,
                c.id AS cred_id,
                c.updated_at
            FROM branches b
            JOIN servers s ON s.branch_id = b.id
            LEFT JOIN ports p ON p.server_id = s.id
            LEFT JOIN credentials c ON c.server_id = s.id AND c.port = p.port
            ORDER BY b.name, s.name, p.port
        """)
        rows = cur.fetchall()
        cur.close()
        return rows

    return _execute(work)


# ==================================================
# WRITE OPERATIONS
# ==================================================

def update_server_name(server_id: int, new_name: str) -> int:
    def work(conn):
        cur = conn.cursor()
        cur.execute(
            "UPDATE servers SET name = %s WHERE id = %s",
            (new_name, server_id)
        )
        affected = cur.rowcount
        conn.commit()
        cur.close()
        return affected

    return _execute(work)


def update_server_ip(server_id: int, new_ip: str) -> int:
    def work(conn):
        cur = conn.cursor()
        cur.execute(
            "UPDATE servers SET ip = %s WHERE id = %s",
            (new_ip, server_id)
        )
        affected = cur.rowcount
        conn.commit()
        cur.close()
        return affected

    return _execute(work)


def report_port_result(server_id: int, port: int, ok: bool) -> int:
    def work(conn):
        cur = conn.cursor()
        if ok:
            cur.execute("""
                UPDATE ports
                SET last_success = CURRENT_TIMESTAMP
                WHERE server_id = %s AND port = %s
            """, (server_id, port))
        else:
            cur.execute("""
                UPDATE ports
                SET last_failure = CURRENT_TIMESTAMP
                WHERE server_id = %s AND port = %s
            """, (server_id, port))

        affected = cur.rowcount
        conn.commit()
        cur.close()
        return affected

    return _execute(work)


def get_vault_path_by_server_port(server_id: int, port: int) -> str | None:
    def work(conn):
        cur = conn.cursor()
        cur.execute("""
            SELECT vault_path
            FROM credentials
            WHERE server_id = %s AND port = %s
        """, (server_id, port))
        row = cur.fetchone()
        cur.close()
        return row[0] if row else None

    return _execute(work)
