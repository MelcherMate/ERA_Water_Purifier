from pymodbus.client import ModbusTcpClient
import struct

def read_sensor_data(client, address, num_registers):
    """
    Function to read sensor data from Modbus registers.
    :param client: The Modbus client instance
    :param address: The starting address of the registers
    :param num_registers: The number of registers to read
    :return: A list of register values
    """
    # Read registers from the Modbus server
    response = client.read_holding_registers(address=address, count=num_registers)

    # Check if the response is valid
    if response.isError():
        print(f"Error reading registers at address {address}")
        return None
    else:
        return response.registers

def process_registers(sensor_type, registers):
    """
    Process the raw registers based on sensor type.
    :param sensor_type: The type of the sensor (e.g., pH, temperature)
    :param registers: The raw register data
    :return: Interpreted sensor value
    """
    if sensor_type == 'ph':
        # Example: For a pH sensor, we assume reg2 and reg3 are combined for the pH value.
        reg2 = registers[1]
        reg3 = registers[2]
        combined = (reg3 << 16) | reg2
        # Convert the 32-bit value to a floating-point number
        float_value = struct.unpack('>f', struct.pack('>I', combined))[0]
        return float_value

    elif sensor_type == 'temperature':
        # Example: For temperature sensor, let's assume simple scaling
        # We use just the first register in this example
        reg1 = registers[0]
        temperature = reg1 * 0.1  # Assume each register unit corresponds to 0.1 �C
        return temperature

    elif sensor_type == 'status_flag':
        # Example: For status flag, use the first register, checking the LSB
        reg1 = registers[0]
        flag = reg1 & 0x0001  # Extract the least significant bit
        return "Active" if flag else "Inactive"

    else:
        print(f"Unknown sensor type: {sensor_type}")
        return None

def main():
    # Connect to the Modbus server
    client = ModbusTcpClient('10.20.16.100', port=502)
    client.connect()

    # Sensor addresses and types (you can extend this for 400 sensors)
    sensor_addresses = {
        1: {'type': 'ph', 'address': 0, 'num_registers': 10},
        2: {'type': 'temperature', 'address': 10, 'num_registers': 2},
        3: {'type': 'status_flag', 'address': 20, 'num_registers': 1},
        # Add more sensors here with different addresses and types
    }

    # Loop through each sensor to read and process data
    for sensor_id, sensor_info in sensor_addresses.items():
        print(f"Reading data for Sensor {sensor_id} (Type: {sensor_info['type']})")

        # Read raw register data
        registers = read_sensor_data(client, sensor_info['address'], sensor_info['num_registers'])

        if registers:
            # Process the data based on the sensor type
            result = process_registers(sensor_info['type'], registers)
            print(f"Sensor {sensor_id} value: {result}")

    # Close the client connection
    client.close()

if __name__ == "__main__":
    main()
