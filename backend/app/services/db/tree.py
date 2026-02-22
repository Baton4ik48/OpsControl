from app.services.db.pool import _execute


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
            c.updated_at,
            c.vault_path
        FROM branches b
        LEFT JOIN servers s ON s.branch_id = b.id
        LEFT JOIN ports p ON p.server_id = s.id
        LEFT JOIN credentials c
            ON c.server_id = s.id AND c.port = p.port
        ORDER BY b.name, s.name, p.port
        """)
        rows = cur.fetchall()
        cur.close()
        return rows

    return _execute(work)