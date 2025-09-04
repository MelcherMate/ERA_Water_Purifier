# ERA Data Acquisition & Sync System

This project is a complete **data acquisition and synchronization package**, which  
- reads registers from industrial controllers (PLC) via **ModbusTCP**,  
- stores the raw data locally in an **SQLite database**,  
- synchronizes them with a **TimescaleDB** database,  
- and automatically generates **delta values** (e.g., water meter consumption differences).  

---

## Project Structure

project-root/
│
├── RegisterList/
│ └── PanelKOVK_KommRef.xlsx # Excel file with Modbus register definitions
│
├── data/
│ ├── modbus_data_from_01_17_2025.sqlite # Data collected after 01.07.2025
│ ├── modbus_data.sqlite # Data collected before 01.07.2025
│ └── modbus_data_oneshot.sqlite # One-shot read result
│
├── PLC/
│ ├── modbus_oneshot_reader.py # One-shot Modbus read and save to SQLite
│ ├── modbus_loop.py # Continuous Modbus read in a loop
│ ├── sync_timescale.py # Sync data to TimescaleDB + delta calculation
│ └── sync_oneshot_timescale.py # Full upload to TimescaleDB (initial load)
│
├── test/
│ ├── db_clearer.py # DANGER! clears the whole TimescaleDB
│ ├── get_sample.py # Decodes modbus data and prints it in console
│ └── test_connection_to_plc.py # Tests the network between the rPI and the PLC
│
├── venv/
├── .gitignore
├── README.mds
└── requirements.txt

---

## ⚙️ Installation

1. **Requirements**  
   - Python 3.10+  
   - PostgreSQL + TimescaleDB  
   - SQLite  
   - PLC accessible via ModbusTCP  

2. **Install Python dependencies**  

```bash
pip install -r requirements.txt
```
# Delta Calculation

The system automatically calculates consumption deltas for two water meters:

A70 Raw Water Delta Volume
Source: PLC_VK.Application.GVL_HMI.rdata.daq_raw.A70_90M2_VOL

A71 Treated Water Delta Volume
Source: PLC_VK.Application.GVL_HMI.rdata.daq_raw.A71_90M1_VOL

**delta = current_value - previous_value**

The deltas are stored as separate channels in TimescaleDB.

## Data Flow Diagram

┌────────────┐ ModbusTCP ┌────────────┐
│ PLC │ ──────────────────▶ │ Python │
│ Device │ │ Scripts │
└────────┘ └─────────┘
│
│ Stores
▼
┌────────────┐
│ SQLite │
│ Database │
└────────────┘
│
│ Sync
▼
┌───────────────┐
│ TimescaleDB │
│ (Main Storage)│
└───────────────┘

## 🛠 Service Files Overview

This project uses **two main systemd service files**:

### 1. `sync_timescale.service`
- Continuously reads data from the Modbus-connected PLC, stores it in SQLite, calculates delta values, and uploads everything to TimescaleDB.

### 2. `modbus_loop.service`
- Previously handled one-shot Modbus reads and stored them in SQLite. Not needed if `sync_timescale` is running.

### Managing Services

1. **View services** 
   - List all running services:
   ```bash
   systemctl list-units --type=service --state=running
   ```
   - List all services (running or inactive):
   ```bash
   systemctl list-units --type=service
   ```
2. **Edit a service file**
   ```bash
   sudo nano /etc/systemd/system/<file_name>.service
   ```
   - After editing, save with Ctrl+O, press Enter, then exit with Ctrl+X.
   - Reload systemd and restart the service:
   ```bash
   sudo systemctl daemon-reloa
   ```
   - or
   ```bash
   sudo systemctl restart <file_name>.service
   ```
