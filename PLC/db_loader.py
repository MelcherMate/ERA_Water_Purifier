import sys
import psycopg2
import pandas as pd
import sqlite3

# List of allowed tags (channel_id-k)
ALLOWED_TAGS = [
    "PLC_VK.Application.GVL_HMI.rdata.daq_raw.SZ42_10M_RUNT",
    "PLC_VK.Application.GVL_HMI.rdata.daq_raw.SZ43_11M_RUNT",
    "PLC_VK.Application.GVL_HMI.rdata.daq_raw.SZ44_12M_RUNT",
    "PLC_VK.Application.GVL_HMI.rdata.daq_raw.H_13M_RUNT",
    "PLC_VK.Application.GVL_HMI.rdata.daq_raw.M80_20M_RUNT",
    "PLC_VK.Application.GVL_HMI.rdata.daq_raw.D23_21M_RUNT",
    "PLC_VK.Application.GVL_HMI.rdata.daq_raw.A71_90M1_VOL",
    "PLC_VK.Application.GVL_HMI.rdata.daq_raw.A70_90M2_VOL",
]

def connect_to_timescale():
    """
    Establish a connection to the TimescaleDB.
    Timeout after 10 seconds if cannot connect.
    """
    try:
        conn = psycopg2.connect(
            "postgres://postgres:password@vaphaet.ddns.net:5432",
            connect_timeout=10
        )
        print("Connected to TimescaleDB successfully.")
        return conn
    except Exception as e:
        print(f"Error connecting to TimescaleDB: {e}")
        sys.exit(1)  # Exit if cannot connect

def read_local_data(sqlite_path: str) -> pd.DataFrame:
    """
    Reads ts, channel_id, and value from local SQLite 'readings' table.
    Filters only allowed channel_ids.
    """
    try:
        conn = sqlite3.connect(sqlite_path)
        df = pd.read_sql_query(
            "SELECT ts, channel_id, value FROM readings;", conn
        )
        conn.close()
        print(f"Read {len(df)} rows from local database.")
        
        # Filter only the allowed tags
        df = df[df['channel_id'].isin(ALLOWED_TAGS)]
        print(f"Filtered down to {len(df)} rows after tag filtering.")
        return df
    except Exception as e:
        print(f"Failed to load data from local database: {e}")
        return pd.DataFrame(columns=['ts', 'channel_id', 'value'])

def upload_to_timescale(df: pd.DataFrame):
    """
    Upload DataFrame to TimescaleDB 'measurements' table using 'tag' field.
    """
    if df.empty:
        print("No data to upload.")
        return

    conn_ts = connect_to_timescale()
    if conn_ts is None:
        return

    insert_sql = (
        'INSERT INTO measurements (time, tag, value) VALUES (%s, %s, %s)'
    )

    try:
        with conn_ts.cursor() as cur:
            records = [
                (row['ts'], row['channel_id'], float(row['value']))
                for _, row in df.iterrows()
            ]
            cur.executemany(insert_sql, records)
        conn_ts.commit()
        print(f"Uploaded {len(records)} records to TimescaleDB.")
    except Exception as e:
        print(f"Error inserting records: {e}")
    finally:
        conn_ts.close()

if __name__ == '__main__':
    SQLITE_PATH = '/home/admin/Documents/ERA/data/modbus_data.sqlite'
    df_local = read_local_data(SQLITE_PATH)
    upload_to_timescale(df_local)
