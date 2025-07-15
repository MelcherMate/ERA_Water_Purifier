import psycopg2
import pandas as pd
import sqlite3
import time
from tqdm import tqdm
from datetime import datetime, timedelta

# --- Configuration --- #
SQLITE_PATH = '/home/admin/Documents/ERA/data/modbus_data_from_01_07_2025.sqlite'
SHORT_NAME = 'OT001'

# - Panelko - #
#POSTGRES_URL = "postgres://panelkoadmin:hFAaTvgD9bT5@rex.panelko.hu:5432/rex_db"

# - DEV - #
POSTGRES_URL = "postgres://postgres:password@vaphaet.ddns.net:5432/postgres"

TARGET_CHANNELS = [
    'PLC_VK.Application.GVL_HMI.rdata.daq_raw.SZ42_10M_RUNT',
    'PLC_VK.Application.GVL_HMI.rdata.daq_raw.SZ43_11M_RUNT',
    'PLC_VK.Application.GVL_HMI.rdata.daq_raw.SZ44_12M_RUNT',
    'PLC_VK.Application.GVL_HMI.rdata.daq_raw.H_13M_RUNT',
    'PLC_VK.Application.GVL_HMI.rdata.daq_raw.M80_20M_RUNT',
    'PLC_VK.Application.GVL_HMI.rdata.daq_raw.D23_21M_RUNT',
    'PLC_VK.Application.GVL_HMI.rdata.daq_raw.A71_90M1_VOL',
    'PLC_VK.Application.GVL_HMI.rdata.daq_raw.A70_90M2_VOL',
]

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
                WHERE device_id = %s AND name = ANY(%s)
            """, (device_id, TARGET_CHANNELS))
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
        conn = sqlite3.connect(sqlite_path, timeout=30)

        df = pd.read_sql_query("SELECT ts, channel_id, value FROM readings", conn)
        conn.close()
        df['ts'] = pd.to_datetime(df['ts']).dt.tz_localize(None)

        # Sz?r�s az elm�lt 3 napra
        three_days_ago = datetime.now() - timedelta(days=3)
        df = df[df['ts'] >= three_days_ago]

        # Csak a TARGET_CHANNELS csatorn�kra sz?r�s
        df = df[df['channel_id'].isin(TARGET_CHANNELS)]

        print(f"Read {len(df)} rows from local database (filtered to last 3 days and target channels).")
        return df
    except Exception as e:
        print(f"Failed to read local SQLite data: {e}")
        return pd.DataFrame(columns=['ts', 'channel_id', 'value'])

def filter_new_data(df: pd.DataFrame, latest_ts: dict) -> pd.DataFrame:
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
        conn = sqlite3.connect(sqlite_path, timeout=30)

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

# --- Main Loop ---
if __name__ == '__main__':
    conn_ts = connect_to_timescale()
    if not conn_ts:
        print("Unable to connect to TimescaleDB. Exiting.")
        exit(1)

    device_id = get_device_id_from_shortname(conn_ts, SHORT_NAME)
    if not device_id:
        print("Device ID not found. Exiting.")
        exit(1)

    channel_mapping = fetch_channel_mappings(conn_ts, device_id)
    if not channel_mapping:
        print("No channel mappings found. Exiting.")
        exit(1)

    print("Starting continuous upload loop. Press Ctrl+C to stop.")
    try:
        while True:
            df_local = read_local_data(SQLITE_PATH)
            latest_ts = get_latest_timestamps(conn_ts, channel_mapping)
            df_new = filter_new_data(df_local, latest_ts)
            upload_data = prepare_upload_records(df_new, channel_mapping)
            upload_records(conn_ts, upload_data)
            delete_uploaded_data(SQLITE_PATH, upload_data, channel_mapping)

            print("Sleeping for 60 seconds...\n")
            time.sleep(60)

    except KeyboardInterrupt:
        print("Stopped by user.")
    finally:
        conn_ts.close()
