from app.services.db.pool import _execute


# ==========================
# READ
# ==========================

def get_vault_path_by_server_port(server_id: int, port: int) -> str | None:
    def work(conn):
        cur = conn.cursor()
        cur.execute("""
            SELECT vault_path
            FROM credentials
            WHERE server_id = %s
              AND port = %s
        """, (server_id, port))

        row = cur.fetchone()
        cur.close()

        return row[0] if row else None

    return _execute(work)