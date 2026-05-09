import sys
import os
import subprocess
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, 
                             QVBoxLayout, QPushButton, QLabel, QFrame, QHBoxLayout, QComboBox, QGridLayout)
from PyQt6.QtCore import Qt

class MasterLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Industrial Test Console")
        self.setFixedSize(550, 480)
        
        # Path for the shared configuration file
        self.config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "port_config.txt")
        
        self.active_process = None
        self.is_any_module_running = False
        self.buttons = []
        self.selectors = {} 

        self.apply_styles()

        main_container = QWidget()
        self.setCentralWidget(main_container)
        layout = QVBoxLayout(main_container)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.tabs.addTab(self.create_tab("Front-End", "Test_Case-Sim.py"), "Front-End")
        self.tabs.addTab(self.create_tab("Back-End", "combined_backend.py"), "Back-End")
        self.tabs.addTab(self.create_tab("End-to-End", "E2E_testing.py"), "End-2-End")

        config_box = QFrame()
        config_box.setStyleSheet("background-color: #161616; border-top: 1px solid #333; border-radius: 8px;")
        config_grid = QGridLayout(config_box)
        
        nodes = [("MEGA", "m"), ("X-RAY", "x"), ("UNO", "u")]
        default_ports = [f"COM{i}" for i in range(1, 15)]

        config_grid.addWidget(QLabel("HARDWARE "), 0, 0)      
        config_grid.addWidget(QLabel("SERIAL PORT"), 0, 1)
        config_grid.addWidget(QLabel("BRIDGE PORT"), 0, 2)

        for row, (name, key) in enumerate(nodes, 1):
            lbl = QLabel(name)
            lbl.setStyleSheet("color: #888; font-weight: bold; font-size: 9px;")
            config_grid.addWidget(lbl, row, 0)

            # Serial Port
            sr_combo = QComboBox()
            sr_combo.setEditable(True)
            sr_combo.addItems(default_ports)
            sr_combo.setCurrentIndex((row-1) * 2 + 5)
            sr_combo.setStyleSheet("background: #2d2d2d; color: #22d3ee; padding: 2px;")
            sr_combo.currentTextChanged.connect(self.save_ports_to_txt) # Auto-save on change
            self.selectors[f"{key}_sr"] = sr_combo
            config_grid.addWidget(sr_combo, row, 1)

            # Bridge Port
            br_combo = QComboBox()
            br_combo.setEditable(True) 
            br_combo.addItems(default_ports)
            br_combo.setCurrentIndex((row-1) * 2 + 6)
            br_combo.setStyleSheet("background: #2d2d2d; color: #fbbf24; padding: 2px;")
            br_combo.currentTextChanged.connect(self.save_ports_to_txt) # Auto-save on change
            self.selectors[f"{key}_br"] = br_combo
            config_grid.addWidget(br_combo, row, 2)

        layout.addWidget(config_box)
        self.save_ports_to_txt() # Initial save on startup

    def save_ports_to_txt(self):
        """Writes all 6 ports to a text file in a strict order."""
        try:
            port_data = [
                self.selectors["m_sr"].currentText(), # Line 0
                self.selectors["m_br"].currentText(), # Line 1
                self.selectors["x_sr"].currentText(), # Line 2
                self.selectors["x_br"].currentText(), # Line 3
                self.selectors["u_sr"].currentText(), # Line 4
                self.selectors["u_br"].currentText()  # Line 5
            ]
            with open(self.config_path, "w") as f:
                f.write("\n".join(port_data))
        except Exception as e:
            print(f"Error saving config: {e}")

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; }
            QTabWidget::pane { border: 1px solid #333; background: #252525; border-radius: 5px; }
            QTabBar::tab { background: #2d2d2d; color: #b1b1b1; padding: 8px 15px; }
            QTabBar::tab:selected { background: #3d3d3d; color: white; border-bottom: 2px solid #007acc; }
            QPushButton { background-color: #007acc; color: white; border-radius: 4px; font-weight: bold; border: none; }
            QComboBox { border: 1px solid #444; border-radius: 3px; font-family: 'Consolas'; font-size: 10px; }
            QLabel { color: #e0e0e0; font-family: 'Segoe UI'; font-size: 10px; text-transform: uppercase; }
            QFrame#StatusBox { background-color: #161616; border: 1px solid #333; border-radius: 8px; }
        """)

    def create_tab(self, title, script_name):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        status_box = QFrame(); status_box.setObjectName("StatusBox"); status_box.setFixedHeight(60)
        status_lay = QHBoxLayout(status_box)
        dot = QLabel("●"); dot.setStyleSheet("color: #333; font-size: 18px;") 
        msg = QLabel("Ready to Launch"); msg.setStyleSheet("font-size: 12px; color: #aaa;")
        status_lay.addWidget(dot); status_lay.addWidget(msg); status_lay.addStretch()
        btn = QPushButton(f"RUN {title.upper()}"); btn.setFixedHeight(40)
        self.buttons.append(btn)
        btn.clicked.connect(lambda checked, n=script_name, m=msg, d=dot, b=btn: self.handle_module(n, m, d, b))
        layout.addWidget(status_box); layout.addWidget(btn)
        return tab

    def handle_module(self, name, msg_label, dot_label, current_btn):
        if self.is_any_module_running and current_btn.text().startswith("STOP"):
            if self.active_process: self.active_process.terminate()
            self.is_any_module_running = False
            self.reset_ui()
            return

        if not self.is_any_module_running:
            try:
                # Ensure the file is updated one last time before launch
                self.save_ports_to_txt()
                
                # Launch script without any arguments
                self.active_process = subprocess.Popen([sys.executable, name])
                self.is_any_module_running = True
                
                msg_label.setText(f"{name} is Running")
                msg_label.setStyleSheet("color: #00ff00; font-weight: bold;")
                dot_label.setStyleSheet("color: #00ff00;")
                current_btn.setText(f"STOP {current_btn.text().replace('RUN ', '')}")
                current_btn.setStyleSheet("background-color: #cc0000;")
                
                for b in self.buttons:
                    if b != current_btn: b.setEnabled(False)
            except:
                msg_label.setText("Launch Error")

    def reset_ui(self):
        for b in self.buttons:
            if b.text().startswith("STOP"): b.setText(b.text().replace("STOP ", "RUN "))
            b.setEnabled(True); b.setStyleSheet("")
        for label in self.tabs.currentWidget().findChildren(QLabel):
            if label.text() == "●": label.setStyleSheet("color: #333; font-size: 18px;")
            elif "Running" in label.text() or label.text() == "Ready to Launch":
                label.setText("Ready to Launch"); label.setStyleSheet("font-size: 12px; color: #aaa;")

if __name__ == "__main__":
    app = QApplication(sys.argv); win = MasterLauncher(); win.show(); sys.exit(app.exec())