import sys, os, sqlite3, shutil, time
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QPushButton, QLabel, 
                             QFrame, QPlainTextEdit, QLineEdit, QFileDialog, QMenu)
from PyQt6.QtCore import Qt, QTimer, QProcess
from PyQt6.QtGui import QAction

class ModularTestingBench(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CONRAD-M | MODULAR TESTING BENCH v5.0")
        self.setFixedSize(1280, 720)
        
        # Setup paths for the Windows App Package environment
        local_app_data = os.environ.get('LOCALAPPDATA', '')
        package_folder = "1b93a6a9-009e-4781-8c7b-31643d1c1f3b_zzsj02r91hwve"
        self.db_path = os.path.join(local_app_data, "Packages", package_folder, "LocalState", "db.sqlite")
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Communication files for the bridge and local fault tracking
        self.cmd_file = os.path.join(local_app_data, "Packages", package_folder, "LocalState", "mega_cmd.txt")
        self.state_file = os.path.join(self.base_dir, "fault_state.txt")
        
        self.source_dir = os.path.join(self.base_dir, "Source_Images")
        self.dest_dir = os.path.join(local_app_data, "Packages", package_folder, "LocalState", "Cropped")
        self.index = 0
        # Initializing core state variables
        self.phase = "READY"
        self.is_sim_active = False
        self.ses_id = 0        
        self.good, self.bad, self.forced_good = 0, 0, 0
        # self.copied_files = []
        self.active_processes = []
        self.terminals = {}

        # Mapping bridge scripts to their UI terminal boxes
        self.process_map = {
            "mega_bridge.py": "mega_bridge", "test_Mega.py": "mega_serial",
            "xray_bridge.py": "xray_bridge", "test_Xray.py": "xray_serial",
            "uno_bridge.py": "uno_bridge",   "test_Uno.py": "uno_serial"
        }

        self.init_ui()

        # Engine for database heartbeat and state transitions
        self.logic_engine = QTimer()
        self.logic_engine.timeout.connect(self.run_logic_cycle)
        self.logic_engine.start(1000)

        # Engine for simulating image arrival (IO stream)
        self.stream_engine = QTimer()
        self.stream_engine.timeout.connect(self.run_stream_cycle)

    def apply_styles(self):
        # Dark theme styling for industrial look
        self.setStyleSheet("""
            QMainWindow { background-color: #020617; }
            #ControlRack { background-color: #0f172a; border-right: 2px solid #1e293b; padding: 20px; }
            #DataRack { background-color: #020617; padding: 20px; }
            QLabel { color: #94a3b8; font-family: 'Consolas'; font-size: 11px; }
            QLabel#Value { color: #22d3ee; font-size: 28px; font-weight: bold; }
            QPushButton { background-color: #1e293b; color: #f8fafc; border: 1px solid #334155; border-radius: 4px; padding: 10px; font-weight: bold; }
            QPushButton#StartBtn { background-color: #10b981; color: #020617; border-radius: 8px; font-size: 14px; font-weight: 900; }
            QPushButton#Fault { background-color: #450a0a; color: #fca5a5; border: 1px solid #ef4444; }
            QPlainTextEdit { background-color: #020617; color: #38bdf8; border: 1px solid #1e293b; font-family: 'Consolas'; font-size: 10px; }
            QLineEdit { background-color: #0f172a; border: 1px solid #1e293b; color: #94a3b8; font-size: 10px; padding: 8px; }
        """)

    def init_ui(self):
        # UI layout initialization
        self.apply_styles()
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left panel: System controls
        rack = QFrame(); rack.setObjectName("ControlRack"); rack.setFixedWidth(400)
        rack_lay = QVBoxLayout(rack)
        
        rack_lay.addWidget(QLabel("SYSTEM PHASE"))
        self.lbl_phase = QLabel("OFFLINE"); self.lbl_phase.setObjectName("Value")
        rack_lay.addWidget(self.lbl_phase)
        
        rack_lay.addSpacing(20)
        self.test_btn = QPushButton("START TESTING"); self.test_btn.setObjectName("StartBtn")
        self.test_btn.setFixedHeight(70); self.test_btn.clicked.connect(self.toggle_testing)
        rack_lay.addWidget(self.test_btn)

        self.clear_btn = QPushButton("CLEAR LOGS"); self.clear_btn.clicked.connect(self.clear_all_logs)
        rack_lay.addWidget(self.clear_btn)

        rack_lay.addStretch()

        # Path management UI
        rack_lay.addWidget(QLabel("SOURCE FOLDER"))
        self.src_in = QLineEdit(self.source_dir); self.src_in.setReadOnly(True)
        rack_lay.addWidget(self.src_in)
        btn_path = QPushButton("BROWSE SOURCE "); btn_path.clicked.connect(self.select_source_path)
        rack_lay.addWidget(btn_path)

        rack_lay.addSpacing(20) 
        rack_lay.addWidget(QLabel("DESTINATION  FOLDER"))
        self.dest_in = QLineEdit(self.dest_dir); self.dest_in.setReadOnly(True)
        rack_lay.addWidget(self.dest_in)
        btn_path = QPushButton("BROWSE DESTINATION "); btn_path.clicked.connect(self.select_dest_path)
        rack_lay.addWidget(btn_path)

        rack_lay.addSpacing(20) 
        btn_fault = QPushButton("INJECT SYSTEM FAULT"); btn_fault.setObjectName("Fault")
        btn_fault.setMenu(self.create_fault_menu())
        rack_lay.addWidget(btn_fault)

        # Right panel: Real-time terminal data
        data_rack = QFrame(); data_rack.setObjectName("DataRack")
        data_lay = QVBoxLayout(data_rack)
        
        grid = QGridLayout()
        nodes = [("MEGA", "mega"), ("X-RAY", "xray"), ("UNO", "uno")]
        for row, (name, key) in enumerate(nodes):
            for col, n_type in enumerate(["BRIDGE", "SERIAL"]):
                v = QVBoxLayout(); v.addWidget(QLabel(f"{name} :: {n_type}"))
                t = QPlainTextEdit(); t.setReadOnly(True)
                self.terminals[f"{key}_{n_type.lower()}"] = t
                v.addWidget(t); grid.addLayout(v, row, col)
        
        data_lay.addLayout(grid, 7)
        data_lay.addWidget(QLabel("SYSTEM EVENT STREAM"))
        self.master_log = QPlainTextEdit(); self.master_log.setFixedHeight(180)
        data_lay.addWidget(self.master_log, 3)

        main_layout.addWidget(rack); main_layout.addWidget(data_rack)

    def toggle_testing(self):
        # Switching between testing and standby modes
        if self.test_btn.text() == "START TESTING":
            self.is_sim_active = True
            self.phase = "READY"
            
            # Resetting DB to clean start state
            self.db_execute("""
                UPDATE control SET 
                status='Welcome', dialog=0, state=0, mains=1, 
                door=0, flid=0, blid=0, warning=0, calib=0, feeder=0 WHERE id=1
            """)
            
            # Wipe existing fault file if it exists to prevent old bugs from carrying over
            if os.path.exists(self.state_file):
                os.remove(self.state_file)

            self.test_btn.setText("STOP TESTING")
            self.test_btn.setStyleSheet("background-color: #ef4444; color: white; border-radius: 8px; font-weight: 900;")
            
            # Kicking off the main communication bridge
            self.start_scripts(["mega_bridge.py", "test_Mega.py"])
            self.log("Testing Initiated: Mega Node Online.")
        else:
            self.stop_all_testing()

    def run_logic_cycle(self):
        # This handles the internal state machine and HMI interaction
        if not self.is_sim_active: return

        row = self.db_execute("SELECT dialog, state FROM control WHERE id=1", fetch=True)
        if not row: return
        dialog, state  = row

        # Waiting for the user to confirm the HMI setup dialog
        if self.phase == "READY" and dialog == 1:
            self.phase = "DIALOG"
            self.log("HMI Prompt: Summary Dialog Active.")
        
        # Once HMI starts running, we find the latest session ID and start simulation
        elif self.phase == "DIALOG" and state == 1:
            self.phase = "RUNNING"
            res_ses = self.db_execute("SELECT MAX(ses) FROM machineStatus", fetch=True)
            self.ses_id = res_ses[0] if (res_ses and res_ses[0] is not None) else 1
            # self.copied_files = []
            self.index = 0
            self.good, self.bad, self.forced_good = 0, 0, 0
            self.db_execute("UPDATE control SET pls_wait=1, dialog=0 WHERE id=1")
            self.stream_engine.start(400)
            self.log(f"Session {self.ses_id} Activated.")

        # Reverting to ready if the machine stops
        elif self.phase == "RUNNING":
            if state == 0:
                self.phase = "READY"
                self.stream_engine.stop()
                self.db_execute("UPDATE control SET status='Welcome', mains=1")
                self.log("Session Terminated by User.")
            
        self.lbl_phase.setText(self.phase)
        
        # Updating the heartbeat so the main app knows this bench is alive
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.db_execute("UPDATE control SET main_hb=? WHERE id=1", (ts,))    

    def run_stream_cycle(self):
        # Simulates image processing by copying files from source to destination
        try:
            # files = [f for f in os.listdir(self.source_dir) if f not in self.copied_files]
            filename = f"CH0_M2_file_{str(self.index)}"
            if os.path.exists(os.path.join(self.source_dir, filename + ".txt")):
                shutil.copy(os.path.join(self.source_dir, filename + ".txt"), os.path.join(self.dest_dir, filename + ".txt"))
                time.sleep(0.001)
                if os.path.exists(os.path.join(self.source_dir, filename + ".tif")):
                    shutil.copy(os.path.join(self.source_dir, filename + ".tif"), os.path.join(self.dest_dir, filename + ".tif"))
                    self.log(f"Simulated IO: {filename+ ".tif"} transferred.")
                    self.index += 1

            # if files:
            #     f = files[0]
            #     shutil.copy(os.path.join(self.source_dir, f), os.path.join(self.dest_dir, f))
            #     self.copied_files.append(f) 
            
        except Exception as e:
            self.log(f"Stream Error: {e}")
            self.stop_all_testing()

    def start_scripts(self, script_list):
        # Launches external bridge/serial simulator scripts as subprocesses
        for script in script_list:
            proc = QProcess(self)
            proc.setProperty("script", script)
            proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
            proc.readyReadStandardOutput.connect(lambda p=proc, s=script: self.handle_output(p, s))
            proc.finished.connect(lambda: self.safe_remove_process(proc))
            proc.start(sys.executable, ["-u", script])
            self.active_processes.append(proc)

    def safe_remove_process(self, proc):
        # Clean up tracking list when a script exits
        if proc in self.active_processes:
            self.active_processes.remove(proc)

    def handle_output(self, proc, script):
        # Main data handler for information coming back from bridges
        data = proc.readAllStandardOutput().data().decode().strip()
        if not data: return
        
        if script in self.process_map:
            self.terminals[self.process_map[script]].appendPlainText(data)

        # Emergency stop if Mega reports an offline state
        if script == "test_Mega.py":
            if "offline" in data.lower():
                self.stop_all_testing()
                return

        # Parsing the binary data from Mega serial (Conveyor, X-Ray, etc.)
        if script == "test_Mega.py" and "[LIVE BITS]:" in data:
            try:
                running_scripts = [p.property("script") for p in self.active_processes]
                bits = data.split(":")[1].strip()
                self.update_devices_from_bits(bits)
                
                res = self.db_execute("SELECT state, feeder, sensitivity FROM control WHERE id=1", fetch=True)
                if res and res[0] == 1:
                    # Dynamically start/stop X-Ray simulator based on xray bit
                    if len(bits) > 2 and bits[2] == "1":
                        if "xray_bridge.py" not in running_scripts:
                            self.db_execute("UPDATE control SET xray=1 WHERE id=1")
                            self.start_scripts(["xray_bridge.py", "test_Xray.py"])
                    else:
                        self.kill_script("xray_bridge.py"); self.kill_script("test_Xray.py")
                    
                    # Logic for the Uno node (Rejecter/Sensor)        
                    if res[1] == 1:
                        self.db_execute("UPDATE machineStatus SET feeder='ON' WHERE ses=?", (self.ses_id,))
                        if len(bits) > 4 and bits[4] == "1" and "uno_bridge.py" not in running_scripts:
                            self.start_scripts(["uno_bridge.py", "test_Uno.py"])
                    else:
                        self.db_execute("UPDATE machineStatus SET feeder='OFF' WHERE ses=?", (self.ses_id,))
                        if len(bits) > 4 and bits[4] == "0":
                            self.kill_script("uno_bridge.py"); self.kill_script("test_Uno.py")
                else:
                    # Cleanup if system is not in a running state
                    self.db_execute("UPDATE machineStatus SET x_ray='OFF', camera='OFF', conveyor='OFF', feeder='OFF' WHERE ses=?", (self.ses_id,))
                    self.db_execute("UPDATE control SET temperature=0, xray=0 WHERE id=1")                   
                    self.kill_script("xray_bridge.py")
                    self.kill_script("test_Xray.py")
                    self.kill_script("uno_bridge.py")
                    self.kill_script("test_Uno.py")
            except: 
                pass

        # Parsing radiation data from X-Ray simulator
        if script == "test_Xray.py" and "[DATA OUT]:" in data:
            try:
                parts = data.split("]:")[1].strip().split()
                if len(parts) >= 2:
                    kv_val = int(parts[0]) / 10
                    ma_val = int(parts[1]) / 1000
                    temp_val = parts[2] if len(parts) > 2 else 20
                    self.db_execute("UPDATE control SET temperature=? WHERE id=1", (str(temp_val),))
                    xray_display = f"ON | {kv_val}kV {ma_val}mA"                    
                    self.db_execute("UPDATE machineStatus SET x_ray=? WHERE ses=?", (xray_display, self.ses_id))
            except: pass

        # Counting good/bad items based on Uno bridge output
        if script == "uno_bridge.py" and "[BRIDGE]:" in data:
            try:
                parts = data.split(":")
                hex_str = parts[1].strip().split()[0]
                hex_val = int(hex_str, 16)
                res = self.db_execute("SELECT state, feeder, sensitivity FROM control WHERE id=1", fetch=True)
                if hex_val == 0xA1: self.good += 1 
                elif hex_val == 0xB1 and res and res[2] == 0: self.bad += 1 
                elif hex_val == 0xF1 and res and res[2] == 0: self.forced_good += 1 
                total = self.good + self.bad + self.forced_good
                self.db_execute("UPDATE machineStatus SET good=?, bad=?, forced_good=?, total=? WHERE ses=?",
                    (self.good, self.bad, self.forced_good, total, self.ses_id))
            except: pass

    def update_devices_from_bits(self, bits):
        # Maps binary sensor data to visual status strings in the DB
        if len(bits) >= 6:
            x_status = "ON" if bits[2] == "1" else "OFF"
            c_status = "ON" if bits[1] == "1" else "OFF"
            v_status = "ON" if bits[3] == "1" else "OFF"
            res = self.db_execute("SELECT x_ray FROM machineStatus WHERE ses=?", (self.ses_id,), fetch=True)
            if res and res[0] and "ON |" in str(res[0]) and x_status == "ON": x_status = res[0]
            self.db_execute("UPDATE machineStatus SET x_ray=?, camera=?, conveyor=? WHERE ses=?",
                (x_status, c_status, v_status, self.ses_id))
            row = self.db_execute("SELECT feeder FROM control WHERE id=1", fetch=True)
            if row and row[0] == 1: self.db_execute("UPDATE control SET feeder=1 WHERE id=1")
                
    def stop_all_testing(self):
        # Shutdown sequence for the bench
        self.is_sim_active = False
        
        # Check if we have any active faults stored in our text file
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    for line in f:
                        if ":" in line:
                            col, val = line.strip().split(":")
                            # Force the DB to keep the fault state even after halt
                            self.db_execute(f"UPDATE control SET {col}=? WHERE id=1", (val,))
                
                # Trash the file so we don't double-read it next time
                os.remove(self.state_file)
            except Exception as e:
                self.log(f"Error handling state file: {e}")

        self.db_execute("UPDATE control SET temperature=0, xray=0 WHERE id=1")
        self.db_execute("UPDATE machineStatus SET x_ray='OFF', camera='OFF', conveyor='OFF', feeder='OFF' WHERE ses=?", (self.ses_id,))

        if os.path.exists(self.source_dir):
            try:
                for f in os.listdir(self.source_dir):
                    f_path = os.path.join(self.source_dir, f)
                    # Only delete if it's a file, not a subdirectory
                    if os.path.isfile(f_path): 
                        os.remove(f_path)
                self.log("Source directory cleared.")
            except Exception as e:
                self.log(f"Error clearing source: {e}")
        
        # Kill all running bridges
        for p in self.active_processes: p.kill()
        self.active_processes = []
        
        # UI cleanup
        self.test_btn.setText("START TESTING")
        self.test_btn.setStyleSheet("background-color: #10b981; color: #020617; border-radius: 8px; font-weight: 900;")
        self.lbl_phase.setText("OFFLINE")
        self.log("Testing Halted: System Powered Off") 

    def create_fault_menu(self):
        # Menu for choosing which hardware fault to simulate
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #1e293b; color: #f1f5f9; border: 1px solid #ef4444; }")
        faults = [
            ("Mains Fail", 49, 0, "mains", "Mains Power Failure"),
            ("Door Open", 34, 1, "door" , "Main Door Open"),
            ("Front Lid Open", 37, 1, "blid", "Front Lid Open"),
            ("Rejection Lid Open", 35, 1, "flid", "Rejection Lid Open")
        ]
        for label, pin, val, col, msg in faults:
            action = QAction(label, self)
            action.triggered.connect(lambda chk, p=pin, v=val, c=col, m=msg: self.set_fault(p, v, c, m))
            menu.addAction(action)
        return menu
    
    def set_fault(self, pin, value, column, message):
        # Injects a fault by writing to bridge cmd and saving it to our text file for persistence
        try:
            with open(self.cmd_file, "w") as f:
                f.write(f"setPin {pin} {value}")
            
            # Read existing faults into a dict so we can update without overwriting other active faults
            state_data = {}
            if os.path.exists(self.state_file):
                with open(self.state_file, "r") as f:
                    for line in f:
                        if ":" in line:
                            k, v = line.strip().split(":")
                            state_data[k] = v
            
            # Update the specific column and save back to text file
            state_data[column] = str(value)
            with open(self.state_file, "w") as f:
                for k, v in state_data.items(): f.write(f"{k}:{v}\n")

            self.terminals["mega_bridge"].appendPlainText(f"\n[!!!] CRITICAL FAULT: {message}")
        except: pass

    def clear_all_logs(self):
        for t in self.terminals.values(): t.clear()
        self.master_log.clear()

    def kill_script(self, name):
        # Safely stops a specific named bridge
        for p in self.active_processes[:]:
            if p.property("script") == name:
                p.kill(); self.active_processes.remove(p)

    def log(self, m): self.master_log.appendPlainText(f"[{datetime.now().strftime('%H:%M:%S')}] {m}")

    def select_source_path(self):
    # Opens dialog to pick the parent folder
        p = QFileDialog.getExistingDirectory(self, "Select Root", self.base_dir)
        if p: 
            self.source_dir = os.path.join(p, "Source_Images")
            
            # Physically create the folder if it doesn't exist yet
            if not os.path.exists(self.source_dir):
                os.makedirs(self.source_dir)
                
            self.src_in.setText(self.source_dir)

    def select_dest_path(self):
        # Opens dialog to pick the parent folder
        p = QFileDialog.getExistingDirectory(self, "Select Root", self.base_dir)
        if p: 
            self.dest_dir = os.path.join(p, "Cropped")
            
            # Physically create the folder if it doesn't exist yet
            if not os.path.exists(self.dest_dir):
                os.makedirs(self.dest_dir)
                
            self.dest_in.setText(self.dest_dir)

    def db_execute(self, query, params=(), fetch=False):
        try:
            with sqlite3.connect(self.db_path, timeout=30) as conn:
                conn.execute("PRAGMA journal_mode=WAL;")
                cursor = conn.execute(query, params)
                conn.commit()
                return cursor.fetchone() if fetch else None
        except: return None

if __name__ == "__main__":
    app = QApplication(sys.argv); window = ModularTestingBench(); window.show(); sys.exit(app.exec())
