from app.services.db.pool import _execute

# ==========================
# READ
# ==========================

def load_branches():
    def work(conn):
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM branches ORDER BY name")
        rows = cur.fetchall()
        cur.close()
        return rows

    return _execute(work)

# ==========================
# CREATE
# ==========================

def create_branch(name: str) -> int:
    def work(conn):
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO branches (name) VALUES (%s) RETURNING id",
            (name,)
        )
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        return new_id

    return _execute(work)

# ==========================
# UPDATE
# ==========================

def update_branch(branch_id: int, new_name: str) -> int:
    def work(conn):
        cur = conn.cursor()
        cur.execute("""
            UPDATE branches
            SET name = %s
            WHERE id = %s
        """, (new_name, branch_id))

        affected = cur.rowcount
        conn.commit()
        cur.close()
        return affected

    return _execute(work)

# ==========================
# DELETE
# ==========================

def delete_branch(branch_id: int) -> int:
    def work(conn):
        cur = conn.cursor()
        cur.execute("DELETE FROM branches WHERE id = %s", (branch_id,))
        affected = cur.rowcount
        conn.commit()
        cur.close()
        return affected

    return _execute(work)