"""
AI Operations Copilot - Native PyQt6 Desktop Client
Pure Python & C++ Native Desktop Interface
"""

import sys
import os
import json
import threading

# Add root directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QLineEdit, QTextEdit, QPushButton, QComboBox, QTabWidget,
        QProgressBar, QSplitter, QGroupBox, QMessageBox
    )
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
    from PyQt6.QtGui import QFont, QColor, QPalette
except ImportError:
    print("PyQt6 is not available. Please install via 'pip install PyQt6'.")
    sys.exit(1)

from app.core.cpp_bridge import cpp_bridge
from app.core.workflow import PlannerAgent
from app.schemas.incident import IncidentCreate
import asyncio

class WorkerSignals(QObject):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"AI Operations Copilot — {cpp_bridge.version}")
        self.resize(1100, 750)
        self.init_ui()
        self.signals = WorkerSignals()
        self.signals.finished.connect(self.receive_result)
        self.signals.error.connect(self.receive_error)

    def init_ui(self):
        # Apply dark theme
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#090d16"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#f1f5f9"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#0f172a"))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#1e293b"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#f1f5f9"))
        palette.setColor(QPalette.ColorRole.Button, QColor("#1e293b"))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor("#f1f5f9"))
        palette.setColor(QPalette.ColorRole.Highlight, QColor("#3b82f6"))
        self.setPalette(palette)

        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("⚡ AI Operations Copilot")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        header_layout.addWidget(title_label)

        engine_badge = QLabel(f"[{cpp_bridge.version}]")
        engine_badge.setStyleSheet("color: #60a5fa; font-weight: bold;")
        header_layout.addWidget(engine_badge)
        header_layout.addStretch()

        main_layout.addLayout(header_layout)

        # Splitter (Left: Input Form, Right: Output Report)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left Panel: Inputs
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_widget.setLayout(left_layout)

        preset_box = QHBoxLayout()
        preset_box.addWidget(QLabel("Preset:"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["Database Saturation", "Memory / OOM Crash", "Network Timeout"])
        self.preset_combo.currentIndexChanged.connect(self.apply_preset)
        preset_box.addWidget(self.preset_combo)
        left_layout.addLayout(preset_box)

        left_layout.addWidget(QLabel("Incident Description:"))
        self.desc_input = QLineEdit()
        left_layout.addWidget(self.desc_input)

        left_layout.addWidget(QLabel("Application Logs (C++ Pattern Matching):"))
        self.logs_input = QTextEdit()
        self.logs_input.setFont(QFont("Consolas", 9))
        left_layout.addWidget(self.logs_input)

        left_layout.addWidget(QLabel("Metrics Telemetry (JSON):"))
        self.metrics_input = QTextEdit()
        self.metrics_input.setFont(QFont("Consolas", 9))
        left_layout.addWidget(self.metrics_input)

        self.run_btn = QPushButton("🚀 Run Incident Analysis (C++ Accelerated)")
        self.run_btn.setStyleSheet("background-color: #2563eb; color: white; padding: 10px; font-weight: bold; border-radius: 6px;")
        self.run_btn.clicked.connect(self.run_analysis)
        left_layout.addWidget(self.run_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        left_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready")
        left_layout.addWidget(self.status_label)

        splitter.addWidget(left_widget)

        # Right Panel: Output Tabs
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_widget.setLayout(right_layout)

        self.tabs = QTabWidget()
        self.report_view = QTextEdit()
        self.report_view.setReadOnly(True)
        self.report_view.setFont(QFont("Consolas", 10))
        self.tabs.addTab(self.report_view, "📑 Postmortem Report")

        self.debug_view = QTextEdit()
        self.debug_view.setReadOnly(True)
        self.debug_view.setFont(QFont("Consolas", 9))
        self.tabs.addTab(self.debug_view, "🔍 Raw Debug JSON")

        right_layout.addWidget(self.tabs)
        splitter.addWidget(right_widget)

        splitter.setSizes([450, 650])
        main_layout.addWidget(splitter)

        self.apply_preset(0)

    def apply_preset(self, index):
        if index == 0:
            self.desc_input.setText("Database lock contention causing severe latency")
            self.logs_input.setPlainText("[ERROR] Deadlock detected in database transaction\n[ERROR] Connection pool exhausted: active=100/100\n[ERROR] 500 Internal Server Error")
            self.metrics_input.setPlainText(json.dumps({"cpu_usage": [45, 92], "latency_ms": [150, 3800]}, indent=2))
        elif index == 1:
            self.desc_input.setText("Worker pod OOM crash and heap space exhaustion")
            self.logs_input.setPlainText("[WARN] High memory usage: 90%\n[ERROR] OutOfMemoryError: Java heap space\n[CRITICAL] oom-killer: killed process")
            self.metrics_input.setPlainText(json.dumps({"memory_usage": [70, 98], "latency_ms": [100, 2400]}, indent=2))
        elif index == 2:
            self.desc_input.setText("Payment upstream gateway timeout")
            self.logs_input.setPlainText("[WARN] Slow response from upstream\n[ERROR] Connection timed out\n[ERROR] 504 Gateway Timeout")
            self.metrics_input.setPlainText(json.dumps({"latency_ms": [200, 4800], "network_drop_rate": 0.12}, indent=2))

    def run_analysis(self):
        desc = self.desc_input.text()
        logs = [l for l in self.logs_input.toPlainText().split("\n") if l.strip()]
        try:
            metrics = json.loads(self.metrics_input.toPlainText()) if self.metrics_input.toPlainText() else {}
        except Exception as e:
            QMessageBox.critical(self, "Invalid JSON", f"Metrics field contains invalid JSON:\n{e}")
            return

        self.run_btn.setEnabled(False)
        self.progress_bar.setValue(10)
        self.status_label.setText("Analyzing logs and metrics in C++...")

        # Run synchronously in background thread
        def task():
            try:
                async def analyze():
                    service = PlannerAgent()
                    try:
                        return await service.analyze(IncidentCreate(description=desc,logs=logs,metrics=metrics))
                    finally:
                        await service.shutdown()
                result = asyncio.run(analyze())
                if result.status != "completed": raise RuntimeError(result.error or result.status)
                self.signals.finished.emit(result.result.model_dump(mode="json"))
            except Exception as exc:
                self.signals.error.emit(type(exc).__name__)

        threading.Thread(target=task, daemon=True).start()

    def receive_result(self, payload):
        from app.schemas.incident import ReportContent
        self.display_result(ReportContent.model_validate(payload))

    def receive_error(self, message):
        self.status_label.setText(message)
        self.run_btn.setEnabled(True)

    def display_result(self, report):
        self.progress_bar.setValue(100)
        self.status_label.setText(f"Analysis completed — {report.investigation.findings.engine} / {report.investigation.retrieval_mode} / {report.investigation.provider.active}")
        self.run_btn.setEnabled(True)

        self.report_view.setPlainText(report.summary)
        self.debug_view.setPlainText(json.dumps(report.dict(), default=str, indent=2))

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
