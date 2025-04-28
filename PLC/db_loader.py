import psycopg2
import pandas as pd
import sqlite3
import time

# --- Configuration ---
SQLITE_PATH = '/home/admin/Documents/ERA/data/modbus_data.sqlite'
DEVICE_ID = 'aa4659f5-47cf-41a2-9a9e-73897609704c'
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
POSTGRES_URL = "postgres://postgres:password@vaphaet.ddns.net:5432"

# --- Functions ---
def connect_to_timescale(timeout=10):
    """
    Establish a connection to the TimescaleDB with a timeout.
    """
    start = time.time()
    while True:
        try:
            conn = psycopg2.connect(POSTGRES_URL)
            print("Connected to TimescaleDB successfully.")
            return conn
        except Exception as e:
            if time.time() - start > timeout:
                print(f"Error connecting to TimescaleDB after {timeout} seconds: {e}")
                return None
            time.sleep(1)


def read_local_data(sqlite_path: str) -> pd.DataFrame:
    """
    Reads ts, channel_id, and value from local SQLite 'readings' table.
    """
    try:
        conn = sqlite3.connect(sqlite_path)
        df = pd.read_sql_query(
            "SELECT ts, channel_id, value FROM readings;", conn
        )
        conn.close()
        print(f"Read {len(df)} rows from local database.")
        return df
    except Exception as e:
        print(f"Failed to load data from local database: {e}")
        return pd.DataFrame(columns=['ts', 'channel_id', 'value'])


def fetch_channel_mappings(conn) -> dict:
    """
    Fetch mapping from channel name (channel_id) to TimescaleDB channel ID (id).
    """
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT id, name
                FROM channels
                WHERE "device_id" = %s
                AND name = ANY(%s)
            """
            cur.execute(sql, (DEVICE_ID, TARGET_CHANNELS))
            results = cur.fetchall()
            mapping = {name: id_ for id_, name in results}
            print(f"Fetched {len(mapping)} channel mappings.")
            return mapping
    except Exception as e:
        print(f"Error fetching channel mappings: {e}")
        return {}


def prepare_delta_records(df: pd.DataFrame, channel_mapping: dict) -> list:
    """
    Prepares delta (value difference) records for uploading.
    """
    if df.empty or not channel_mapping:
        return []

    # Filter only needed channels and create a copy to avoid SettingWithCopyWarning
    df_filtered = df[df['channel_id'].isin(channel_mapping.keys())].copy()
    if df_filtered.empty:
        print("No matching tags found in local data.")
        return []

    # Convert timestamp column on the copy
    df_filtered.loc[:, 'ts'] = pd.to_datetime(df_filtered['ts'])
    df_sorted = df_filtered.sort_values(['channel_id', 'ts'])

    delta_records = []

    for channel_id, group in df_sorted.groupby('channel_id'):
        group = group.sort_values('ts').copy()  # explicit copy
        group.loc[:, 'delta'] = group['value'].diff()
        group = group.dropna(subset=['delta'])

        for _, row in group.iterrows():
            delta_records.append(
                (
                    row['ts'].to_pydatetime(),
                    channel_mapping[channel_id],
                    float(row['delta'])
                )
            )

    print(f"Prepared {len(delta_records)} delta records.")
    return delta_records


def upload_records(conn, records: list):
    """
    Uploads prepared delta records to the TimescaleDB measurements table.
    """
    if not records:
        print("No records to upload.")
        return

    insert_sql = (
        'INSERT INTO measurements (time, channel_id, value) VALUES (%s, %s, %s)'
    )

    try:
        with conn.cursor() as cur:
            cur.executemany(insert_sql, records)
        conn.commit()
        print(f"Uploaded {len(records)} records to TimescaleDB.")
    except Exception as e:
        print(f"Error uploading records: {e}")


# --- Main ---
if __name__ == '__main__':
    df_local = read_local_data(SQLITE_PATH)

    conn_ts = connect_to_timescale()
    if conn_ts:
        channel_mapping = fetch_channel_mappings(conn_ts)
        missing = set(TARGET_CHANNELS) - set(channel_mapping.keys())
        for m in missing:
            print(f"Warning: {m} not found in channel mappings, skipping.")

        delta_records = prepare_delta_records(df_local, channel_mapping)
        upload_records(conn_ts, delta_records)
        conn_ts.close()
