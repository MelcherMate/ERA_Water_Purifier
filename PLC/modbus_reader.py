import pandas as pd
from pymodbus.client import ModbusTcpClient
import struct
import os
from sqlalchemy import create_engine, Table, Column, String, Float, Boolean, DateTime, MetaData
from datetime import datetime

# Get the parent directory of the current script (PLC folder)
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)

# Define the Excel file's relative path (inside the RegisterList folder)
file_path = os.path.join(parent_dir, 'RegisterList', 'PanelKOVK_KommRef.xlsx')

# Load the Excel file
df = pd.read_excel(file_path, engine='openpyxl')

# Connect to the Modbus server
client = ModbusTcpClient('10.20.16.100', port=502)
client.connect()

# The total number of registers you want to read (252 registers)
total_registers = 252
registers_data = []
address = 0
count = 100  # Number of registers to read per request

while len(registers_data) < total_registers:
    response = client.read_holding_registers(address=address, count=count)
    if response.isError():
        print("Error reading registers")
        break
    else:
        registers_data.extend(response.registers)
    address += count

# Print values and prepare list for DB insertion
insert_data = []

for i, row in df.iterrows():
    if i >= len(registers_data):
        break

    channel_id = row['channel_id']
    type_ = row['Type']
    description = row['Description']
    dimension = row['Dimension'] if 'Dimension' in row else 'N/A'
    modbus_register_value = registers_data[i]
    value = None

    try:
        if type_ == 'BOOL':
            value = float(bool(modbus_register_value))
            print(f"Register {i+1} ({channel_id}): {value} - Description: {description} - Dimension: {dimension}")
        elif type_ == 'INT':
            value = float(modbus_register_value)
            print(f"Register {i+1} ({channel_id}): {value} - Description: {description} - Dimension: {dimension}")
        elif type_ == 'BIT':
            value = float(modbus_register_value & 1)
            print(f"Register {i+1} ({channel_id}): {value} - Description: {description} - Dimension: {dimension}")
        elif type_ == 'UDINT' and len(registers_data) > i + 3:
            reg1 = registers_data[i]
            reg2 = registers_data[i + 1]
            reg3 = registers_data[i + 2]
            reg4 = registers_data[i + 3]
            value = float((reg4 << 24) | (reg3 << 16) | (reg2 << 8) | reg1)
            print(f"Register {i+1} ({channel_id}): {value} - Description: {description} - Dimension: {dimension}")
        elif type_ == 'LREAL' and len(registers_data) > i + 7:
            reg1 = registers_data[i]
            reg2 = registers_data[i + 1]
            reg3 = registers_data[i + 2]
            reg4 = registers_data[i + 3]
            reg5 = registers_data[i + 4]
            reg6 = registers_data[i + 5]
            reg7 = registers_data[i + 6]
            reg8 = registers_data[i + 7]
            combined = (reg8 << 48) | (reg7 << 32) | (reg6 << 16) | reg5
            combined |= (reg4 << 56) | (reg3 << 40) | (reg2 << 24) | (reg1 << 8)
            value = float(struct.unpack('>d', struct.pack('>Q', combined))[0])
            print(f"Register {i+1} ({channel_id}): {value} - Description: {description} - Dimension: {dimension}")
        elif len(registers_data) > i + 1:
            reg1 = registers_data[i]
            reg2 = registers_data[i + 1]
            combined = (reg2 << 16) | reg1
            value = float(struct.unpack('>f', struct.pack('>I', combined))[0])
            print(f"Register {i+1} ({channel_id}): {value} - Description: {description} - Dimension: {dimension}")
    except Exception as e:
        print(f"Error processing register {i+1} ({channel_id}): {e}")
        continue

    if value is not None:
        insert_data.append({
            "channel_id": channel_id,
            "value": value,
            "time": datetime.utcnow(),
            "accounted": False,
        })
        # Create SQLAlchemy engine for TimescaleDB
# Adjust host and credentials as needed (this example assumes local port forwarding or VPN)
db_url = "postgresql+psycopg2://postgres:password@vaphaet.ddns.net/postgres"
engine = create_engine(db_url)

# Define metadata and table structure
metadata = MetaData()

measurements = Table('measurements', metadata,
    Column('channel_id', String, nullable=False),
    Column('value', Float, nullable=False),
    Column('time', DateTime(timezone=True), nullable=False),
    Column('accounted', Boolean, nullable=False)
)

# Insert data into the database
with engine.connect() as connection:
    with connection.begin():
        for entry in insert_data:
            try:
                connection.execute(measurements.insert().values(
                    channel_id=entry["channel_id"],
                    value=entry["value"],
                    time=entry["time"],
                    accounted=entry["accounted"]
                ))
            except Exception as e:
                print(f"Failed to insert entry for channel {entry['channel_id']}: {e}")

# Disconnect from the Modbus server
client.close()
print("Modbus client disconnected and data uploaded to TimescaleDB.")