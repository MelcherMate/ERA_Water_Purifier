import psycopg2
import pandas as pd
import sqlite3
import time
from tqdm import tqdm

# --- Configuration ---
SQLITE_PATH = '/home/admin/Documents/ERA/data/modbus_data.sqlite'
SHORT_NAME = 'OT001'
POSTGRES_URL = "postgres://panelkoadmin:hFAaTvgD9bT5@rex.panelko.hu:5432/rex_db"

# --- Database Helpers ---
def connect_to_timescale():
    while True:
        try:
            conn = psycopg2.connect(POSTGRES_URL)
            print("Connected to TimescaleDB successfully.")
            return conn
        except Exception as e:
            print(f"Error connecting to TimescaleDB. Retrying in 5 seconds: {e}")
            time.sleep(5)

def get_device_id_from_shortname(conn, short_name: str) -> str:
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM hardware WHERE short_name = %s", (short_name,))
            result = cur.fetchone()
            return result[0] if result else None
    except Exception as e:
        print(f"Error fetching device_id: {e}")
        return None

def fetch_channel_mappings(conn, device_id: str) -> dict:
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name
                FROM channels
                WHERE device_id = %s
            """, (device_id,))
            return {name: id_ for id_, name in cur.fetchall()}
    except Exception as e:
        print(f"Error fetching channel mappings: {e}")
        return {}

def get_latest_timestamps(conn, channel_mapping: dict) -> dict:
    latest = {}
    try:
        with conn.cursor() as cur:
            for name, ch_id in tqdm(channel_mapping.items(), desc="Fetching latest timestamps"):
                cur.execute("SELECT MAX(time) FROM measurements WHERE channel_id = %s", (ch_id,))
                result = cur.fetchone()
                latest[name] = pd.Timestamp(result[0], tz=None) if result and result[0] else pd.Timestamp.min
        return latest
    except Exception as e:
        print(f"Error fetching latest timestamps: {e}")
        return {name: pd.Timestamp.min for name in channel_mapping.keys()}

# --- Local Data Handling ---
def read_local_data(sqlite_path: str) -> pd.DataFrame:
    try:
        conn = sqlite3.connect(sqlite_path)
        df = pd.read_sql_query("SELECT ts, channel_id, value FROM readings", conn)
        conn.close()
        print(f"Read {len(df)} rows from local database.")
        return df
    except Exception as e:
        print(f"Failed to read local SQLite data: {e}")
        return pd.DataFrame(columns=['ts', 'channel_id', 'value'])

def filter_new_data(df: pd.DataFrame, latest_ts: dict) -> pd.DataFrame:
    df['ts'] = pd.to_datetime(df['ts']).dt.tz_localize(None)
    filtered = []
    for channel, group in tqdm(df.groupby('channel_id'), desc="Filtering new data"):
        limit = latest_ts.get(channel, pd.Timestamp.min)
        if limit.tzinfo:
            limit = limit.tz_localize(None)
        filtered_group = group[group['ts'] > limit]
        filtered.append(filtered_group)
    return pd.concat(filtered) if filtered else pd.DataFrame(columns=['ts', 'channel_id', 'value'])

# --- Upload ---
def prepare_upload_records(df: pd.DataFrame, channel_mapping: dict) -> list:
    if df.empty:
        return []
    df = df[df['channel_id'].isin(channel_mapping.keys())].copy()
    df['ts'] = pd.to_datetime(df['ts'])
    df_sorted = df.sort_values(['channel_id', 'ts'])

    upload_records = []
    for _, row in df_sorted.iterrows():
        upload_records.append((
            row['ts'].to_pydatetime(),
            channel_mapping[row['channel_id']],
            float(row['value'])
        ))
    print(f"Prepared {len(upload_records)} records for upload.")
    return upload_records

def upload_records(conn, records: list):
    if not records:
        print("No records to upload.")
        return
    insert_sql = """
        INSERT INTO measurements (time, channel_id, value)
        VALUES (%s, %s, %s)
        ON CONFLICT DO NOTHING
    """
    try:
        with conn.cursor() as cur:
            for record in tqdm(records, desc="Uploading to Timescale"):
                cur.execute(insert_sql, record)
        conn.commit()
        print(f"Uploaded {len(records)} records to TimescaleDB.")
    except Exception as e:
        print(f"Failed to upload records: {e}")

# --- Cleanup local database ---
def delete_uploaded_data(sqlite_path: str, records: list, channel_id_to_name: dict):
    if not records:
        return
    try:
        conn = sqlite3.connect(sqlite_path)
        cur = conn.cursor()
        for ts, ch_id, _ in tqdm(records, desc="Deleting uploaded records"):
            channel_name = [k for k, v in channel_id_to_name.items() if v == ch_id]
            if channel_name:
                cur.execute(
                    "DELETE FROM readings WHERE ts = ? AND channel_id = ?",
                    (ts.strftime('%Y-%m-%d %H:%M:%S'), channel_name[0])
                )
        conn.commit()
        conn.close()
        print("Deleted uploaded records from SQLite.")
    except Exception as e:
        print(f"Failed to delete from local database: {e}")

# --- Main ---
if __name__ == '__main__':
    df_local = read_local_data(SQLITE_PATH)

    conn_ts = connect_to_timescale()
    if conn_ts:
        device_id = get_device_id_from_shortname(conn_ts, SHORT_NAME)
        if not device_id:
            print("Device ID not found, exiting.")
            exit(1)

        channel_mapping = fetch_channel_mappings(conn_ts, device_id)
        if not channel_mapping:
            print("No channel mappings found, exiting.")
            exit(1)

        latest_ts = get_latest_timestamps(conn_ts, channel_mapping)
        df_new = filter_new_data(df_local, latest_ts)
        upload_data = prepare_upload_records(df_new, channel_mapping)

        upload_records(conn_ts, upload_data)
        delete_uploaded_data(SQLITE_PATH, upload_data, channel_mapping)

        conn_ts.close()
