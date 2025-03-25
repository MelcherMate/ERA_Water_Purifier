from pymodbus.client import ModbusTcpClient
# Set up the PLC IP address and Modbus Port
PLC_IP = "192.168.1.100" #Change to set the PLC IP
PLC_PORT = 502	#Default Modbus TCP Port

def check_modbus_conncetion():
	try:
		#Open connection
		client = ModbusTcpClient(PLC_IP, port=PLC_PORT)
		conncetion = client.connect()
		
		if conncetion:
			print(f"------------------------------------------------------")
			print(f"Successfully connected to PLC on ({PLC_IP}:{PLC_PORT})")
			print(f"------------------------------------------------------")
		else:
			print(f"------------------------------------------------------")
			print(f"Failed to connect to PLC on ({PLC_IP}:{PLC_PORT})")
			print(f"------------------------------------------------------")
			
		#Close connection
		client.close()
	except Exception as e:
		print(f"An error occured: {e}")
		
		
if __name__ == "__main__":
	check_modbus_conncetion()
