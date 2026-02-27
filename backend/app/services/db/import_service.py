import pandas as pd
from fastapi import HTTPException
from app.services.db.pool import _execute


REQUIRED_COLUMNS = {"branch", "server_name", "ip", "port"}


# =========================================================
# PREVIEW
# =========================================================

def preview_import(file) -> dict:

    df = pd.read_excel(file)

    if not REQUIRED_COLUMNS.issubset(df.columns):
        raise HTTPException(
            status_code=400,
            detail=f"XLSX must contain columns: {REQUIRED_COLUMNS}"
        )

    conflicts = []
    new_branches = set()
    new_servers = set()
    new_ports = []

    def work(conn):
        cur = conn.cursor()

        for index, row in df.iterrows():

            branch = str(row["branch"]).strip()
            server_name = str(row["server_name"]).strip()
            ip = str(row["ip"]).strip()
            port = int(row["port"])

            # ---- Check branch
            cur.execute(
                "SELECT id FROM branches WHERE name = %s",
                (branch,)
            )
            branch_row = cur.fetchone()

            if not branch_row:
                new_branches.add(branch)

            # ---- Check server by IP
            cur.execute(
                "SELECT id FROM servers WHERE ip = %s",
                (ip,)
            )
            server_row = cur.fetchone()

            if server_row:
                conflicts.append({
                    "row": int(index) + 2,
                    "reason": f"IP {ip} already exists"
                })
                continue

            new_servers.add(ip)

            new_ports.append((ip, port))

        cur.close()

    _execute(work)

    return {
        "new_branches": len(new_branches),
        "new_servers": len(new_servers),
        "new_ports": len(new_ports),
        "conflicts": conflicts
    }


# =========================================================
# APPLY (АТОМАРНО)
# =========================================================

def apply_import(file) -> dict:

    df = pd.read_excel(file)

    if not REQUIRED_COLUMNS.issubset(df.columns):
        raise HTTPException(
            status_code=400,
            detail=f"XLSX must contain columns: {REQUIRED_COLUMNS}"
        )

    def work(conn):
        cur = conn.cursor()

        created_branches = 0
        created_servers = 0
        created_ports = 0

        for _, row in df.iterrows():

            branch = str(row["branch"]).strip()
            server_name = str(row["server_name"]).strip()
            ip = str(row["ip"]).strip()
            port = int(row["port"])

            # ---- Branch
            cur.execute(
                "SELECT id FROM branches WHERE name = %s",
                (branch,)
            )
            branch_row = cur.fetchone()

            if branch_row:
                branch_id = branch_row[0]
            else:
                cur.execute(
                    "INSERT INTO branches (name) VALUES (%s) RETURNING id",
                    (branch,)
                )
                branch_id = cur.fetchone()[0]
                created_branches += 1

            # ---- Server (IP must be unique)
            cur.execute(
                "SELECT id FROM servers WHERE ip = %s",
                (ip,)
            )
            server_row = cur.fetchone()

            if server_row:
                continue  # не перезаписываем

            cur.execute(
                """
                INSERT INTO servers (branch_id, name, ip)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (branch_id, server_name, ip)
            )
            server_id = cur.fetchone()[0]
            created_servers += 1

            # ---- Port
            cur.execute(
                """
                INSERT INTO ports (server_id, port)
                VALUES (%s, %s)
                ON CONFLICT (server_id, port) DO NOTHING
                """,
                (server_id, port)
            )

            created_ports += 1

        conn.commit()
        cur.close()

        return {
            "created_branches": created_branches,
            "created_servers": created_servers,
            "created_ports": created_ports
        }

    return _execute(work)