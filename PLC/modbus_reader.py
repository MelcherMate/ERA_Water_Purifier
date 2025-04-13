import pandas as pd
from pymodbus.client import ModbusTcpClient
import struct
import os

# Get the parent directory of the current script (PLC folder)
script_dir = os.path.dirname(os.path.abspath(__file__))

# Go one level up to reach the parent directory
parent_dir = os.path.dirname(script_dir)

# Define the Excel file's relative path (it's inside the RegisterList folder)
file_path = os.path.join(parent_dir, 'RegisterList', 'PanelKOVK_KommRef.xlsx')

# Load the Excel file
# Make sure to convert non-numeric scale values to NaN, so they default to 1.0 later
df = pd.read_excel(file_path, engine='openpyxl')
df['Scale'] = pd.to_numeric(df['Scale'], errors='coerce')

# Connect to the Modbus server
client = ModbusTcpClient('10.20.16.100', port=502)
client.connect()

# Read Modbus registers in chunks of 100 registers at a time
registers_data = []
address = 0
count = 100  # Number of registers to read per request

while len(registers_data) < 300:  # Read at least 300 registers
    response = client.read_holding_registers(address=address, count=count)
    if response.isError():
        print(f"Error reading registers at address {address}")
        break
    else:
        registers_data.extend(response.registers)
    address += count

# Iterate through the rows of the Excel sheet
for _, row in df.iterrows():
    reg_address = int(row['Address'])
    channel_id = row['channel_id']
    type_ = row['Type']
    description = row['Description']
    dimension = row['Dimension'] if 'Dimension' in row else 'N/A'
    scale = float(row['Scale']) if not pd.isna(row['Scale']) else 1.0

    if reg_address >= len(registers_data):
        print(f"Address {reg_address} out of range")
        continue

    reg_val = registers_data[reg_address]

    if type_ == 'BOOL':
        value = bool(reg_val)
    elif type_ == 'INT':
        value = reg_val
    elif type_ == 'BIT':
        value = reg_val & 1
    elif type_ == 'UDINT':
        if reg_address + 3 < len(registers_data):
            reg1, reg2, reg3, reg4 = registers_data[reg_address:reg_address+4]
            value = ((reg4 << 24) | (reg3 << 16) | (reg2 << 8) | reg1) * scale
        else:
            value = 'N/A'
    elif type_ == 'LREAL':
        if reg_address + 7 < len(registers_data):
            regs = registers_data[reg_address:reg_address+8]
            combined = 0
            for i, r in enumerate(reversed(regs)):
                combined |= r << (i * 8)
            value = struct.unpack('>d', struct.pack('>Q', combined))[0] * scale
        else:
            value = 'N/A'
    else:
        if reg_address + 1 < len(registers_data):
            reg1, reg2 = registers_data[reg_address], registers_data[reg_address + 1]
            combined = (reg2 << 16) | reg1
            value = struct.unpack('>f', struct.pack('>I', combined))[0] * scale
        else:
            value = 'N/A'

    print(f"Address {reg_address} ({channel_id}): {value} - Description: {description} - Dimension: {dimension}")

client.close()
