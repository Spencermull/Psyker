"""GUI entry point. One app with embedded terminal running Psyker REPL."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMainWindow

from .dashboard import PsykerDashboard


def run_gui_impl() -> int:
    """Launch the Psyker GUI with embedded terminal (CLI inside the app)."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = QMainWindow()
    window.setWindowTitle("\u29bf PSYKER v0.1 \u29d7")
    window.setMinimumSize(1200, 700)
    window.resize(1600, 900)
    window.setCentralWidget(PsykerDashboard())
    window.setStyleSheet("QMainWindow { background-color: #0b0f14; }")
    window.show()
    return app.exec()
