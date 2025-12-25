import pandas as pd
import sqlite3
import os
from PyQt6.QtWidgets import QFileDialog, QApplication, QMessageBox

DB_FILE = os.path.join("bin", "database.db")


def import_excel_to_db(excel_path, db_path, sheet_name="Servers"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        df = pd.read_excel(excel_path, sheet_name=sheet_name)
    except Exception as e:
        raise RuntimeError(f"Ошибка чтения Excel: {e}")

    # --- Проверка колонок ---
    required_columns = {"BranchName", "ServerName", "ServerIP", "PortNumber"}
    if not required_columns.issubset(df.columns):
        raise ValueError(
            f"Excel должен содержать колонки: {', '.join(required_columns)}"
        )

    for row_index, row in df.iterrows():
        branch_name = str(row["BranchName"]).strip()
        server_name = str(row["ServerName"]).strip()
        server_ip = str(row["ServerIP"]).strip()
        port_number = row["PortNumber"]
        protocol = (
            str(row["Protocol"]).strip().lower()
            if "Protocol" in row and pd.notna(row["Protocol"])
            else "tcp"
        )

        # --- Проверка данных ---
        if not branch_name or not server_ip or pd.isna(port_number):
            print(f"Пропуск строки {row_index + 2}: некорректные данные")
            continue

        # --- Branch ---
        cursor.execute(
            "INSERT OR IGNORE INTO branches(name) VALUES (?)",
            (branch_name,)
        )
        cursor.execute(
            "SELECT id FROM branches WHERE name = ?",
            (branch_name,)
        )
        branch_id = cursor.fetchone()[0]

        # --- Server ---
        cursor.execute(
            """
            INSERT OR IGNORE INTO servers(branch_id, name, ip)
            VALUES (?, ?, ?)
            """,
            (branch_id, server_name, server_ip)
        )
        cursor.execute(
            "SELECT id FROM servers WHERE ip = ?",
            (server_ip,)
        )
        server_id = cursor.fetchone()[0]

        # --- Port ---
        cursor.execute(
            """
            INSERT OR IGNORE INTO ports(server_id, port, protocol)
            VALUES (?, ?, ?)
            """,
            (server_id, int(port_number), protocol)
        )

    conn.commit()
    conn.close()
