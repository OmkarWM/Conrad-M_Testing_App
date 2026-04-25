import sys
import subprocess
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, 
                             QVBoxLayout, QPushButton, QLabel, QFrame, QHBoxLayout)
from PyQt6.QtCore import Qt

class MasterLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Industrial Test Console")
        self.setFixedSize(380, 280)
        
        # GLOBAL LOCK: Tracks if any module is currently active
        self.active_process = None
        self.is_any_module_running = False

        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; }
            QTabWidget::pane { border: 1px solid #333; top: -1px; background: #252525; border-radius: 5px; }
            QTabBar::tab { background: #2d2d2d; color: #b1b1b1; padding: 8px 20px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background: #3d3d3d; color: white; border-bottom: 2px solid #007acc; }
            QPushButton { background-color: #007acc; color: white; border-radius: 4px; font-weight: bold; border: none; }
            QPushButton:hover { background-color: #0098ff; }
            QPushButton:disabled { background-color: #444; color: #888; }
            QLabel { color: #e0e0e0; }
            QFrame#StatusBox { background-color: #161616; border: 1px solid #333; border-radius: 8px; }
        """)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Storage for all buttons so we can disable them globally
        self.buttons = []

        self.tabs.addTab(self.create_tab("Front-End", "Test_Case-Sim.py"), "Front-End")
        self.tabs.addTab(self.create_tab("Back-End", "combined_backend.py"), "Back-End")
        self.tabs.addTab(self.create_tab("End-to-End", "original_sim.py"), "End-2-End")

    def create_tab(self, title, script_name):
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        lbl_title = QLabel(title.upper())
        lbl_title.setStyleSheet("letter-spacing: 2px; color: #888; font-size: 10px; font-weight: bold;")
        
        status_box = QFrame()
        status_box.setObjectName("StatusBox")
        status_box.setFixedHeight(80)
        status_layout = QHBoxLayout(status_box)
        
        dot = QLabel("●")
        dot.setStyleSheet("color: #333; font-size: 18px;") 
        
        msg = QLabel("Ready to Launch")
        msg.setStyleSheet("font-size: 13px; color: #aaa;")
        
        status_layout.addSpacing(10)
        status_layout.addWidget(dot)
        status_layout.addWidget(msg)
        status_layout.addStretch()

        btn = QPushButton(f"RUN {title.upper()}")
        btn.setFixedHeight(45)
        self.buttons.append(btn)
        
        # Link the button to the launch logic
        btn.clicked.connect(lambda checked, n=script_name, m=msg, d=dot, b=btn: self.handle_module(n, m, d, b))

        layout.addWidget(lbl_title)
        layout.addWidget(status_box)
        layout.addSpacing(10)
        layout.addWidget(btn)
        tab.setLayout(layout)
        return tab

    def handle_module(self, name, msg_label, dot_label, current_btn):
        # Case 1: If a module is already running, this button becomes a "STOP" button
        if self.is_any_module_running and current_btn.text().startswith("STOP"):
            if self.active_process:
                self.active_process.terminate()
                self.active_process = None
            
            self.is_any_module_running = False
            self.reset_ui()
            return

        # Case 2: Try to launch a new module
        if not self.is_any_module_running:
            try:
                self.active_process = subprocess.Popen([sys.executable, name])
                self.is_any_module_running = True
                
                # Update UI for the running module
                msg_label.setText(f"{name} is Running")
                msg_label.setStyleSheet("color: #00ff00; font-weight: bold;")
                dot_label.setStyleSheet("color: #00ff00; ")
                
                # Change THIS button to a Stop button
                current_btn.setText(f"STOP {current_btn.text().replace('RUN ', '')}")
                current_btn.setStyleSheet("background-color: #cc0000;")
                
                # Disable all OTHER buttons
                for b in self.buttons:
                    if b != current_btn:
                        b.setEnabled(False)
                        
            except Exception:
                msg_label.setText("Error: File Not Found")
                msg_label.setStyleSheet("color: #ff4444;")
                dot_label.setStyleSheet("color: #ff4444;")

    def reset_ui(self):
        """Restores the UI to a state where any module can be run."""
        for b in self.buttons:
            # Restore text (STOP CONVEYOR -> RUN CONVEYOR)
            if b.text().startswith("STOP"):
                b.setText(b.text().replace("STOP ", "RUN "))
            
            b.setEnabled(True)
            b.setStyleSheet("") # Back to default QSS
            

        self.tabs.currentWidget().findChildren(QLabel)[1].setText("●")
        self.tabs.currentWidget().findChildren(QLabel)[1].setStyleSheet("color: #333; font-size: 18px;")
        self.tabs.currentWidget().findChildren(QLabel)[2].setText("Ready to Launch")
        self.tabs.currentWidget().findChildren(QLabel)[2].setStyleSheet("font-size: 13px; color: #aaa;")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MasterLauncher()
    window.show()
    sys.exit(app.exec())