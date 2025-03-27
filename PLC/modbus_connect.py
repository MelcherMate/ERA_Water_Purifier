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
        # For BOOL, we need to check the specific bit in the register value
        return bool(data[0])
    elif data_type == "INT":
        # For INT, just convert the first register value to integer
        return int(data[0])
    elif data_type == "FLOAT":
        # For FLOAT, two registers are used to store the value
        packed = struct.pack('>HH', data[0], data[1])  # Big-endian float conversion
        return struct.unpack('>f', packed)[0]
    elif data_type == "STRING":
        # If the data type is STRING, we handle it differently (can be an ASCII string or a fixed-length string)
        return ''.join(chr(val) for val in data if val != 0)  # Assuming data are ASCII values
    return data[0] if data else None

# Connect to PLC
if client.connect():
    print("Connected to PLC")
    try:
        for index, row in df.iterrows():
            try:
                address = int(row["Variable"])  # Modbus register address
            except ValueError:
                print(f"Skipping non-numeric address: {row['Variable']}")
                continue
            
            data_type = row["Type"]    # Data type (e.g., BOOL, INT, FLOAT, STRING)
            bit_pos = row["Bit"] if "Bit" in row and not pd.isna(row["Bit"]) else None
            
            # Based on the data type, decide how many registers to read
            if data_type == "FLOAT":
                count = 2  # Two registers are needed for a FLOAT
            else:
                count = 1  # One register for other types
            
            response = client.read_holding_registers(address=address, count=count)
            if response.isError():
                print(f"Error reading register {address}")
                continue
            
            value = response.registers
            if bit_pos is not None:
                # If bit position is specified, extract the bit value
                value = (value[0] >> int(bit_pos)) & 1
            else:
                # Convert value based on the type
                value = convert_value(value, data_type)
            
            # Print the result
            print(f"{row['Variable']}: {value}")
    except Exception as e:
        print("Error:", e)
    finally:
        client.close()
        print("Connection closed")
else:
    print("Failed to connect to PLC")
