import sys
import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPlainTextEdit, QPushButton, QLabel
from PyQt6.QtGui import QFont, QTextCursor
from PyQt6.QtCore import QProcess, Qt

class ConsoleWidget(QWidget):
    def __init__(self, workspace_path=None, parent=None):
        super().__init__(parent)
        self.workspace_path = workspace_path or os.getcwd()
        self.setStyleSheet("""
            QWidget {
                background-color: #000000;
                color: #39FF14;
            }
            QPlainTextEdit {
                background-color: #000000;
                color: #39FF14;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10pt;
                border: 1px solid #00FF00;
            }
            QLineEdit {
                background-color: #050505;
                color: #39FF14;
                border: 1px solid #00FF00;
                padding: 4px;
                font-family: 'Consolas', monospace;
            }
            QPushButton {
                background-color: #002200;
                color: #39FF14;
                border: 1px solid #39FF14;
                padding: 4px 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #004400;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Control Panel
        control_layout = QHBoxLayout()
        control_layout.addWidget(QLabel("Terminal (Integrated Console)"))
        
        control_layout.addStretch()
        
        self.clear_btn = QPushButton("Temizle")
        self.clear_btn.clicked.connect(self.clear_output)
        control_layout.addWidget(self.clear_btn)
        
        self.restart_btn = QPushButton("Yeniden Başlat")
        self.restart_btn.clicked.connect(lambda: self.start_shell(self.workspace_path))
        control_layout.addWidget(self.restart_btn)

        layout.addLayout(control_layout)

        # Output display
        self.output_area = QPlainTextEdit()
        self.output_area.setReadOnly(True)
        layout.addWidget(self.output_area, 1)

        # Input line
        input_layout = QHBoxLayout()
        self.prompt_label = QLabel("> ")
        input_layout.addWidget(self.prompt_label)
        
        self.input_line = QLineEdit()
        self.input_line.returnPressed.connect(self.send_command)
        input_layout.addWidget(self.input_line, 1)
        
        layout.addLayout(input_layout)

        # QProcess for running Powershell/CMD
        self.process = None
        self.start_shell(self.workspace_path)

    def change_directory(self, path):
        self.workspace_path = path
        self.start_shell(path)

    def start_shell(self, working_dir=None):
        if self.process:
            self.process.kill()
            self.process.waitForFinished()

        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.read_output)
        
        # Set working directory
        if working_dir:
            self.process.setWorkingDirectory(working_dir)
        else:
            self.process.setWorkingDirectory(self.workspace_path)

        # Start powershell on Windows
        if sys.platform == "win32":
            self.process.start("powershell.exe", ["-NoLogo"])
        else:
            self.process.start("bash", ["-i"])

        self.output_area.appendPlainText(f"--- Terminal Oturumu Başlatıldı ({working_dir or self.workspace_path}) ---")

    def read_output(self):
        data = self.process.readAllStandardOutput()
        # Decode properly
        try:
            text = data.data().decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = data.data().decode("cp857") # Turkish Windows default
            except Exception:
                text = data.data().decode("latin1", errors="replace")

        self.output_area.moveCursor(QTextCursor.MoveOperation.End)
        self.output_area.insertPlainText(text)
        self.output_area.moveCursor(QTextCursor.MoveOperation.End)

    def send_command(self):
        cmd = self.input_line.text()
        self.input_line.clear()
        if cmd.strip() == "clear" or cmd.strip() == "cls":
            self.clear_output()
            return
            
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.process.write((cmd + "\n").encode())
        else:
            self.output_area.appendPlainText("Terminal çalışmıyor, yeniden başlatılıyor...")
            self.start_shell()

    def clear_output(self):
        self.output_area.clear()

    def run_command_programmatically(self, cmd):
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.output_area.appendPlainText(f"> {cmd}\n")
            self.process.write((cmd + "\n").encode())

    def closeEvent(self, event):
        if self.process:
            self.process.kill()
        super().closeEvent(event)
