import serial, os
import time
import random

# --- CONFIGURATION ---
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
BRIDGE_PORT = get_config_port(5, "COM11")
BAUD = 9600

# The List of valid hex codes 
HEX_COMMANDS = [0xA1, 0xB1, 0xC1, 0xD1, 0xE1, 0xF1, 0xF2, 0xF3, 0xF4]

def run_bridge():
    try:
        ser = serial.Serial(BRIDGE_PORT, BAUD, timeout=0.1)
        print("--- Uno Bridge: Active---")
    except Exception as e:
        print(f"Bridge Error: {e}"); return

    while True:
        # Randomly pick a command from the list
        cmd = random.choice(HEX_COMMANDS)
        ser.write(bytes([cmd]))
        print(f"\r[BRIDGE]: 0x{cmd:02X} sent to Uno ", end="", flush=True)
        time.sleep(0.5) 

if __name__ == "__main__":
    run_bridge()