from app.services.db.pool import _execute


# ==========================
# READ
# ==========================

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


# ==========================
# CREATE
# ==========================

def create_port(server_id: int, port: int) -> int:
    def work(conn):
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO ports (server_id, port)
                VALUES (%s, %s)
            """, (server_id, port))
            conn.commit()
        except Exception as e:
            print("DB EXCEPTION:", type(e), e)
            raise
        finally:
            cur.close()
        return 1

    return _execute(work)


# ==========================
# UPDATE
# ==========================

def update_port(server_id: int, old_port: int, new_port: int) -> int:
    def work(conn):
        cur = conn.cursor()

        if old_port == new_port:
            cur.close()
            return 1

        cur.execute("""
            DELETE FROM credentials
            WHERE server_id = %s AND port = %s
        """, (server_id, old_port))

        cur.execute("""
            UPDATE ports
            SET port = %s
            WHERE server_id = %s
              AND port = %s
        """, (new_port, server_id, old_port))

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
                SET last_success = (NOW() AT TIME ZONE 'UTC')
                WHERE server_id = %s AND port = %s
            """, (server_id, port))
        else:
            cur.execute("""
                UPDATE ports
                SET last_failure = (NOW() AT TIME ZONE 'UTC')
                WHERE server_id = %s AND port = %s
            """, (server_id, port))

        affected = cur.rowcount
        conn.commit()
        cur.close()
        return affected

    return _execute(work)


def update_vault_path(server_id: int, port: int, new_path: str) -> int:
    def work(conn):
        cur = conn.cursor()

        cleaned_path = (new_path or "").strip()

        if cleaned_path == "":
            cur.execute("""
                DELETE FROM credentials
                WHERE server_id = %s AND port = %s
            """, (server_id, port))

            conn.commit()
            cur.close()
            return 1

        cur.execute("""
            INSERT INTO credentials (server_id, port, vault_path)
            VALUES (%s, %s, %s)
            ON CONFLICT (server_id, port)
            DO UPDATE SET
                vault_path = EXCLUDED.vault_path,
                updated_at = (NOW() AT TIME ZONE 'UTC')
        """, (server_id, port, cleaned_path))

        conn.commit()
        cur.close()
        return 1

    return _execute(work)


# ==========================
# DELETE
# ==========================

def delete_port(server_id: int, port: int) -> int:
    def work(conn):
        cur = conn.cursor()
        cur.execute("""
            DELETE FROM ports
            WHERE server_id = %s
              AND port = %s
        """, (server_id, port))
        affected = cur.rowcount
        conn.commit()
        cur.close()
        return affected

    return _execute(work)

def delete_credentials(server_id: int, port: int) -> int:
    def work(conn):
        cur = conn.cursor()
        cur.execute("""
            DELETE FROM credentials
            WHERE server_id = %s AND port = %s
        """, (server_id, port))

        affected = cur.rowcount
        conn.commit()
        cur.close()
        return affected

    return _execute(work)