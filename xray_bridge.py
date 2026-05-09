import serial, sys
import time
import os
import random

# --- CONFIGURATION ---
local_app_data = os.environ.get('LOCALAPPDATA')
package_folder = "1b93a6a9-009e-4781-8c7b-31643d1c1f3b_zzsj02r91hwve"
DB_PATH = os.path.join(local_app_data, "Packages", package_folder, "LocalState", "db.sqlite")

def get_config_port(line_index, default_fallback):
    try:
        # Get the path of the script directory
        base_path = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base_path, "port_config.txt")
        
        with open(config_path, "r") as f:
            lines = f.readlines()
            # Return the specific port for this script
            return lines[line_index].strip()
    except Exception:
        # If file is missing or line doesn't exist, use the fallback
        print(f"Config not found. Falling back to {default_fallback}")
        return default_fallback
BRIDGE_PORT = get_config_port(3, "COM9")
BAUD = 9600

# def db_query(query, params=(), fetch=False):
#     try:
#         with sqlite3.connect(DB_PATH, timeout=10) as conn:
#             conn.execute("PRAGMA journal_mode=WAL;")
#             cursor = conn.execute(query, params)
#             return cursor.fetchone() if fetch else None
#     except:
#         return None

def run_xray_bridge():
    try:
        ser = serial.Serial(BRIDGE_PORT, BAUD, timeout=0.1)
        print(f"--- X-Ray Automated Bridge Active on {BRIDGE_PORT} ---")
    except Exception as e:
        print(f"Connection Error: {e}"); return

    while True:
        try:
            # Check if machine is ON
            # row = db_query("SELECT state FROM control WHERE id=1", fetch=True)
            
            # if row and row[0] == 1:
                #  GENERATE DATA
                # rand_kv = round(random.uniform(40.0, 100.0), 1)
                # rand_ma = round(random.uniform(0.1, 5.0), 2)

                # FORMAT COMMANDS
                kv_cmd = "0800"
                ma_cmd = "01000" 
                
                # SEND (TX)
                ser.write(f"\x02VP{kv_cmd}\r\n".encode())
                ser.write(f"\x02CP{ma_cmd}\r\n".encode())

                # RECEIVE (RX)
                rx_info = "Waiting..."
                if ser.in_waiting > 0:
                    raw = ser.readline().decode().strip()
                    # Clean the raw string of non-printable chars for console
                    rx_info = "".join(c for c in raw if c.isprintable() or c.isspace())
                  
                    
                # TX: Shows what was just pushed | RX: Shows what the simulator returned
                print(f"\r[TX]: VP{kv_cmd} CP{ma_cmd} | [RX]: {rx_info}", end="", flush=True)
            
            # else:
            #     print(f"\r[XRAY]: STANDBY (Machine Off) {' ':<50}", end="", flush=True)

                time.sleep(0.5)
        except Exception as e:
            print(f"\nError: {e}"); break

if __name__ == "__main__":
    run_xray_bridge()