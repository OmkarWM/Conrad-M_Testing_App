import serial
import time

# --- CONFIGURATION ---
PORT = 'COM10'  # Use a virtual pair (e.g., COM10 <-> COM11)
BAUD = 9600

class UnoSimulator:
    def __init__(self):
        try:
            self.ser = serial.Serial(PORT, BAUD, timeout=0.1)
            print(f"--- Uno Simulator Active on {PORT} ---")
        except Exception as e:
            print(f"Connection Error: {e}")
            exit()

        # Mapping hex codes to Pin number
        self.channel_map = {
            0xA1: 5, 0xB1: 4, 0xC1: 8, 0xD1: 6,
            0xE1: 10, 0xF1: 11, 0xF2: 12, 0xF3: 7, 0xF4: 13
        }

    def run(self):
        while True:
            if self.ser.in_waiting > 0:
                # Read 1 byte as hex
                incoming_byte = self.ser.read(1)[0]
                
                if incoming_byte in self.channel_map:
                    pin = self.channel_map[incoming_byte]
                    print(f"\n[UNO] Received 0x{incoming_byte:02X} -> Pulsing PIN {pin} HIGH")
                    time.sleep(0.01) # Simulate t_on
                    print(f"[UNO] PIN {pin} LOW")
                else:
                    print(f"\r[UNO] Unknown Byte: 0x{incoming_byte:02X}", end="")

if __name__ == "__main__":
    UnoSimulator().run()