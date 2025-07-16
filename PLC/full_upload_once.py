import psycopg2
import pandas as pd
import sqlite3
from tqdm import tqdm
from datetime import datetime
from psycopg2.extras import execute_values


# --- Configuration --- #
SQLITE_PATH = '/home/admin/Documents/ERA/data/modbus_data.sqlite'
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
    'PLC_VK.Application.GVL_HMI.rdata.daq.A71_90M1_VOL',
    'PLC_VK.Application.GVL_HMI.rdata.daq_raw.A70_90M2_VOL',
    'PLC_VK.Application.GVL_HMI.data.z50',
    'PLC_VK.Application.GVL_HMI.data.z51',
]

def connect_to_timescale():
    return psycopg2.connect(POSTGRES_URL)

def get_device_id(conn, short_name):
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM hardware WHERE short_name = %s", (short_name,))
        result = cur.fetchone()
        return result[0] if result else None

def fetch_channel_mappings(conn, device_id):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT c.id, tag
            FROM channels c,
            unnest(c.tags) AS tag
            WHERE c.device_id = %s AND tag = ANY(%s)
        """, (device_id, TARGET_CHANNELS))
        rows = cur.fetchall()
        return {tag: ch_id for ch_id, tag in rows}

def read_all_target_data(sqlite_path):
    conn = sqlite3.connect(sqlite_path, timeout=30)
    df = pd.read_sql_query("SELECT ts, channel_id, value FROM readings", conn)
    conn.close()
    df['ts'] = pd.to_datetime(df['ts']).dt.tz_localize(None)
    df = df[df['channel_id'].isin(TARGET_CHANNELS)]
    print(f"Read {len(df)} total rows for TARGET_CHANNELS.")
    return df

def prepare_records(df, channel_mapping):
    df = df[df['channel_id'].isin(channel_mapping.keys())].copy()
    df_sorted = df.sort_values(['channel_id', 'ts'])
    records = []
    for _, row in df_sorted.iterrows():
        records.append((
            row['ts'].to_pydatetime(),
            channel_mapping[row['channel_id']],
            float(row['value'])
        ))
    return records

def upload_records(conn, records, batch_size=1000):
    if not records:
        print("No records to upload.")
        return

    insert_sql = """
        INSERT INTO measurements (time, channel_id, value)
        VALUES %s
        ON CONFLICT DO NOTHING
    """

    try:
        with conn.cursor() as cur:
            for i in tqdm(range(0, len(records), batch_size), desc="Uploading"):
                batch = records[i:i+batch_size]
                execute_values(cur, insert_sql, batch)
        conn.commit()
        print(f"Uploaded {len(records)} records to TimescaleDB.")
    except Exception as e:
        print(f"Failed to upload records: {e}")

# --- Main --- #
if __name__ == '__main__':
    print("Starting full upload for TARGET_CHANNELS...")
    conn = connect_to_timescale()
    device_id = get_device_id(conn, SHORT_NAME)
    if not device_id:
        print("Device ID not found.")
        exit(1)

    mapping = fetch_channel_mappings(conn, device_id)
    if not mapping:
        print("No matching channel mappings found.")
        exit(1)

    df_all = read_all_target_data(SQLITE_PATH)
    records = prepare_records(df_all, mapping)
    upload_records(conn, records)

    conn.close()
    print("Done.")
