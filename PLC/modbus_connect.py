import time
from pymodbus.client import ModbusTcpClient
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.constants import Endian

# Configuration parameters
PLC_IP = "10.20.16.100"  # PLC IP address
PLC_PORT = 502           # Modbus TCP port

# Modbus register configurations
START_ADDRESS_HOLDING_REGISTERS = 0
COUNT_HOLDING_REGISTERS = 125
START_ADDRESS_INPUT_REGISTERS = 0
COUNT_INPUT_REGISTERS = 125
START_ADDRESS_COILS = 0
COUNT_COILS = 125
START_ADDRESS_DISCRETE_INPUTS = 0
COUNT_DISCRETE_INPUTS = 125

def decode_registers(registers):
    try:
        decoder = BinaryPayloadDecoder.fromRegisters(registers, byteorder=Endian.Big)
        decoded_value = decoder.decode_16bit_int  # Adjust based on PLC data format
        return decoded_value
    except Exception as e:
        return f"Decoding error: {e}"

def read_holding_registers(client, start_address, count):
    try:
        result = client.read_holding_registers(address=start_address, count=count)
        print(f"\nHolding Registers ({start_address} - {start_address + count - 1}):")
        if not result.isError():
            print(f"Raw response: {result.registers}")
            decoded_value = decode_registers(result.registers)
            print(f"Decoded: {decoded_value}")
        else:
            print(f"Error reading holding registers: {result}")
    except Exception as e:
        print(f"Error reading holding registers: {e}")

def read_input_registers(client, start_address, count):
    try:
        result = client.read_input_registers(address=start_address, count=count)
        print(f"\nInput Registers ({start_address} - {start_address + count - 1}):")
        if not result.isError():
            print(f"Raw response: {result.registers}")
            decoded_value = decode_registers(result.registers)
            print(f"Decoded: {decoded_value}")
        else:
            print(f"Error reading input registers: {result}")
    except Exception as e:
        print(f"Error reading input registers: {e}")

def read_coils(client, start_address, count):
    try:
        result = client.read_coils(address=start_address, count=count)
        if not result.isError():
            print(f"\nCoils ({start_address} - {start_address + count - 1}): {result.bits}")
        else:
            print(f"Error reading coils: {result}")
    except Exception as e:
        print(f"Error reading coils: {e}")

def read_discrete_inputs(client, start_address, count):
    try:
        result = client.read_discrete_inputs(address=start_address, count=count)
        if not result.isError():
            print(f"\nDiscrete Inputs ({start_address} - {start_address + count - 1}): {result.bits}")
        else:
            print(f"Error reading discrete inputs: {result}")
    except Exception as e:
        print(f"Error reading discrete inputs: {e}")

if __name__ == "__main__":
    print(f"Connecting to PLC at {PLC_IP}:{PLC_PORT}...")
    client = ModbusTcpClient(host=PLC_IP, port=PLC_PORT)

    try:
        if client.connect():
            print("Connection successful!")
            while True:
                print("\n--- Reading Modbus Data ---")
                read_holding_registers(client, START_ADDRESS_HOLDING_REGISTERS, COUNT_HOLDING_REGISTERS)
                read_input_registers(client, START_ADDRESS_INPUT_REGISTERS, COUNT_INPUT_REGISTERS)
                read_coils(client, START_ADDRESS_COILS, COUNT_COILS)
                read_discrete_inputs(client, START_ADDRESS_DISCRETE_INPUTS, COUNT_DISCRETE_INPUTS)
                time.sleep(1)
        else:
            print("Failed to connect to PLC.")
    except KeyboardInterrupt:
        print("\nUser interrupted the program. Exiting...")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if client.is_socket_open():
            client.close()