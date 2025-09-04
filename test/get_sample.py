"""
Modbus LREAL Decoder Helper
---------------------------

This script connects to a Modbus TCP server, reads 4 registers (64-bit = LREAL),
and then attempts to decode them as a double-precision float using different
byte/word ordering strategies.

Why?
-----
Different PLCs and Modbus devices store 64-bit values in different endian
formats (word-swapped, byte-swapped, etc.). This tool helps you test which
ordering matches your system by printing the decoded value for all common
variants.

Usage:
------
1. Adjust `start_address` to the Modbus register address you want to test.
2. Run the script.
3. Compare the printed decoding attempts to see which one makes sense.

"""

import struct
from pymodbus.client import ModbusTcpClient

# Modbus connection settings
HOST = '10.20.16.100'
PORT = 502

# Define the starting address to read from
start_address = 70  # <-- Replace this with the Address from your Excel file
count = 4           # LREAL = requires 4 x 16-bit registers

# Possible decoding strategies
def decode_variants(registers):
    variants = {}

    # 1. Big endian (straight order)
    raw = struct.pack('>4H', *registers)
    variants["Big endian"] = struct.unpack('>d', raw)[0]

    # 2. Little endian (straight order)
    raw = struct.pack('<4H', *registers)
    variants["Little endian"] = struct.unpack('<d', raw)[0]

    # 3. Swap word pairs (0<->1, 2<->3) + little endian
    swapped = [registers[1], registers[0], registers[3], registers[2]]
    raw = struct.pack('<4H', *swapped)
    variants["Word swap + little endian"] = struct.unpack('<d', raw)[0]

    # 4. Byte-swap each register, big endian packing
    swapped_bytes = b''.join(struct.pack('>H', r)[::-1] for r in registers)
    variants["Byte swap + big endian"] = struct.unpack('>d', swapped_bytes)[0]

    # 5. Byte-swap each register, little endian packing
    swapped_bytes = b''.join(struct.pack('<H', r)[::-1] for r in registers)
    variants["Byte swap + little endian"] = struct.unpack('<d', swapped_bytes)[0]

    return variants


# --- Main execution ---
client = ModbusTcpClient(HOST, port=PORT)
client.connect()

try:
    response = client.read_holding_registers(address=start_address, count=count)
    if response.isError():
        print(f"Error reading registers at address {start_address}")
    else:
        registers = response.registers
        print(f"Registers at address {start_address}:")
        for i, reg in enumerate(registers):
            print(f"  Reg {start_address + i}: 0x{reg:04X} (dec {reg})")

        if len(registers) == 4:
            print("\nDecoding attempts for LREAL (64-bit float):")
            results = decode_variants(registers)
            for name, value in results.items():
                print(f"  {name}: {value}")

finally:
    client.close()
