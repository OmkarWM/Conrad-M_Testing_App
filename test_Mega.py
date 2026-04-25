import serial
import threading
import time
import sys

# --- CONFIGURATION ---
# Set this to the other end of your virtual pair (e.g., COM6 if Bridge is on COM7)
PORT = 'COM6'  
BAUD = 9600
NUM_PINS = 70

# Pin Definitions
RejectionConPIN = 44; ConveyorPIN = 38; XrayPIN = 46
CameraPIN = 42; FeederPIN = 40; BlackButtonPIN = 36
SMPSMachineSTATUS = 49; ConveyorSTATUS = 41; XraySTATUS = 43
CameraSTATUS = 45; FeederSTATUS = 47; DoorsSTATUS = 34
FlidSTATUS = 37; RlidSTATUS = 35; PowerSTATUS = 51
UpsInpSTATUS = 53; RejectionConSTATUS = 39

# --- INITIALIZATION ---
pins = {i: {"value": 0} for i in range(NUM_PINS)}
STATUS_PIN_MAP = [
    SMPSMachineSTATUS, ConveyorSTATUS, XraySTATUS, CameraSTATUS,
    FeederSTATUS, RejectionConSTATUS, DoorsSTATUS, FlidSTATUS,
    RlidSTATUS, PowerSTATUS, UpsInpSTATUS, BlackButtonPIN
]

# Default Safety States (Machine is healthy at start)
pins[SMPSMachineSTATUS]["value"] = 1
pins[PowerSTATUS]["value"] = 1
pins[UpsInpSTATUS]["value"] = 1

stop_polling = threading.Event()

try:
    ser = serial.Serial(PORT, BAUD, timeout=0.05)
except Exception as e:
    print(f"ERROR: Could not open {PORT}. {e}")
    sys.exit()

def send_to_com(message):
    try:
        # Standardized format for C++ and Bridge to read
        ser.write(f"{message}\n".encode())      
    except:
        pass

# --- MACHINE LOGIC ---
def safety_check():
    """Immediately stops machine if any safety interlock is triggered"""
    if (pins[SMPSMachineSTATUS]["value"] == 0 or pins[DoorsSTATUS]["value"] == 1 or 
        pins[PowerSTATUS]["value"] == 0 or pins[UpsInpSTATUS]["value"] == 0 or 
        pins[FlidSTATUS]["value"] == 1 or pins[RlidSTATUS]["value"] == 1 or 
        pins[BlackButtonPIN]["value"] == 1):
        
        # stop_machine()
        return -1
    else:
        return 0
        # pass
        

def start_machine():
   
    # Safety gate
    if (pins[SMPSMachineSTATUS]["value"] == 0 or pins[DoorsSTATUS]["value"] == 1 or 
        pins[PowerSTATUS]["value"] == 0 or pins[UpsInpSTATUS]["value"] == 0 or 
        pins[FlidSTATUS]["value"] == 1 or pins[RlidSTATUS]["value"] == 1 or 
        pins[BlackButtonPIN]["value"] == 1):
        print("[ARDUINO] Start Aborted: Safety Interlock Active")
        return
    
    print("[ARDUINO] Starting Machine Sequence...")
    
    pins[XrayPIN]["value"] = 1; pins[XraySTATUS]["value"] = 1
    time.sleep(0.5)   
    pins[CameraPIN]["value"] = 1; pins[CameraSTATUS]["value"] = 1
    time.sleep(0.5)
    pins[ConveyorPIN]["value"] = 1; pins[ConveyorSTATUS]["value"] = 1
    # time.sleep(0.5)

    
    # pins[RejectionConPIN]["value"] = 1; pins[RejectionConSTATUS]["value"] = 1
    # print("[ARDUINO] Machine fully operational.")

def stop_machine():   
    print("[ARDUINO] Stopping Machine...")
    pins[FeederPIN]["value"] = 0; pins[FeederSTATUS]["value"] = 0
    time.sleep(0.5)
    pins[CameraPIN]["value"] = 0; pins[CameraSTATUS]["value"] = 0
    time.sleep(0.5)
    pins[RejectionConPIN]["value"] = 0; pins[RejectionConSTATUS]["value"] = 0
    time.sleep(0.5)
    pins[XrayPIN]["value"] = 0; pins[XraySTATUS]["value"] = 0
    time.sleep(0.5)
    pins[ConveyorPIN]["value"] = 0; pins[ConveyorSTATUS]["value"] = 0
    # print("[ARDUINO] Machine Safely Stopped.")

def process_command(cmd):
    cmd = cmd.strip()
    if not cmd: return

    print(f"\n[RECEIVED CMD]: {cmd}")
    parts = cmd.split()

    if cmd == "StartMachine":
        # threading.Thread(target=start_machine, daemon=True).start()
        start_machine()
    elif cmd == "StopMachine":
        # threading.Thread(target=stop_machine, daemon=True).start()
        stop_machine()
    elif cmd == "AlignMode":
        pins[RejectionConPIN]["value"] = 0; pins[RejectionConSTATUS]["value"] = 0
    elif cmd == "ResumeNormalMode":
        pins[RejectionConPIN]["value"] = 1; pins[RejectionConSTATUS]["value"] = 1
    elif cmd == "StartFeeder":
        pins[FeederPIN]["value"] = 1; pins[FeederSTATUS]["value"] = 1
    elif cmd == "StopFeeder":
        pins[FeederPIN]["value"] = 0; pins[FeederSTATUS]["value"] = 0
    elif parts[0] == "setPin" and len(parts) == 3:
        try:
            p, v = int(parts[1]), int(parts[2])
            pins[p]["value"] = v
            safety_check()
        except: pass

# --- CONTINUOUS STATUS THREAD FOR ARDUINO ---
def status_thread():
    while True:
        # if not stop_polling.is_set():
            is_ok = safety_check()
            if is_ok == -1:
                print("is_ok:",is_ok)
                break
            
                      
            # Construct the status bitstring
            current_bits = "".join(str(pins[p]["value"]) for p in STATUS_PIN_MAP)
            
            print(f"\r[LIVE BITS]: {current_bits} | Monitoring COM6...", end="", flush=True)
            
            # Check for incoming commands (like "getStatus" from the Bridge)
            if ser.in_waiting > 0:
                try:
                    raw_data = ser.readline().decode().strip()
                    
                    # If bridge asks for status, send it back immediately
                    if raw_data == "getStatus":
                        send_to_com(f"BITS:{current_bits}")
                    else:
                        process_command(raw_data)
                except:
                    pass
            
        
            time.sleep(1) # Faster polling for better responsiveness
# --- MAIN RUNTIME ---
if __name__ == "__main__":
    print(f"--- Virtual Arduino Mega Active on {PORT} ---")
    status_thread()
    
    # Start the hardware simulation thread
    # t = threading.Thread(target=status_thread, daemon=True)
    # t.start()

    # try:
    #     while True:
    #         # Keeps the main process alive for the thread
    #         time.sleep(1)
    # except KeyboardInterrupt:
    ser.close()
    print("\nSimulator Offline.")