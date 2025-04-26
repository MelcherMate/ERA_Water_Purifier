import struct
from pymodbus.client import ModbusTcpClient

# Modbus kapcsol�d�s
client = ModbusTcpClient('10.20.16.100', port=502)
client.connect()

# Itt add meg, milyen kezd? c�mt?l olvassunk (p�ld�ul 2640)
start_address = 70  # <-- Ezt cser�ld ki a probl�m�s csatorna Address �rt�k�re az Excelb?l
count = 4  # LREAL = 4 db 16-bites regiszter kell

try:
    response = client.read_holding_registers(address=start_address, count=count)
    if response.isError():
        print(f"Error reading registers at address {start_address}")
    else:
        registers = response.registers
        print(f"Registers at address {start_address}:")
        for i, reg in enumerate(registers):
            print(f"  Reg {start_address + i}: 0x{reg:04X} (dec {reg})")

        # Most csin�lunk p�rf�le k�s�rleti �sszeilleszt�st:
        if len(registers) == 4:
            print("\nDifferent decoding attempts:")

            # 1. Egyszer? �sszepakol�s, big endian
            raw = struct.pack('>4H', *registers)
            print(f"  Big endian float64: {struct.unpack('>d', raw)[0]}")

            # 2. Egyszer? �sszepakol�s, little endian
            raw = struct.pack('<4H', *registers)
            print(f"  Little endian float64: {struct.unpack('<d', raw)[0]}")

            # 3. Regiszter swap (0<->1, 2<->3) + little endian
            swapped = [registers[1], registers[0], registers[3], registers[2]]
            raw = struct.pack('<4H', *swapped)
            print(f"  Swap reg + little endian float64: {struct.unpack('<d', raw)[0]}")

            # 4. Byte swap minden regiszteren bel�l, majd �sszepakol�s
            swapped_bytes = b''.join(struct.pack('>H', r)[::-1] for r in registers)
            print(f"  Byte-swap + big endian float64: {struct.unpack('>d', swapped_bytes)[0]}")

finally:
    client.close()
