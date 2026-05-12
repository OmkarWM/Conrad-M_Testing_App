import sys, os, sqlite3, shutil, time
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QPushButton, QLabel, 
                             QFrame, QPlainTextEdit, QMenu, QFileDialog, QLineEdit)
from PyQt6.QtCore import Qt, QProcess, QTimer 
from PyQt6.QtGui import QAction

class BackendHardwareTest(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Back-End-Testing GUI")
        self.setFixedSize(1400, 900)

        def get_db_path():
            config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "port_config.txt")
            if os.path.exists(config_file):
                try:
                    with open(config_file, "r") as f:
                        lines = f.read().splitlines()
                        if len(lines) >= 7 and lines[6].strip():
                            return lines[6].strip()
                except Exception:
                    pass
            return ""
                
        self.local_app_data = os.environ.get('LOCALAPPDATA', '')
        self.package_folder = "1b93a6a9-009e-4781-8c7b-31643d1c1f3b_zzsj02r91hwve"
        # self.db_path = os.path.join(self.local_app_data, "Packages", self.package_folder, "LocalState", "db.sqlite")
        self.db_path = get_db_path()
        self.cmd_file = os.path.join(self.local_app_data, "Packages", self.package_folder, "LocalState", "mega_cmd.txt")
        #default path
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.source_dir = os.path.join(self.base_dir)
        self.dest_dir = os.path.join(self.local_app_data, "Packages", self.package_folder, "LocalState")
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self.img_monitor_transfer)
        
        self.active_processes = []
        self.controls = {}
        self.terminals = {}
        self.copied_files = []
        self.index = 0
 
        
        # Split mapping: Each script routes to its own specific terminal
        self.process_map = {
            "mega_bridge.py": "mega_bridge", "test_Mega.py": "mega_serial",
            "xray_bridge.py": "xray_bridge", "test_Xray.py": "xray_serial",
            "uno_bridge.py": "uno_bridge",   "test_Uno.py": "uno_serial"
        }
        
        self.init_ui()

    def db_execute(self, query, params=(), fetch=False):
        if not self.db_path: 
            return None
        try:
            with sqlite3.connect(self.db_path, timeout=20) as conn:
                conn.execute("PRAGMA journal_mode=WAL;")
                cursor = conn.execute(query, params)
                conn.commit()
                return cursor.fetchone() if fetch else None
        except Exception as e:
            print(f"DB Error: {e}")
            return None
        
    def select_folder(self, folder_type):
        
        new_path = QFileDialog.getExistingDirectory(self, "Select Location", self.base_dir)
        
        if new_path:
            if folder_type == "src":
                # Keeps "Source_Images" but changes the parent path
                self.source_dir = os.path.join(new_path)
                self.src_input.setText(self.source_dir)
            else:
                # Keeps "Saved_Images" but changes the parent path
                self.dest_dir = os.path.join(new_path)
                self.dst_input.setText(self.dest_dir)
                
            self.terminals["mega_bridge"].appendPlainText(f"[CONFIG] Path updated to new path: {new_path}")

    def init_ui(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #0f172a; }
            QLabel { color: #94a3b8; font-family: 'Segoe UI'; font-size: 11px; font-weight: 700; text-transform: uppercase; }
            QPlainTextEdit { 
                background-color: #020617; 
                color: #38bdf8; 
                border: 1px solid #1e293b; 
                border-radius: 4px; 
                font-family: 'Consolas'; 
                font-size: 10px;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # --- TERMINAL GRID (SPLIT INTO 6) ---
        grid_container = QWidget()
        grid = QGridLayout(grid_container)
        grid.setSpacing(10)

        systems = [("MEGA", "mega"), ("X-RAY", "xray"), ("UNO", "uno")]
        for row, (name, key) in enumerate(systems):
            # Bridge Terminal column
            v_bridge = QVBoxLayout()
            v_bridge.addWidget(QLabel(f"● {name} | BRIDGE"))
            t_bridge = QPlainTextEdit(); t_bridge.setReadOnly(True)
            self.terminals[f"{key}_bridge"] = t_bridge
            v_bridge.addWidget(t_bridge)
            grid.addLayout(v_bridge, row, 0)

            # Serial Terminal column
            v_serial = QVBoxLayout()
            v_serial.addWidget(QLabel(f"○ {name} | SERIAL"))
            t_serial = QPlainTextEdit(); t_serial.setReadOnly(True)
            self.terminals[f"{key}_serial"] = t_serial
            v_serial.addWidget(t_serial)
            grid.addLayout(v_serial, row, 1)

        main_layout.addWidget(grid_container, 7)

        # --- SIDEBAR ---
        sidebar_frame = QFrame()
        sidebar_frame.setStyleSheet("background-color: #1e293b; border-radius: 20px;")
        sidebar = QVBoxLayout(sidebar_frame)
        sidebar.setContentsMargins(15, 25, 15, 25)
        sidebar.setSpacing(15)

        title = QLabel("SYSTEM MASTER")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 16px; color: #f8fafc; letter-spacing: 2px;")
        sidebar.addWidget(title)

        self.test_btn = QPushButton("START TESTING")
        self.test_btn.setFixedHeight(80)
        self.test_btn.setStyleSheet("background-color: #10b981; color: #020617; border-radius: 15px; font-weight: 900;")
        self.test_btn.clicked.connect(self.toggle_testing)
        sidebar.addWidget(self.test_btn)

        self.clear_btn = QPushButton("CLEAR LOGS")
        self.clear_btn.setFixedHeight(40)
        self.clear_btn.setStyleSheet("background-color: #334155; color: #94a3b8; border-radius: 10px; font-weight: bold;")
        self.clear_btn.clicked.connect(self.clear_all_logs)
        sidebar.addWidget(self.clear_btn)

        sidebar.addStretch()

        for txt, col in [("START MACHINE", "state"), ("FEEDER ON", "feeder")]:
            btn = QPushButton(txt); btn.setFixedHeight(65)
            btn.setStyleSheet("background-color: #334155; color: #f8fafc; border-radius: 15px; font-weight: bold;")
            self.controls[col] = btn
            btn.clicked.connect(lambda chk, c=col, b=btn: self.safe_db_update(c, b))
            sidebar.addWidget(btn)

        sidebar.addStretch()

        # --- PATH CONFIGURATION PANEL ---
        path_panel = QFrame()
        path_panel.setStyleSheet("""
            QFrame { 
                background-color: #020617; 
                border: 1px solid #1e293b; 
                border-radius: 12px; 
            }
            QLabel { 
                color: #22d3ee; 
                font-size: 10px; 
                letter-spacing: 1px; 
                border: none;
                background: transparent;
            }
            QLineEdit {
                background-color: #020617;
                color: #f8fafc; 
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 8px; 
                font-family: 'Consolas';
                font-size: 11px; 
            }           
            QPushButton {
                background-color: #1e293b;
                color: #f8fafc;
                border-radius: 6px;
                font-size: 9px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #334155;
                border: 1px solid #22d3ee;
            }
        """)
        
        path_layout = QVBoxLayout(path_panel)
        path_layout.setSpacing(8)

        # Source Configuration
        path_layout.addWidget(QLabel("STORAGE SOURCE"))
        self.src_input = QLineEdit(self.source_dir)
        self.src_input.setReadOnly(True)
        path_layout.addWidget(self.src_input)
        
        src_btn = QPushButton("SELECT SOURCE")
        src_btn.setFixedHeight(28)
        src_btn.clicked.connect(lambda: self.select_folder("src"))
        path_layout.addWidget(src_btn)

        # Separator Line
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #1e293b;")
        path_layout.addWidget(line)

        # Destination Configuration
        path_layout.addWidget(QLabel("STORAGE DESTINATION"))
        self.dst_input = QLineEdit(self.dest_dir)
        self.dst_input.setReadOnly(True)
        path_layout.addWidget(self.dst_input)
        
        dst_btn = QPushButton("SELECT DESTINATION")
        dst_btn.setFixedHeight(28)
        dst_btn.clicked.connect(lambda: self.select_folder("dst"))
        path_layout.addWidget(dst_btn)

        sidebar.addWidget(path_panel)

        # reset_btn = QPushButton("RESET MACHINE")
        # reset_btn.setFixedHeight(50)
        # reset_btn.setStyleSheet("background: transparent; color: #22d3ee; border: 2px solid #22d3ee; border-radius: 12px; font-weight: bold;")
        # reset_btn.clicked.connect(self.manual_reset)
        # sidebar.addWidget(reset_btn)

        self.err_btn = QPushButton("TRIGGER FAULT")
        self.err_btn.setFixedHeight(50)
        self.err_btn.setStyleSheet("background-color: #450a0a; color: #fca5a5; border: 2px solid #ef4444; border-radius: 12px; font-weight: bold;")
        self.err_btn.setMenu(self.create_error_menu())
        sidebar.addWidget(self.err_btn)

        main_layout.addWidget(sidebar_frame, 3)

    def clear_all_logs(self):
        for t in self.terminals.values(): t.clear()

    def create_error_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #1e293b; color: #f1f5f9; border: 1px solid #ef4444; }")
        faults = [
            ("Mains Fail", 49, 0, "Mains Power Failure"),
            ("Door Open", 34, 1, "Main Door Open"),
            ("Front Lid Open", 37, 1, "Front Lid Open"),
            ("Rejection Lid Open", 35, 1, "Rejection Lid Open")
        ]
        for label, pin, val, msg in faults:
            action = QAction(label, self)
            action.triggered.connect(lambda chk, p=pin, v=val, m=msg: self.set_fault(p, v, m))
            menu.addAction(action)
        return menu

    def set_fault(self, pin, value, message):
        try:
            with open(self.cmd_file, "w") as f:
                f.write(f"setPin {pin} {value}")
            self.db_execute("UPDATE control SET state=0, feeder=0, xray=0 WHERE id=1")
            for s in ["xray_bridge.py", "test_Xray.py", "uno_bridge.py", "test_Uno.py"]:
                self.kill_script(s)
            self.reset_ui_buttons()
            self.terminals["mega_bridge"].appendPlainText(f"\n[!!!] CRITICAL FAULT: {message}")
            self.monitor_timer.stop()
        except Exception as e:
            print(f"Fault Error: {e}")

    # def manual_reset(self):
    #     try:
    #         commands = ["setPin 49 1", "setPin 34 0", "setPin 37 0", "setPin 35 0"]
    #         with open(self.cmd_file, "w") as f:
    #             f.write("\n".join(commands))
    #         self.terminals["mega_bridge"].appendPlainText("> [SYSTEM] Hardware reset successful.")
    #     except: pass

    def toggle_testing(self):
        if self.test_btn.text() == "START TESTING":
            self.test_btn.setText("STOP TESTING")
            self.test_btn.setStyleSheet("background-color: #ef4444; color: white; border-radius: 15px; font-weight: 900;")
            self.start_scripts(["mega_bridge.py", "test_Mega.py"])
        else:
            self.stop_all_testing()

    def handle_output(self, proc, script):
        data = proc.readAllStandardOutput().data().decode().strip()
        if not data: return
        
        if script in self.process_map:
            self.terminals[self.process_map[script]].appendPlainText(data)

        # --- MEGA LOGIC ---
        if script == "test_Mega.py" and "[LIVE BITS]:" in data:
            # self.img_monitor_transfer()
            try:
                res = self.db_execute("SELECT state, feeder FROM control WHERE id=1", fetch=True)
                if res and res[0] == 1:
                    bits = data.split(":")[1].strip()
                    if len(bits) > 5 and bits[5] == "1":
                        self.db_execute("UPDATE control SET xray=1 WHERE id=1")
                        self.start_scripts(["xray_bridge.py", "test_Xray.py"])
                    
                    if res[1] == 1:
                        self.start_scripts(["uno_bridge.py", "test_Uno.py"])
            except: pass

        # --- X-RAY DATA LOGIC  ---
        # if script == "test_Xray.py" and "[DATA OUT]:" in data:
        #     try:
                
        #         parts = data.split("]:")[1].strip().split()
                
        #         if len(parts) >= 2:
        #             kv_val = parts[0]  # "kv"
        #             ma_val = parts[1]  # "ma"
        #             temp_val = parts[2]

                    
        #             # Using str() ensures zeros stay if the DB column is TEXT
        #             self.db_execute(
        #                 "UPDATE energy SET kv=?, ma=? WHERE num_grade=1", 
        #                 (str(kv_val), str(ma_val))
        #             )
        #             self.db_execute(
        #                 "UPDATE control SET temperature=? WHERE id=1", 
        #                 (str(temp_val),) 
        #             )
                    
       
        #     except Exception as e:
        #         print(f"X-ray Parse Error: {e} | Data: {data}")

    def safe_db_update(self, column, button):
        
        if column == "state":
            # Get current state from DB
            res = self.db_execute("SELECT state FROM control WHERE id=1", fetch=True)
            current_v = res[0] if res else 0
            
            # If the user is trying to START 
            if current_v == 0:
                # Check the Mega Serial terminal for active fault bits
                # Based on  map: bit 0 (Mains), 6 (Door), 7 (FLid), 8 (RLid)
                mega_log = self.terminals["mega_serial"].toPlainText().splitlines()
                last_bits = ""
                
                # Find the most recent [LIVE BITS] line
                for line in reversed(mega_log):
                    if "[LIVE BITS]:" in line:
                        last_bits = line.split(":")[1].strip()
                        break
                
                if last_bits:
                    # Logic: If bit 0 is '0' (Power Fail) OR bit 6,7,8 is '1' (Open)
                    has_fault = (last_bits[0] == '0' or last_bits[6] == '1' or 
                                 last_bits[7] == '1' or last_bits[8] == '1')
                    
                    if has_fault:
                        self.terminals["mega_bridge"].appendPlainText("\n[!] START BLOCKED: Safety Interlock Active.")
                        return # EXIT HERE: Do not update database to state=1
                    
        res = self.db_execute(f"SELECT {column} FROM control WHERE id=1", fetch=True)
        new_v = 1 if (res[0] if res else 0) == 0 else 0
        self.db_execute(f"UPDATE control SET {column}=? WHERE id=1", (new_v,))
        
        if new_v == 1:
            color = "#eab308" if column == "state" else "#a855f7"
            button.setText("STOP MACHINE" if column == "state" else "FEEDER OFF")
            button.setStyleSheet(f"background-color:{color}; color:black; border-radius:15px; font-weight:bold;")
            
            if column == "state":
                for path in [self.source_dir, self.dest_dir]:
                    if not os.path.exists(path):
                        os.makedirs(path)
                # self.copied_files = []
                self.index = 0
                self.monitor_timer.start(400)
                # self.img_monitor_transfer()
        else:
            button.setText("START MACHINE" if column == "state" else "FEEDER ON")
            button.setStyleSheet("background-color:#334155; color:white; border-radius:15px; font-weight:bold;")
            self.monitor_timer.stop()
            if column == "feeder":
                self.kill_script("uno_bridge.py"); self.kill_script("test_Uno.py")
            if column == "state":
                self.db_execute("UPDATE control SET xray=0, feeder=0 WHERE id=1")
                for s in ["xray_bridge.py", "test_Xray.py", "uno_bridge.py", "test_Uno.py"]: self.kill_script(s)
                self.reset_ui_buttons()

    def img_monitor_transfer(self):

        try:
            filename = f"CH0_M2_file_{str(self.index)}"
            if os.path.exists(os.path.join(self.source_dir, filename + ".txt")):
                shutil.copy(os.path.join(self.source_dir, filename + ".txt"), os.path.join(self.dest_dir, filename + ".txt"))
                time.sleep(0.001)
                if os.path.exists(os.path.join(self.source_dir, filename + ".tif")):
                    shutil.copy(os.path.join(self.source_dir, filename + ".tif"), os.path.join(self.dest_dir, filename + ".tif"))
                    self.terminals["mega_bridge"].appendPlainText(f"[STORAGE] Copied: {filename + ".tif"}")
                    self.index += 1

                
        except Exception as e:
            print(f"Copy Error: {e}")
            self.stop_all_testing()

    def kill_script(self, name):
        for p in self.active_processes[:]:
            if p.property("script") == name:
                p.kill(); self.active_processes.remove(p)

    def start_scripts(self, script_list):
        running = [p.property("script") for p in self.active_processes]
        for script in script_list:
            if script not in running:
                proc = QProcess(self)
                proc.setProperty("script", script)
                proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
                proc.readyReadStandardOutput.connect(lambda p=proc, s=script: self.handle_output(p, s))
                proc.start(sys.executable, ["-u", script])
                self.active_processes.append(proc)

    def stop_all_testing(self):
        self.db_execute("UPDATE control SET state=0, feeder=0, xray=0 WHERE id=1")
        # self.manual_reset()\

        # if os.path.exists(self.source_dir):
        #     try:
        #         for f in os.listdir(self.source_dir):
        #             f_path = os.path.join(self.source_dir, f)
        #             # Only delete if it's a file, not a subdirectory
        #             if os.path.isfile(f_path): 
        #                 os.remove(f_path)
        #         self.terminals["mega_bridge"].appendPlainText("Source directory cleared.")
    
        #     except Exception as e:
        #         self.terminals["mega_bridge"].appendPlainText(f"Error clearing source: {e}")

        for p in self.active_processes: p.kill()
        self.active_processes = []
        self.test_btn.setText("START TESTING")
        self.test_btn.setStyleSheet("background-color: #10b981; color: #020617; border-radius: 15px; font-weight: 900;")
        self.reset_ui_buttons()

    def reset_ui_buttons(self):
        for k, btn in self.controls.items():
            btn.setText("START MACHINE" if k == "state" else "FEEDER ON")
            btn.setStyleSheet("background-color:#334155; color:white; border-radius:15px; font-weight:bold;")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BackendHardwareTest()
    window.show()
    sys.exit(app.exec())