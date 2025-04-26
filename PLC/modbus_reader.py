import os
import time
import struct
import pandas as pd
import sqlite3
from pymodbus.client import ModbusTcpClient

# --- Configuration ---
MODBUS_HOST = '10.20.16.100'
MODBUS_PORT = 502
READ_INTERVAL = 5  # Reading the data in every 5 sec

# Paths
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
excel_path = os.path.join(parent_dir, 'RegisterList', 'PanelKOVK_KommRef.xlsx')
sqlite_path = os.path.join(parent_dir, 'data', 'modbus_data.sqlite')

# --- Setup local SQLite ---
os.makedirs(os.path.dirname(sqlite_path), exist_ok=True)
sqlite_conn = sqlite3.connect(sqlite_path)
sqlite_cursor = sqlite_conn.cursor()
sqlite_cursor.execute(
    '''
    CREATE TABLE IF NOT EXISTS readings (
        ts TEXT,
        channel_id TEXT,
        value REAL,
        description TEXT,
        dimension TEXT
    )
    '''
)
sqlite_conn.commit()

# --- Load Excel definitions ---
df = pd.read_excel(excel_path, engine='openpyxl')
df['Scale'] = pd.to_numeric(df['Scale'], errors='coerce')

# --- Connect Modbus ---
client = ModbusTcpClient(MODBUS_HOST, port=MODBUS_PORT)
client.connect()

# --- Main loop ---
try:
    while True:
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        # Read Modbus registers
        registers_data = []
        max_address = int(df['Address'].max()) + 10
        address = 0
        chunk = 100
        while address < max_address:
            count = min(chunk, max_address - address)
            resp = client.read_holding_registers(address=address, count=count)
            if resp.isError():
                print(f"Error reading registers at {address}")
                break
            registers_data.extend(resp.registers)
            address += chunk

        # Save to local SQLite
        for _, row in df.iterrows():
            addr = int(row['Address'])
            cid = row['channel_id']
            typ = row['Type']
            desc = row['Description']
            dim = row.get('Dimension', 'N/A')
            scale = float(row['Scale']) if not pd.isna(row['Scale']) else 1.0

            # Value decoding
            if typ == 'BOOL':
                val = bool(registers_data[addr])
            elif typ == 'INT':
                val = registers_data[addr]
            elif typ == 'BIT':
                val = registers_data[addr] & 1
            elif typ == 'UDINT' and addr+1 < len(registers_data):
                r1, r2 = registers_data[addr], registers_data[addr+1]
                val = struct.unpack('<I', struct.pack('<HH', r1, r2))[0] * scale
            elif typ == 'LREAL' and addr+3 < len(registers_data):
                block = registers_data[addr:addr+4]
                val = struct.unpack('<d', struct.pack('<HHHH', *block))[0] * scale
            elif addr+1 < len(registers_data):
                r1, r2 = registers_data[addr], registers_data[addr+1]
                combined = (r2 << 16) | r1
                val = struct.unpack('>f', struct.pack('>I', combined))[0] * scale
            else:
                continue

            sqlite_cursor.execute(
                'INSERT INTO readings (ts, channel_id, value, description, dimension) VALUES (?, ?, ?, ?, ?)',
                (timestamp, cid, val, desc, dim)
            )
        sqlite_conn.commit()

        print(f"Local save complete at {timestamp}")
        time.sleep(READ_INTERVAL)
except KeyboardInterrupt:
    print("Stopped by user.")
finally:
    client.close()
    sqlite_conn.close()
