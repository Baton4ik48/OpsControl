from app.services.db.pool_db import _execute


def load_servers(branch_id: int):
    def work(conn):
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, name, ip, device_type
            FROM servers
            WHERE branch_id = %s
            ORDER BY name
        """,
            (branch_id,),
        )
        rows = cur.fetchall()
        cur.close()
        return rows

    return _execute(work)


def create_server(
    branch_id: int, name: str, ip: str, device_type: str = "linux"
) -> int:
    def work(conn):
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO servers (branch_id, name, ip, device_type)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """,
            (branch_id, name, ip, device_type),
        )
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        return new_id

    return _execute(work)


def update_server(
    server_id: int, name: str, ip: str, device_type: str = "linux"
) -> int:
    def work(conn):
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE servers
            SET name = %s,
                ip = %s,
                device_type = %s
            WHERE id = %s
        """,
            (name, ip, device_type, server_id),
        )

        affected = cur.rowcount
        conn.commit()
        cur.close()
        return affected

    return _execute(work)


def update_server_comment(server_id: int, comment: str) -> int:
    def work(conn):
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE servers
            SET comment            = %s,
                comment_updated_at = (NOW() AT TIME ZONE 'UTC')
            WHERE id = %s
            """,
            (comment or None, server_id),
        )
        affected = cur.rowcount
        conn.commit()
        cur.close()
        return affected

    return _execute(work)


def delete_server(server_id: int) -> int:
    def work(conn):
        cur = conn.cursor()
        cur.execute("DELETE FROM servers WHERE id = %s", (server_id,))
        affected = cur.rowcount
        conn.commit()
        cur.close()
        return affected

    return _execute(work)
