from app.services.db.pool import _execute


# ==========================
# READ
# ==========================

def load_ports(server_id: int):
    def work(conn):
        cur = conn.cursor()
        cur.execute("""
            SELECT port, protocol, last_success, last_failure
            FROM ports
            WHERE server_id = %s
            ORDER BY port
        """, (server_id,))
        rows = cur.fetchall()
        cur.close()

        return [
            {
                "port": r[0],
                "protocol": r[1],
                "last_success": r[2],
                "last_failure": r[3],
            }
            for r in rows
        ]

    return _execute(work)


# ==========================
# CREATE
# ==========================

def create_port(server_id: int, port: int, protocol: str) -> int:
    def work(conn):
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO ports (server_id, port, protocol)
            VALUES (%s, %s, %s)
        """, (server_id, port, protocol))
        conn.commit()
        cur.close()
        return 1

    return _execute(work)


# ==========================
# UPDATE
# ==========================

def update_port(server_id: int, old_port: int, new_port: int) -> int:
    def work(conn):
        cur = conn.cursor()

        cur.execute("""
            UPDATE ports
            SET port = %s
            WHERE server_id = %s
              AND port = %s
        """, (new_port, server_id, old_port))

        affected = cur.rowcount

        # если есть credentials — обновляем и там
        cur.execute("""
            UPDATE credentials
            SET port = %s
            WHERE server_id = %s
              AND port = %s
        """, (new_port, server_id, old_port))

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


def update_vault_path(server_id: int, port: int, new_path: str) -> int:
    def work(conn):
        cur = conn.cursor()
        cur.execute("""
            UPDATE credentials
            SET vault_path = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE server_id = %s
              AND port = %s
        """, (new_path, server_id, port))

        affected = cur.rowcount
        conn.commit()
        cur.close()
        return affected

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