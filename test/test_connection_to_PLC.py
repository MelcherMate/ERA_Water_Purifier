from pymodbus.client import ModbusTcpClient

# Configuration parameters from the email
PLC_IP = "10.20.16.100"  # PLC IP address
PLC_PORT = 502            # Modbus TCP port
NETWORK = "10.20.16.0/24"   # Network address and mask
GATEWAY = "10.20.16.1"      # Gateway address
DNS = "10.20.16.1"          # DNS server address
MY_IP = "10.20.16.200"     # Your device's IP address

def check_modbus_connection():
    try:
        # Establish connection
        client = ModbusTcpClient(PLC_IP, port=PLC_PORT)
        connection = client.connect()

        if connection:
            print(f"------------------------------------------------------")
            print(f"Successfully connected to PLC on ({PLC_IP}:{PLC_PORT})")
            print(f"------------------------------------------------------")
        else:
            print(f"------------------------------------------------------")
            print(f"Failed to connect to PLC on ({PLC_IP}:{PLC_PORT})")
            print(f"------------------------------------------------------")

        # Close connection
        client.close()
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    print(f"Network parameters:")
    print(f"Network: {NETWORK}")
    print(f"Gateway: {GATEWAY}")
    print(f"DNS: {DNS}")
    print(f"PLC address: {PLC_IP}:{PLC_PORT}")
    print(f"Your device's address: {MY_IP}")
    print(f"------------------------------------------------------")

    check_modbus_connection()