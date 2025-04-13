import pandas as pd
from pymodbus.client import ModbusTcpClient
import struct
import os
import time

# Get the parent directory of the current script (PLC folder)
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)

# Define the Excel file's relative path
file_path = os.path.join(parent_dir, 'RegisterList', 'PanelKOVK_KommRef.xlsx')

# Load the Excel file
df = pd.read_excel(file_path, engine='openpyxl')
df['Scale'] = pd.to_numeric(df['Scale'], errors='coerce')

# Connect to the Modbus server
client = ModbusTcpClient('10.20.16.100', port=502)
client.connect()

# Calculate how many registers we need to read based on the Excel file
max_address = df['Address'].max()
registers_needed = max_address + 10

try:
    while True:
        # Read Modbus registers in chunks of 100 registers at a time
        registers_data = []
        address = 0
        count = 100

        while address < registers_needed:
            read_count = min(count, registers_needed - address)
            response = client.read_holding_registers(address=address, count=read_count)
            if response.isError():
                print(f"Error reading registers at address {address}")
                break
            else:
                registers_data.extend(response.registers)
            address += count

        print(f"\n--- New Read at {time.strftime('%Y-%m-%d %H:%M:%S')} ---")
        # Iterate through the rows of the Excel sheet
        for _, row in df.iterrows():
            reg_address = int(row['Address'])
            channel_id = row['channel_id']
            type_ = row['Type']
            description = row['Description']
            dimension = row['Dimension'] if 'Dimension' in row else 'N/A'
            scale = float(row['Scale']) if not pd.isna(row['Scale']) else 1.0

            if reg_address >= len(registers_data):
                print(f"{channel_id} - N/A - {description} (out of range)")
                continue

            reg_val = registers_data[reg_address]

            if type_ == 'BOOL':
                value = bool(reg_val)
            elif type_ == 'INT':
                value = reg_val
            elif type_ == 'BIT':
                value = reg_val & 1
            elif type_ == 'UDINT':
                if reg_address + 1 < len(registers_data):
                    reg1, reg2 = registers_data[reg_address], registers_data[reg_address + 1]
                    packed = struct.pack('<HH', reg1, reg2)
                    value = struct.unpack('<I', packed)[0] * scale
                else:
                    value = 'N/A'
            elif type_ == 'LREAL':
                if reg_address + 3 < len(registers_data):
                    reg_block = registers_data[reg_address:reg_address + 4]
                    packed = struct.pack('<HHHH', *reg_block)
                    value = struct.unpack('<d', packed)[0] * scale
                else:
                    value = 'N/A'
            else:
                if reg_address + 1 < len(registers_data):
                    reg1, reg2 = registers_data[reg_address], registers_data[reg_address + 1]
                    combined = (reg2 << 16) | reg1
                    value = struct.unpack('>f', struct.pack('>I', combined))[0] * scale
                else:
                    value = 'N/A'

            print(f"{channel_id} - {value} - {description}")

        time.sleep(5)

except KeyboardInterrupt:
    print("\nStop modbus reading...")
finally:
    client.close()
