import psycopg2
import sys

print("Тест подключения к БД")
      
try:
    conn = psycopg2.connect(
        host="postgres",
        dbname="ppm_database",
        user="login_ppm",
        password="7946130q!"
    )
    print("CONNECTED OK")
    conn.close()
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)