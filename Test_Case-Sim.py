import sys
import sqlite3
import os
import random
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QPushButton, QLabel, QFrame)
from PyQt6.QtCore import QTimer, Qt

class TestCaseSimulator(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # local_app_data = os.environ.get('LOCALAPPDATA')
        # package_folder = "1b93a6a9-009e-4781-8c7b-31643d1c1f3b_zzsj02r91hwve"
        # self.db_path = os.path.join(local_app_data, "Packages", package_folder, "LocalState", "db.sqlite")
        def get_db_path():
            config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "port_config.txt")
            if os.path.exists(config_file):
                with open(config_file, "r") as f:
                    lines = f.read().splitlines()
                    if len(lines) >= 7:
                        return lines[6]
            return None

        self.db_path = get_db_path()
        print(f"Using database at: {self.db_path}")
        
        self.phase = "READY" 
        self.is_sim_active = False 
        self.ses_id = 0
        self.cur_kv = 70
        self.cur_ma = 1.0
        self.current_temp = 20
        self.startup_step = 0
        self.good, self.bad, self.forced_good = 0, 0, 0

        self.apply_dark_theme()
        self.init_ui()

        self.timer = QTimer()
        self.timer.timeout.connect(self.run_logic)
        self.timer.start(1000)

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #0f111a; }
            QMenuBar { background-color: #1a1c2c; color: #bfc2c7; border-bottom: 1px solid #2d2f3f; padding: 4px; }
            QMenuBar::item:selected { background-color: #2d2f3f; border-radius: 4px; }
            QMenuBar::item:disabled { color: #33364a; }
            QMenu { background-color: #1a1c2c; border: 1px solid #2d2f3f; color: #bfc2c7; }
            QMenu::item:selected { background-color: #3e4461; color: #ffffff; }
            QMenu::item:disabled { color: #4b4e6d; }
            #StatusCard { background-color: #1a1c2c; border: 1px solid #2d2f3f; border-radius: 12px; }
            QPushButton#PowerButton {
                background-color: #3e4461; color: #ffffff; border: none; border-radius: 8px;
                padding: 12px; font-weight: 600; font-size: 14px;
            }
            QPushButton#PowerButton:hover { background-color: #4e5579; }
        """)

    def update_ui(self, status, logic, color="green", bold_logic=False):      
        self.lbl_status.setText(status)
        self.lbl_logic.setText(logic)
        status_color = "#4ade80" if color == "green" else "#fb7185" if color == "red" else "#94a3b8"
        self.lbl_status.setStyleSheet(f"color: {status_color}; font-size: 18px; font-weight: bold; background: transparent;")
        logic_style = "color: #94a3b8; background: transparent;"
        if bold_logic: logic_style = "color: #fb7185; font-weight: bold; background: transparent;"
        self.lbl_logic.setStyleSheet(logic_style)

    def set_fault(self, column, value, display_name):
        self.db_execute(f"UPDATE control SET {column}=? WHERE id=1", (value,))
        self.update_ui("CRITICAL ERROR", f"Fault: {display_name}", color="red", bold_logic=True)

    def db_execute(self, query, params=(), fetch=False):
        try:
            with sqlite3.connect(self.db_path, timeout=20) as conn:
                conn.execute("PRAGMA journal_mode=WAL;")
                cursor = conn.execute(query, params)
                conn.commit()
                return cursor.fetchone() if fetch else None
        except Exception: return None

    def init_ui(self):
        self.setWindowTitle("System Control - Dark Edition")
        self.setFixedSize(450, 420)
        menubar = self.menuBar()    
              
        self.menu_phys = menubar.addMenu("Physical Sensors")
        self.menu_phys.addAction("Mains Fail").triggered.connect(lambda: self.set_fault("mains", 0, "Mains Power Failure"))
        self.menu_phys.addAction("Door Open").triggered.connect(lambda: self.set_fault("door", 1, "Main Door Open"))
        self.menu_phys.addAction("Rejection Lid Open").triggered.connect(lambda: self.set_fault("flid", 1, "Rejection Lid Open"))
        self.menu_phys.addAction("Feeder Lid Open").triggered.connect(lambda: self.set_fault("blid", 1, "Feeder Lid Open"))
        self.menu_phys.addAction("Belt Slip").triggered.connect(lambda: self.set_fault("warning", 1, "Belt Slip"))

        self.menu_sys = menubar.addMenu("System Errors")
        self.menu_sys.addAction("X-Ray Failure").triggered.connect(lambda: self.set_fault("warning", 2, "X-Ray Failure"))
        self.menu_sys.addAction("Camera Failure").triggered.connect(lambda: self.set_fault("warning", 3, "Camera Failure"))
        self.menu_sys.addAction("I/O Controller Fail").triggered.connect(lambda: self.set_fault("warning", 4, "I/O Controller Fail"))
        self.menu_sys.addAction("DRV Controller Fail").triggered.connect(lambda: self.set_fault("warning", 5, "DRV Controller Fail"))
        self.menu_sys.addAction("COM Ports Fail").triggered.connect(lambda: self.set_fault("warning", 6, "COM Ports Fail"))
        self.menu_sys.addAction("X-Ray kv error").triggered.connect(lambda: self.set_fault("warning", 7, "X-Ray kv error"))
        self.menu_sys.addAction("X-Ray ma error").triggered.connect(lambda: self.set_fault("warning", 8, "X-Ray ma error"))
        self.menu_sys.addAction("X-Ray Temp Error").triggered.connect(lambda: self.set_fault("warning", 9, "X-Ray Temp Error"))

        self.menu_thr = menubar.addMenu("Threads/Logic")
        self.menu_thr.addAction("Control Thread Stop").triggered.connect(lambda: self.set_fault("warning", 16, "Control Thread Stop"))
        self.menu_thr.addAction("Read Contractors Stop").triggered.connect(lambda: self.set_fault("warning", 17, "Read Contractors Stop"))
        self.menu_thr.addAction("Overall Monitor Stop").triggered.connect(lambda: self.set_fault("warning", 18, "Overall Monitor Stop"))
        self.menu_thr.addAction("System Overload").triggered.connect(lambda: self.set_fault("warning", 19, "System Overload"))
        self.menu_thr.addAction("Cropping Thread Exited").triggered.connect(lambda: self.set_fault("warning", 24, "Cropping Thread Exited"))
        self.menu_thr.addAction("C2C Below Threshold").triggered.connect(lambda: self.set_fault("warning", 25, "C2C Below Threshold"))
        self.menu_thr.addAction("C2C Exceeds Threshold").triggered.connect(lambda: self.set_fault("warning", 26, "C2C Exceeds Threshold"))

        self.menu_res = menubar.addMenu("Resources/Setup")
        self.menu_res.addAction("Calibration Limit").triggered.connect(lambda: self.set_fault("calib", 3, "Calibration Limit Exceeded"))
        self.menu_res.addAction("C-Drive Full").triggered.connect(lambda: self.set_fault("warning", 10, "C-Drive Full"))
        self.menu_res.addAction("S-Drive Full").triggered.connect(lambda: self.set_fault("warning", 11, "S-Drive Full"))
        self.menu_res.addAction("E-Drive Full").triggered.connect(lambda: self.set_fault("warning", 12, "E-Drive Full"))
        self.menu_res.addAction("30 Days Unused").triggered.connect(lambda: self.set_fault("warning", 13, "30 Days Unused"))
        self.menu_res.addAction("2 Hours Usage").triggered.connect(lambda: self.set_fault("warning", 14, "2 Hours Usage"))

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(24, 24, 24, 24)
        
        self.card = QFrame()
        self.card.setObjectName("StatusCard")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(20, 30, 20, 30)
        
        self.lbl_status = QLabel("SIMULATOR: OFF")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_logic = QLabel("Press Power ON to start")
        self.lbl_logic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        card_layout.addWidget(self.lbl_status)
        card_layout.addSpacing(10)
        card_layout.addWidget(self.lbl_logic)
        
        self.btn_power = QPushButton("Power ON Simulator")
        self.btn_power.setObjectName("PowerButton")
        self.btn_power.clicked.connect(self.toggle_power)
        
        main_layout.addWidget(self.card)
        main_layout.addStretch()
        main_layout.addWidget(self.btn_power)
        self.update_ui("SIMULATOR: OFF", "Press Power ON to start", color="gray")

    def toggle_power(self):
        if not self.is_sim_active:
            self.is_sim_active = True
            self.phase = "READY"
            self.btn_power.setText("Power OFF Simulator")
            self.btn_power.setStyleSheet("background-color: #e63946;")
            self.db_execute("UPDATE control SET status='Welcome', dialog=0, state=0, pls_wait=0, mains=1, door=0, flid=0, blid=0, warning=0, calib=0, feeder=0")
            self.update_ui("SIMULATOR: ON", "SIMULATOR ACTIVE: Running...")
        else:
            self.is_sim_active = False
            self.btn_power.setText("Power ON Simulator")
            self.btn_power.setStyleSheet("")
            self.update_ui("SIMULATOR: OFF", "Press Power ON to start", color="gray")

    def run_logic(self):
        s_active = self.is_sim_active
        is_running = (self.phase == "RUNNING")

        # Start of Original Enabling/Disabling Logic
        for menu in [self.menu_phys, self.menu_sys, self.menu_thr, self.menu_res]:
            menu.setEnabled(s_active)

        if not s_active: return

        for action in self.menu_res.actions():
            if "Calibration" in action.text():
                action.setEnabled(not is_running)
            else:
                action.setEnabled(is_running)

        for m in [self.menu_phys, self.menu_sys, self.menu_thr]:
            m.setEnabled(is_running)
        # End of Original Enabling/Disabling Logic

        row = self.db_execute("SELECT dialog, state, feeder, sensitivity FROM control WHERE id=1", fetch=True)
        if not row: return
        dialog, state, feeder_signal, sensitivity = row

        is_running = (self.phase == "RUNNING")

        self.cur_kv = max(70.0, min(130.0, self.cur_kv + random.choice([-5, 5])))
        self.cur_ma = max(1.0, min(2.5, self.cur_ma + random.choice([-0.2, 0.2])))
        xray_display = f"ON | {int(self.cur_kv)}kV {round(self.cur_ma, 1)}mA" 
        self.current_temp = max(20, min(100, self.current_temp + random.choice([5,-5])))

        if is_running:
            if self.startup_step < 3:
                self.startup_step += 1
                if self.startup_step == 1: self.db_execute("UPDATE machineStatus SET x_ray='ON' WHERE ses=?", (self.ses_id,))               
                elif self.startup_step == 2: self.db_execute("UPDATE machineStatus SET camera='ON' WHERE ses=?", (self.ses_id,))
                elif self.startup_step == 3: self.db_execute("UPDATE machineStatus SET conveyor='ON' WHERE ses=?", (self.ses_id,))
            self.db_execute("UPDATE control SET temperature=? WHERE id=1",(self.current_temp,))
            self.db_execute("UPDATE machineStatus SET x_ray=? WHERE ses=?", (xray_display,self.ses_id,))
            
            f_status = "ON" if feeder_signal == 1 else "OFF"
            self.db_execute("UPDATE machineStatus SET feeder=? WHERE ses=?", (f_status, self.ses_id))

            if f_status == "ON" and self.startup_step == 3:
                self.good += random.randint(0, 2)
                self.bad += random.randint(0,2) if random.random() > 0.5 and sensitivity == 0 else 0
                self.forced_good += random.randint(0,2) if random.random() > 0.8 and sensitivity == 0  else 0
                total = self.good + self.bad + self.forced_good
                self.db_execute("UPDATE machineStatus SET good=?, bad=?, forced_good=?, total=? WHERE ses=?", (self.good, self.bad, self.forced_good, total, self.ses_id))
        else:
            self.startup_step = 0

        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.db_execute("UPDATE control SET main_hb=? WHERE id=1", (ts,))

        if self.phase == "READY":
            if dialog == 1:
                self.phase = "DIALOG"
                self.update_ui("DIALOG ACTIVE", "SIMULATOR ACTIVE: Running...")
            else:
                self.update_ui("READY: Waiting for User to Press START", self.lbl_logic.text())

        elif self.phase == "DIALOG":           
            if state == 1:
                res_ses = self.db_execute("SELECT MAX(ses) FROM machineStatus", fetch=True)
                self.ses_id = res_ses[0] if (res_ses and res_ses[0] is not None) else 0
                self.good, self.bad, self.forced_good = 0, 0, 0
                self.cur_kv, self.cur_ma, self.current_temp = 70, 1.0, 20
                self.phase = "RUNNING"
                self.db_execute("UPDATE control SET pls_wait=1, dialog=0 WHERE id=1")
            elif dialog == 0:
                self.phase = "READY"
                self.db_execute("UPDATE control SET status='Welcome'")
                
        elif self.phase == "RUNNING":
            if state == 0:               
                self.phase = "READY"
                self.db_execute("UPDATE control SET status='Welcome',mains=1,temperature=0")
                self.db_execute("UPDATE machineStatus set x_ray='OFF'")
            else:
                self.db_execute("UPDATE control SET main_hb=? WHERE id=1", (ts,))
                self.lbl_status.setText(f"RUNNING: {ts}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestCaseSimulator()
    window.show()
    sys.exit(app.exec())