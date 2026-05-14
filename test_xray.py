import serial, os, multiprocessing
import threading
import time
import sys
import random

# --- CONFIGURATION ---
def get_base_path():
    if getattr(sys, 'frozen', False): return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def get_config_port(line_index, default_fallback):
    try:
        # Get the path of the script directory
        # base_path = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(get_base_path(), "port_config.txt")
        
        with open(config_path, "r") as f:
            lines = f.readlines()
            # Return the specific port for this script
            return lines[line_index].strip()
    except Exception:
        # If file is missing or line doesn't exist, use the fallback
        print(f"Config not found. Falling back to {default_fallback}")
        return default_fallback

PORT = get_config_port(2, "COM8") 
BAUD = 9600

class XraySimulator:
    def __init__(self):
        self.kv_target = "0000"
        self.ma_target = "00000"
        self.temp = 25
        self.hum = 40
        self.is_running = True

        try:
            self.ser = serial.Serial(PORT, BAUD, timeout=0.1)
            print(f"--- Virtual X-Ray Controller Active on {PORT} ---")
        except Exception as e:
            print(f"ERROR: {e}")
            sys.exit()

    def listen_for_commands(self):
        while self.is_running:
            if self.ser.in_waiting > 0:
                raw = self.ser.read_until(b'\r\n').decode().strip()
                if not raw: continue
                
                # Logic to parse \02VP0800\r\n
                if "VP" in raw:
                    # Extract the 4 digits after VP
                    self.kv_target = raw.split("VP")[-1][:4]
                    # print(f"\n[X-RAY] Voltage Set to: {self.kv_target} kV")
                
                elif "CP" in raw:
                    # Extract the 5 digits after CP
                    self.ma_target = raw.split("CP")[-1][:5]
                    # print(f"\n[X-RAY] Current Set to: {self.ma_target} mA")

    def broadcast_feedback(self):
        while self.is_running:
            # Simulate slight fluctuations in environment
            cur_temp = self.temp + random.randint(-1, 1)
            cur_hum = self.hum + random.randint(-1, 1)
            
            # Format: 0800 01000 <temp> <hum>
            feedback = f"{self.kv_target} {self.ma_target} {cur_temp} {cur_hum}\r\n"
            
            try:
                self.ser.write(feedback.encode())
            except:
                pass
            
            # Print to local console for developer to see
            print(f"\r[DATA OUT]: {feedback.strip()}", end="", flush=True)
            time.sleep(0.5) # Matches the Bridge polling rate

if __name__ == "__main__":
    multiprocessing.freeze_support()
    sim = XraySimulator()
    
    # Start threads
    threading.Thread(target=sim.listen_for_commands, daemon=True).start()
    sim.broadcast_feedback()