"""GUI entry point. One app with embedded terminal running Psyker REPL."""

from __future__ import annotations

import sys

from PySide6.QtCore import QSettings, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMainWindow

from .. import __version__
from ..update_check import start_async_update_check
from .dashboard import PsykerDashboard


class PsykerMainWindow(QMainWindow):
    """Main GUI window with a persistent light/dark theme toggle."""

    def __init__(self) -> None:
        super().__init__()
        self._settings = QSettings("Psyker", "Psyker")
        saved_theme = str(self._settings.value("theme", "dark"))
        self._theme = "light" if saved_theme == "light" else "dark"

        self.setWindowTitle("\u29bf PSYKER v0.1 \u29d7")
        self.setMinimumSize(1200, 700)
        self.resize(1600, 900)

        self._dashboard = PsykerDashboard(theme=self._theme)
        self.setCentralWidget(self._dashboard)

        toolbar = self.addToolBar("View")
        toolbar.setObjectName("ViewToolbar")
        toolbar.setMovable(False)
        self._theme_action = QAction("Light Theme", self)
        self._theme_action.setCheckable(True)
        self._theme_action.setToolTip("Toggle light/dark theme")
        self._theme_action.toggled.connect(self._on_theme_toggled)
        toolbar.addAction(self._theme_action)

        self.apply_theme(self._theme)

    def _on_theme_toggled(self, enabled: bool) -> None:
        self.apply_theme("light" if enabled else "dark")

    def apply_theme(self, theme: str) -> None:
        self._theme = "light" if theme == "light" else "dark"
        if self._theme == "dark":
            window_bg = "#0b0f14"
            toolbar_bg = "#0f1520"
            toolbar_fg = "#79c0ff"
            border = "#8b5cf6"
        else:
            window_bg = "#eef2ff"
            toolbar_bg = "#f8fafc"
            toolbar_fg = "#2563eb"
            border = "#a78bfa"

        self._dashboard.set_theme(self._theme)
        self._theme_action.blockSignals(True)
        self._theme_action.setChecked(self._theme == "light")
        self._theme_action.blockSignals(False)
        self.setStyleSheet(
            f"""
            QMainWindow {{
                background-color: {window_bg};
            }}
            QToolBar#ViewToolbar {{
                background-color: {toolbar_bg};
                border: 1px solid {border};
                spacing: 6px;
            }}
            QToolButton {{
                color: {toolbar_fg};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 6px 10px;
            }}
            QToolButton:checked {{
                background: {toolbar_bg};
            }}
            """
        )
        self._settings.setValue("theme", self._theme)

    def show_update_notice(self, message: str) -> None:
        self.statusBar().showMessage(message, 15000)


def run_gui_impl(*, check_updates: bool = False) -> int:
    """Launch the Psyker GUI with embedded terminal (CLI inside the app)."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = PsykerMainWindow()
    if check_updates:
        start_async_update_check(
            __version__,
            lambda message: QTimer.singleShot(0, lambda msg=message: window.show_update_notice(msg)),
        )
    window.show()
    return app.exec()
