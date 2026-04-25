import serial
import sqlite3
import time
import os

# --- CONFIGURATION ---
local_app_data = os.environ.get('LOCALAPPDATA')
package_folder = "1b93a6a9-009e-4781-8c7b-31643d1c1f3b_zzsj02r91hwve"
DB_PATH = os.path.join(local_app_data, "Packages", package_folder, "LocalState", "db.sqlite")
# Absolute path to the LocalState folder
CMD_FILE = os.path.join(local_app_data, "Packages", package_folder, "LocalState", "mega_cmd.txt")

BRIDGE_PORT = 'COM7' 
BAUD = 9600

def db_query(query, params=(), fetch=False):
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor.fetchone() if fetch else None
    except Exception as e:
        print(f"DB Error: {e}")
        return None

# def safety_check(bit_string):
    
#     if len(bit_string) >= 9 and all(c in '01' for c in bit_string):
#         if bit_string[0] == '0':
#             print("\n[SAFETY ALERT] FAILURE: MAINS / SMPS")
#         if bit_string[6] == '1':
#             print("\n[SAFETY ALERT] FAILURE: DOOR OPEN")
#         if bit_string[7] == '1':
#             print("\n[SAFETY ALERT] FAILURE: FRONT LID")
#         if bit_string[8] == '1':
#             print("\n[SAFETY ALERT] FAILURE: REJECTION LID")
    
def run_bridge():
    try:
        ser = serial.Serial(BRIDGE_PORT, BAUD, timeout=0.1)
        print(f"Bridge Active on {BRIDGE_PORT}. Polling Arduino...")
    except Exception as e:
        print(f"Error: {e}")
        return

    last_state = 0
    last_feeder = 0

    while True:
        try:
            # --- 0. RELAY GUI COMMANDS (Option B) ---
            if os.path.exists(CMD_FILE):
                try:
                    with open(CMD_FILE, "r") as f:
                        gui_cmd = f.read().strip() # This will be "setPin 49 0"
                    if gui_cmd:
                        ser.write(f"{gui_cmd}\n".encode())
                        print(f"\n[BRIDGE] Relay Message: {gui_cmd}")
                    os.remove(CMD_FILE)
                except Exception as e:
                    print(f"Relay Error: {e}")

            # POLL THE ARDUINO: Send the getStatus command
            ser.write(b"getStatus\n")
            
            # READ THE RESPONSE: Catch the BITS from Arduino
            if ser.in_waiting > 0:
                response = ser.readline().decode().strip()
                print(f"\r[BRIDGE RECEIVED]: {response}", end="", flush=True)
                
                # --- RUN SAFETY CHECK ---
                # safety_check(response)
                    

            # CHECK DATABASE: For Phase Changes
            row = db_query("SELECT state, feeder, align_mode FROM control WHERE id=1", fetch=True)
            if row:
                state, feeder, align_mode = row
                
                # --- Machine State Logic ---
                if state == 1 and last_state == 0:
                    ser.write(b"StartMachine\n")
                    print("\n [BRIDGE] Sent: StartMachine")

                    time.sleep(0.1) 
                    # Check the mode selected on GUI BEFORE the start
                    if align_mode == 1:
                        ser.write(b"AlignMode\n")
                        print("[BRIDGE] Startup Mode: ALIGNMENT")
                    else:
                        ser.write(b"ResumeNormalMode\n")
                        print("[BRIDGE] Startup Mode: NORMAL")
                elif state == 0 and last_state == 1:
                    print(last_state)
                    ser.write(b"StopMachine\n")
                    print("\n [BRIDGE] Sent: StopMachine")
                             
                if state == 1: 
                    if feeder == 1 and last_feeder == 0:
                        ser.write(b"StartFeeder\n")
                        print("\n [BRIDGE] Sent: StartFeeder")
                    elif feeder == 0 and last_feeder == 1:
                        ser.write(b"StopFeeder\n")
                        print("\n [BRIDGE] Sent: StopFeeder")
        
                # --- Update Tracking Variables ---
                last_state = state
                last_feeder = feeder

            time.sleep(1) 
        except Exception as e:
            print(f"\nBridge Error: {e}")
            break

if __name__ == "__main__":
    run_bridge()