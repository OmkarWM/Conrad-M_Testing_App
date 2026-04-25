import serial
import time
import random

# --- CONFIGURATION ---
UNO_PORT = 'COM11' # Connects to COM10
BAUD = 9600

# The List of valid hex codes 
HEX_COMMANDS = [0xA1, 0xB1, 0xC1, 0xD1, 0xE1, 0xF1, 0xF2, 0xF3, 0xF4]

def run_bridge():
    try:
        ser = serial.Serial(UNO_PORT, BAUD, timeout=0.1)
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