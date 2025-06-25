import psycopg2

# --- Konfigur�ci� ---
POSTGRES_URL = "postgres://panelkoadmin:hFAaTvgD9bT5@rex.panelko.hu:5432/rex_db"

def truncate_measurements():
    try:
        conn = psycopg2.connect(POSTGRES_URL)
        with conn.cursor() as cur:
            print("Kapcsol�dva TimescaleDB-hez.")
            cur.execute("TRUNCATE TABLE measurements;")
            conn.commit()
            print("A 'measurements' t�bla sikeresen �r�tve lett.")
        conn.close()
    except Exception as e:
        print(f"Hiba a t�rl�s sor�n: {e}")

if __name__ == "__main__":
    truncate_measurements()
