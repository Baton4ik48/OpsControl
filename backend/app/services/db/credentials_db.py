from app.services.db.pool_db import _execute


def get_vault_path_by_server_port(server_id: int, port: int) -> str | None:
    def work(conn):
        cur = conn.cursor()
        cur.execute(
            """
            SELECT vault_path
            FROM credentials
            WHERE server_id = %s
              AND port = %s
        """,
            (server_id, port),
        )

        row = cur.fetchone()
        cur.close()

        return row[0] if row else None

    return _execute(work)


def get_credentials_username(server_id: int, port: int) -> str | None:
    """Возвращает username из vault_path (не трогает Vault — только путь из БД)."""

    def work(conn):
        cur = conn.cursor()
        cur.execute(
            """
            SELECT vault_path
            FROM credentials
            WHERE server_id = %s AND port = %s
        """,
            (server_id, port),
        )
        row = cur.fetchone()
        cur.close()
        return row[0] if row else None

    return _execute(work)


def touch_credentials_updated_at(server_id: int, port: int) -> None:
    def work(conn):
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE credentials
            SET updated_at = CURRENT_TIMESTAMP
            WHERE server_id = %s AND port = %s
        """,
            (server_id, port),
        )
        conn.commit()
        cur.close()

    _execute(work)


def get_all_credentials_with_server_info() -> list[dict]:
    """Возвращает все credentials с данными сервера и филиала, отсортированные по филиалу → серверу → порту."""

    def work(conn):
        cur = conn.cursor()
        cur.execute("""
            SELECT
                b.name  AS branch_name,
                s.name  AS server_name,
                s.ip,
                s.device_type,
                c.port,
                c.vault_path,
                c.updated_at
            FROM credentials c
            JOIN servers  s ON s.id       = c.server_id
            JOIN branches b ON b.id       = s.branch_id
            ORDER BY b.name, s.name, c.port
        """)
        rows = cur.fetchall()
        cur.close()
        return [
            {
                "branch": row[0],
                "server_name": row[1],
                "ip": row[2],
                "device_type": row[3],
                "port": row[4],
                "vault_path": row[5],
                "updated_at": row[6].isoformat() if row[6] else None,
            }
            for row in rows
        ]

    return _execute(work)


def upsert_vault_path(server_id: int, port: int, vault_path: str) -> None:
    def work(conn):
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO credentials (server_id, port, vault_path, updated_at)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (server_id, port)
            DO UPDATE SET
                vault_path = EXCLUDED.vault_path,
                updated_at = CURRENT_TIMESTAMP
        """,
            (server_id, port, vault_path),
        )
        conn.commit()
        cur.close()

    _execute(work)
