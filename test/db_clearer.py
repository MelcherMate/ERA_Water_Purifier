"""
TimescaleDB Measurements Truncate Script
----------------------------------------

This script connects to the TimescaleDB database and truncates the
'measurements' table, deleting all data. Use with caution!

"""

import psycopg2

# --- Configuration ---
POSTGRES_URL = "postgres://panelkoadmin:hFAaTvgD9bT5@rex.panelko.hu:5432/rex_db"

def truncate_measurements():
    try:
        conn = psycopg2.connect(POSTGRES_URL)
        with conn.cursor() as cur:
            print("Connected to TimescaleDB.")
            cur.execute("TRUNCATE TABLE measurements;")
            conn.commit()
            print("The 'measurements' table has been successfully truncated.")
        conn.close()
    except Exception as e:
        print(f"Error during truncation: {e}")

if __name__ == "__main__":
    truncate_measurements()
