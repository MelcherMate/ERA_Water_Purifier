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
df = pd.read_excel(file_path, engine='openpyxl')

# Connect to the Modbus server
client = ModbusTcpClient('10.20.16.100', port=502)
client.connect()


# The total number of sensors you want to read (252 sensors)
total_sensors = 252

# Read Modbus registers in chunks of 100 registers at a time
registers = []
address = 0
count = 100  # Number of registers to read per request

while len(registers) < total_sensors:
    # Read the registers
    response = client.read_holding_registers(address=address, count=count)

    # Check if the response is valid
    if response.isError():
        print("Error reading registers")
        break
    else:
        # Add the registers to the list
        registers.extend(response.registers)

    # Update the address to read the next chunk of registers
    address += count

# Now we have all the registers, we can process them
print("Raw register values:", registers)

# Iterate through the rows of the Excel sheet
for i, row in df.iterrows():
    if i >= len(registers):  # Stop if we reach the end of the available registers
        break
    
    variable = row['Variable']
    type_ = row['Type']
    description = row['Description']  # Get the description from the table
    dimension = row['Dimension'] if 'Dimension' in row else 'N/A'  # Get the dimension from the table (if exists)
    modbus_register = registers[i]  # Get the corresponding register value

    # Interpret the data based on its type
    if type_ == 'BOOL':
        # If BOOL, then return true/false
        value = bool(modbus_register)
        print(f"Sensor {i+1} ({variable}): {value} - Description: {description} - Dimension: {dimension}")
    elif type_ == 'INT':
        # If INT, then return the integer value (e.g. 0, 1, 2)
        value = modbus_register
        print(f"Sensor {i+1} ({variable}): {value} - Description: {description} - Dimension: {dimension}")
    elif type_ == 'BIT':
        # If BIT, then check the bit (0 or 1)
        value = modbus_register & 1  # Checking the first bit
        print(f"Sensor {i+1} ({variable}): {value} - Description: {description} - Dimension: {dimension}")
    elif type_ == 'UDINT':
        # If UDINT (unsigned 32-bit), combine four 16-bit registers
        if len(registers) > i + 3:  # Ensure there are enough registers
            reg1 = registers[i]
            reg2 = registers[i + 1]
            reg3 = registers[i + 2]
            reg4 = registers[i + 3]
            # Combine the four registers to form the 32-bit UDINT
            udint_value = (reg4 << 24) | (reg3 << 16) | (reg2 << 8) | reg1
            print(f"Sensor {i+1} ({variable}): {udint_value} - Description: {description} - Dimension: {dimension}")
    elif type_ == 'LREAL':
        # If LREAL (64-bit floating point), combine eight 16-bit registers
        if len(registers) > i + 7:  # Ensure there are enough registers
            reg1 = registers[i]
            reg2 = registers[i + 1]
            reg3 = registers[i + 2]
            reg4 = registers[i + 3]
            reg5 = registers[i + 4]
            reg6 = registers[i + 5]
            reg7 = registers[i + 6]
            reg8 = registers[i + 7]
            # Combine the eight registers to form the 64-bit LREAL
            combined = (reg8 << 48) | (reg7 << 32) | (reg6 << 16) | (reg5)
            combined |= (reg4 << 56) | (reg3 << 40) | (reg2 << 24) | (reg1 << 8)
            # Convert the 64-bit combined value into a floating point number
            lreal_value = struct.unpack('>d', struct.pack('>Q', combined))[0]
            print(f"Sensor {i+1} ({variable}): {lreal_value} - Description: {description} - Dimension: {dimension}")
    else:
        # For other types (e.g., FLOAT)
        # Combine registers and convert to a floating-point number
        if len(registers) > i + 1:  # Check if there's a next register
            reg1 = registers[i]
            reg2 = registers[i + 1]
            combined = (reg2 << 16) | reg1
            float_value = struct.unpack('>f', struct.pack('>I', combined))[0]
            print(f"Sensor {i+1} ({variable}): {float_value} - Description: {description} - Dimension: {dimension}")

# Disconnect from the Modbus server
client.close()
