import pandas as pd
from pymodbus.client import ModbusTcpClient
import struct
import os

# Define the relative path to the Excel file
file_path = 'RegisterList/PanelKOVK_KommRef.xlsx'

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Construct the absolute path by joining the script directory and the relative path
absolute_file_path = os.path.join(script_dir, file_path)

# Load the Excel file
df = pd.read_excel(absolute_file_path, engine='openpyxl')

# Connect to the Modbus server
client = ModbusTcpClient('10.20.16.100', port=502)
client.connect()


# The total number of registers you want to read (252 registers)
total_registers = 252

# Read Modbus registers in chunks of 100 registers at a time
registers_data = []
address = 0
count = 100  # Number of registers to read per request

while len(registers_data) < total_registers:
    # Read the registers
    response = client.read_holding_registers(address=address, count=count)

    # Check if the response is valid
    if response.isError():
        print("Error reading registers")
        break
    else:
        # Add the registers to the list
        registers_data.extend(response.registers)

    # Update the address to read the next chunk of registers
    address += count

# Now we have all the registers, we can process them
# print("Raw register values:", registers_data)

# Iterate through the rows of the Excel sheet
for i, row in df.iterrows():
    if i >= len(registers_data):  # Stop if we reach the end of the available registers
        break

    channel_id = row['channel_id']  # Use the column name 'channel_id'
    type_ = row['Type']
    description = row['Description']  # Get the description from the table
    dimension = row['Dimension'] if 'Dimension' in row else 'N/A'  # Get the dimension from the table (if exists)
    modbus_register_value = registers_data[i]  # Get the corresponding register value

    # Interpret the data based on its type
    if type_ == 'BOOL':
        # If BOOL, then return true/false
        value = bool(modbus_register_value)
        print(f"Register {i+1} ({channel_id}): {value} - Description: {description} - Dimension: {dimension}")
    elif type_ == 'INT':
        # If INT, then return the integer value (e.g. 0, 1, 2)
        value = modbus_register_value
        print(f"Register {i+1} ({channel_id}): {value} - Description: {description} - Dimension: {dimension}")
    elif type_ == 'BIT':
        # If BIT, then check the bit (0 or 1)
        value = modbus_register_value & 1  # Checking the first bit
        print(f"Register {i+1} ({channel_id}): {value} - Description: {description} - Dimension: {dimension}")
    elif type_ == 'UDINT':
        # If UDINT (unsigned 32-bit), combine four 16-bit registers
        if len(registers_data) > i + 3:  # Ensure there are enough registers
            reg1 = registers_data[i]
            reg2 = registers_data[i + 1]
            reg3 = registers_data[i + 2]
            reg4 = registers_data[i + 3]
            # Combine the four registers to form the 32-bit UDINT
            udint_value = (reg4 << 24) | (reg3 << 16) | (reg2 << 8) | reg1
            print(f"Register {i+1} ({channel_id}): {udint_value} - Description: {description} - Dimension: {dimension}")
    elif type_ == 'LREAL':
        # If LREAL (64-bit floating point), combine eight 16-bit registers
        if len(registers_data) > i + 7:  # Ensure there are enough registers
            reg1 = registers_data[i]
            reg2 = registers_data[i + 1]
            reg3 = registers_data[i + 2]
            reg4 = registers_data[i + 3]
            reg5 = registers_data[i + 4]
            reg6 = registers_data[i + 5]
            reg7 = registers_data[i + 6]
            reg8 = registers_data[i + 7]
            # Combine the eight registers to form the 64-bit LREAL
            combined = (reg8 << 48) | (reg7 << 32) | (reg6 << 16) | (reg5)
            combined |= (reg4 << 56) | (reg3 << 40) | (reg2 << 24) | (reg1 << 8)
            # Convert the 64-bit combined value into a floating point number
            lreal_value = struct.unpack('>d', struct.pack('>Q', combined))[0]
            print(f"Register {i+1} ({channel_id}): {lreal_value} - Description: {description} - Dimension: {dimension}")
    else:
        # For other types (e.g., FLOAT)
        # Combine registers and convert to a floating-point number
        if len(registers_data) > i + 1:  # Check if there's a next register
            reg1 = registers_data[i]
            reg2 = registers_data[i + 1]
            combined = (reg2 << 16) | reg1
            float_value = struct.unpack('>f', struct.pack('>I', combined))[0]
            print(f"Register {i+1} ({channel_id}): {float_value} - Description: {description} - Dimension: {dimension}")

# Disconnect from the Modbus server
client.close()