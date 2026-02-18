"""GUI entry point. One app with embedded terminal running Psyker REPL."""

from __future__ import annotations

import sys

from PySide6.QtCore import QSettings, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMainWindow

from .. import __version__
from ..update_check import start_async_update_check
from .dashboard import PsykerDashboard

try:  # pragma: no cover - optional GUI dependency
    from qt_material import apply_stylesheet as _apply_material_stylesheet
except Exception:  # pragma: no cover - optional GUI dependency
    _apply_material_stylesheet = None


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
        self._apply_global_theme_engines()
        if self._theme == "dark":
            window_bg = "#06090F"
            toolbar_bg = "#0B0F1A"
            toolbar_fg = "#E6F2FF"
            border = "#1E2C44"
            hover = "#2FD8FF"
            accent = "#E64CFF"
            checked_bg = "rgba(47, 216, 255, 32)"
        else:
            window_bg = "#070C14"
            toolbar_bg = "#101625"
            toolbar_fg = "#E6F2FF"
            border = "#243758"
            hover = "#2FD8FF"
            accent = "#9B5CFF"
            checked_bg = "rgba(47, 216, 255, 40)"

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
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {toolbar_bg},
                    stop:1 {window_bg});
                border: 1px solid {border};
                spacing: 6px;
            }}
            QToolButton {{
                color: {toolbar_fg};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 6px 10px;
                background: transparent;
            }}
            QToolButton:hover {{
                color: {hover};
                border: 1px solid {hover};
            }}
            QToolButton:pressed {{
                color: {accent};
                border: 1px solid {accent};
            }}
            QToolButton:checked {{
                color: {hover};
                border: 1px solid {hover};
                background: {checked_bg};
            }}
            """
        )
        self._settings.setValue("theme", self._theme)

    def _apply_global_theme_engines(self) -> None:
        app = QApplication.instance()
        if app is None:
            return

        if _apply_material_stylesheet is not None:
            material_theme = "dark_cyan.xml"
            try:
                _apply_material_stylesheet(
                    app,
                    theme=material_theme,
                    extra={
                        "density_scale": "0",
                        "font_family": "JetBrains Mono",
                    },
                )
            except Exception:
                pass


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
