#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path

# --- Check Internet Access ---
while True:
    answer = input("Does this Raspberry Pi have an active internet connection? (y/n): ").strip().lower()
    if answer == "y":
        break
    elif answer == "n":
        print("Installation stopped: Internet access is required.")
        sys.exit(1)
    else:
        print("Please answer 'y' or 'n'.")

# --- Configuration ---
ERA_PATH = Path("/home/admin/Documents/ERA")
REPO_URL = "https://github.com/MelcherMate/ERA_Water_Purifier.git"
VENV_PATH = ERA_PATH / "venv"
ENV_FILE = ERA_PATH / ".env"

# --- Clone or update repository ---
if not ERA_PATH.exists():
    ERA_PATH.mkdir(parents=True)
    subprocess.run(["git", "clone", REPO_URL, str(ERA_PATH)], check=True)
else:
    print(f"{ERA_PATH} exists. Pulling latest changes...")
    subprocess.run(["git", "-C", str(ERA_PATH), "pull"], check=True)

# --- Create virtual environment ---
if not VENV_PATH.exists():
    subprocess.run([sys.executable, "-m", "venv", str(VENV_PATH)], check=True)

# --- Install requirements ---
subprocess.run([str(VENV_PATH / "bin/python3"), "-m", "pip", "install", "--upgrade", "pip"], check=True)
subprocess.run([str(VENV_PATH / "bin/python3"), "-m", "pip", "install", "-r", str(ERA_PATH / "requirements.txt")], check=True)

# --- Create .env file if not exists ---
if not ENV_FILE.exists():
    ENV_FILE.write_text(
"""# --- General Config ---
SHORT_NAME=OT001
SQLITE_PATH=/home/admin/Documents/ERA/data/modbus_data_from_01_07_2025.sqlite

# --- Database ---
# - Panelko - #
#POSTGRES_URL=postgres://panelkoadmin:hFAaTvgD9bT5@rex.panelko.hu:5432/rex_db

# - DEV - #
POSTGRES_URL=postgres://postgres:password@vaphaet.ddns.net:5432/postgres

# --- Modbus Config ---
MODBUS_HOST=10.20.16.100
MODBUS_PORT=502
# Reading the data in every 60 sec
READ_INTERVAL=1800
"""
    )
    print(f"Created .env file at {ENV_FILE}")

# --- Create systemd service files ---
SERVICES = {
    "modbus_loop.service": f"""
[Unit]
Description=ERA Water Purification Modbus Loop
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart={VENV_PATH}/bin/python3 {ERA_PATH}/PLC/modbus_loop.py
Restart=always
User=admin
Group=admin
WorkingDirectory={ERA_PATH}/PLC/
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
""",
    "sync_timescale.service": f"""
[Unit]
Description=ERA DB Loader - Upload SQLite readings to TimescaleDB
After=network.target network-online.target
Wants=network-online-target

[Service]
Type=simple
ExecStart={VENV_PATH}/bin/python3 {ERA_PATH}/PLC/sync_timescale.py
Restart=always
User=admin
Group=admin
WorkingDirectory={ERA_PATH}/PLC/
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""
}

for svc_name, content in SERVICES.items():
    svc_path = Path("/etc/systemd/system") / svc_name
    print(f"Creating {svc_path}...")
    with open(svc_path, "w") as f:
        f.write(content)
    subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
    subprocess.run(["sudo", "systemctl", "enable", svc_name], check=True)
    subprocess.run(["sudo", "systemctl", "start", svc_name], check=True)

print("Installation complete. Services are running.")
