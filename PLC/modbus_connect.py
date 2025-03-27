import pandas as pd
from pymodbus.client import ModbusTcpClient
import struct
import os

# Configuration parameters
PLC_IP = "10.20.16.100"  # PLC IP address
PLC_PORT = 502           # Modbus TCP port

# Load register mapping from Excel file
base_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(base_dir, "..", "RegisterList", "PanelKOVK_KommRef.xlsx")
df = pd.read_excel(file_path, sheet_name="Komm. ref.")

# Create Modbus client
client = ModbusTcpClient(PLC_IP, port=PLC_PORT)

def convert_value(data, data_type):
    """Converts raw Modbus register data to the correct data type."""
    if data_type == "BOOL":
        return bool(data)
    elif data_type == "INT":
        return int(data)
    elif data_type == "FLOAT":
        packed = struct.pack('>HH', data[0], data[1])  # Big-endian float conversion
        return struct.unpack('>f', packed)[0]
    return data

# Connect to PLC
if client.connect():
    print("Connected to PLC")
    try:
        for index, row in df.iterrows():
            try:
                address = int(row["Value"])  # Modbus register address
            except ValueError:
                print(f"Skipping non-numeric address: {row['Value']}")
                continue
            
            data_type = row["Type"]    # Data type
            bit_pos = row["Bit"] if "Bit" in row and not pd.isna(row["Bit"]) else None
            
            response = client.read_holding_registers(address=address, count=2 if data_type == "FLOAT" else 1)
            if response.isError():
                print(f"Error reading register {address}")
                continue
            
            value = response.registers
            if bit_pos is not None:
                value = (value[0] >> int(bit_pos)) & 1
            else:
                value = convert_value(value, data_type)
            
            print(f"{row['Value']}: {value}")
    except Exception as e:
        print("Error:", e)
    finally:
        client.close()
        print("Connection closed")
else:
    print("Failed to connect to PLC")