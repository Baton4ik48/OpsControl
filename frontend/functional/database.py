import psycopg2

def get_connection():
    return psycopg2.connect(
        dbname="ppm_database",
        user="postgres",
        password="postgres",
        host="127.0.0.1",
        port=5432
    )


# ================================
#   ЗАГРУЗКА ИЗ БАЗЫ
# ================================

def load_branches():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM branches ORDER BY name")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows



def load_servers(branch_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, ip
        FROM servers
        WHERE branch_id = %s
        ORDER BY name
    """, (branch_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows



def load_ports(server_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT port, last_success, last_failure, status
        FROM ports
        WHERE server_id = %s
        ORDER BY port
    """, (server_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {
            "port": row[0],
            "last_success": row[1],
            "last_failure": row[2],
            "status": row[3]
        }
        for row in rows
    ]


# ================================
#   ОБНОВЛЕНИЕ ИЗ БАЗЫ
# ================================

def update_server_name(server_id, new_name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE servers SET name = %s WHERE id = %s",
        (new_name, server_id)
    )
    conn.commit()
    cur.close()
    conn.close()



def update_server_ip(server_id, new_ip):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE servers SET ip = %s WHERE id = %s",
        (new_ip, server_id)
    )
    conn.commit()
    cur.close()
    conn.close()



def update_port_status(server_id, port, ok):
    conn = get_connection()
    cur = conn.cursor()

    if ok:
        cur.execute("""
            UPDATE ports
            SET status = 'up',
                last_success = CURRENT_TIMESTAMP
            WHERE server_id = %s AND port = %s
        """, (server_id, port))
    else:
        cur.execute("""
            UPDATE ports
            SET status = 'down',
                last_failure = CURRENT_TIMESTAMP
            WHERE server_id = %s AND port = %s
        """, (server_id, port))

    conn.commit()
    cur.close()
    conn.close()

