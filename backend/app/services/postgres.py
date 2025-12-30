from psycopg2.pool import SimpleConnectionPool
from psycopg2 import OperationalError
from app.config import settings


# ==================================================
# CONNECTION POOL
# ==================================================

pool = SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    host=settings.POSTGRES_HOST,
    port=settings.POSTGRES_PORT,
    dbname=settings.POSTGRES_DB,
    user=settings.POSTGRES_USER,
    password=settings.POSTGRES_PASSWORD,
    connect_timeout=5,
)


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
                # битое соединение — выкидываем
                try:
                    pool.putconn(conn, close=True)
                except Exception:
                    pass

        finally:
            if conn:
                try:
                    pool.putconn(conn)
                except Exception:
                    pass

    # если не получилось даже после retry
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
                p.last_failure
            FROM branches b
            JOIN servers s ON s.branch_id = b.id
            LEFT JOIN ports p ON p.server_id = s.id
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
