#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path

# --- Ensure script runs as root ---
if os.geteuid() != 0:
    print("⚠️ This installer requires root privileges. Restarting with sudo...")
    os.execvp("sudo", ["sudo", sys.executable] + sys.argv)

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
USER_HOME = Path("/home/pi")  # <-- adjust if needed
ERA_PATH = USER_HOME / "Documents" / "ERA"
REPO_URL = "https://github.com/MelcherMate/ERA_Water_Purifier.git"
VENV_PATH = ERA_PATH / "venv"
ENV_FILE = ERA_PATH / ".env"

# --- Clone or update repository ---
if not ERA_PATH.exists():
    ERA_PATH.mkdir(parents=True)
    print(f"Created folder: {ERA_PATH}")
    subprocess.run(["git", "clone", REPO_URL, str(ERA_PATH)], check=True)
else:
    print(f"{ERA_PATH} exists. Pulling latest changes...")
    subprocess.run(["git", "-C", str(ERA_PATH), "pull"], check=True)

# --- Create virtual environment ---
if not VENV_PATH.exists():
    print("Creating virtual environment...")
    subprocess.run([sys.executable, "-m", "venv", str(VENV_PATH)], check=True)
else:
    print("Virtual environment already exists.")

# --- Upgrade pip and install requirements ---
venv_python = VENV_PATH / "bin" / "python3"
subprocess.run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"], check=True)
subprocess.run([str(venv_python), "-m", "pip", "install", "-r", str(ERA_PATH / "requirements.txt")], check=True)

# --- Ask user for SHORT_NAME ---
short_name = input("Enter the SHORT_NAME for this Raspberry Pi: ").strip()
if not short_name:
    print("SHORT_NAME cannot be empty. Exiting.")
    sys.exit(1)

# --- Create or overwrite .env file ---
ENV_FILE.write_text(
f"""# --- General Config ---
SHORT_NAME={short_name}
SQLITE_PATH={ERA_PATH}/data/modbus_data_from_01_07_2025.sqlite

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
print(f"✅ Created .env file at {ENV_FILE}")

# --- Define systemd services ---
SERVICES = {
    "modbus_loop.service": f"""
[Unit]
Description=ERA Water Purification Modbus Loop
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart={venv_python} {ERA_PATH}/PLC/modbus_loop.py
Restart=always
User=pi
Group=pi
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
Wants=network-online.target

[Service]
Type=simple
ExecStart={venv_python} {ERA_PATH}/PLC/sync_timescale.py
Restart=always
User=pi
Group=pi
WorkingDirectory={ERA_PATH}/PLC/
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""
}

# --- Create or update services ---
for svc_name, content in SERVICES.items():
    svc_path = Path("/etc/systemd/system") / svc_name
    if svc_path.exists():
        print(f"{svc_name} already exists. Overwriting...")
    else:
        print(f"Creating {svc_name}...")
    svc_path.write_text(content)
    
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "enable", svc_name], check=True)
    subprocess.run(["systemctl", "restart", svc_name], check=True)

# --- Verification / Status Check ---
print("\n🔎 Verifying services and virtual environment...")
for svc_name in SERVICES.keys():
    subprocess.run(["systemctl", "status", svc_name, "--no-pager"])

try:
    result = subprocess.run([str(venv_python), "--version"], capture_output=True, text=True, check=True)
    print(f"\n✅ Virtual environment Python version: {result.stdout.strip()}")
except subprocess.CalledProcessError:
    print("❌ Virtual environment Python check failed!")

try:
    result = subprocess.run([str(venv_python), "-m", "pip", "--version"], capture_output=True, text=True, check=True)
    print(f"✅ Virtual environment pip version: {result.stdout.strip()}")
except subprocess.CalledProcessError:
    print("❌ Virtual environment pip check failed!")

print("\n🎉 Installation complete. All services should be running.")
