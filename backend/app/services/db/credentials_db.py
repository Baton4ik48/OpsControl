from app.services.db.pool_db import _execute

# ==========================
# READ
# ==========================


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


# ==========================
# READ USERNAME
# ==========================


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


# ==========================
# TOUCH updated_at
# ==========================


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


# ==========================
# UPSERT
# ==========================


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
