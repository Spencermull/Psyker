"""Psyker GUI dashboard layout and panels."""

from __future__ import annotations

from collections import deque
from datetime import datetime
from pathlib import Path
import shlex

from PySide6.QtCore import QDir, QPoint, QTimer, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QFileSystemModel,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QTabWidget,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from ..cli import PsykerCLI, create_default_cli
from .terminal import EmbeddedTerminal

try:  # pragma: no cover - optional GUI dependency
    import psutil
except Exception:  # pragma: no cover - optional GUI dependency
    psutil = None

try:  # pragma: no cover - optional GUI dependency
    import pyqtgraph as pg
except Exception:  # pragma: no cover - optional GUI dependency
    pg = None


LOADABLE_SUFFIXES = {".psy", ".psya", ".psyw"}

THEMES: dict[str, dict[str, str]] = {
    "dark": {
        "bg": "#0b0f14",
        "panel_bg": "#0f1520",
        "input_bg": "#0d1117",
        "border": "#8b5cf6",
        "primary": "#79c0ff",
        "text": "#dbe7ff",
        "muted": "#6b7280",
        "alert": "#d946ef",
        "selected_bg": "#1b2538",
        "tree_alt_bg": "#121a28",
        "ram_plot": "#a78bfa",
    },
    "light": {
        "bg": "#eef2ff",
        "panel_bg": "#f8fafc",
        "input_bg": "#ffffff",
        "border": "#a78bfa",
        "primary": "#2563eb",
        "text": "#0f172a",
        "muted": "#475569",
        "alert": "#d946ef",
        "selected_bg": "#dbeafe",
        "tree_alt_bg": "#f1f5f9",
        "ram_plot": "#7c3aed",
    },
}


class TopContextBar(QFrame):
    """Top status bar with app identity, sandbox path, and runtime counts."""

    def __init__(self, cli: PsykerCLI, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cli = cli
        self.setObjectName("TopContextBar")
        self.setFrameShape(QFrame.StyledPanel)
        self.setFixedHeight(64)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(14)

        self._title = QLabel("\u29bf PSYKER v0.1 \u29d7")
        self._title.setObjectName("ContextTitle")
        self._sandbox = QLabel("")
        self._sandbox.setObjectName("ContextSandbox")
        self._counts = QLabel("")
        self._counts.setObjectName("ContextCounts")
        self._counts.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        layout.addWidget(self._title, 0)
        layout.addWidget(self._sandbox, 1)
        layout.addWidget(self._counts, 0)

        self.refresh()

    def refresh(self) -> None:
        runtime = self._cli.runtime
        self._sandbox.setText(f"SANDBOX: {runtime.sandbox.root}")
        self._counts.setText(
            f"AGENTS: {len(runtime.agents)}   WORKERS: {len(runtime.workers)}   TASKS: {len(runtime.tasks)}"
        )


class RightMonitorPanel(QFrame):
    """Monitor panel with metrics and runtime lists."""

    def __init__(self, cli: PsykerCLI, theme: str = "dark", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cli = cli
        self._theme = theme if theme in THEMES else "dark"
        self._colors = THEMES[self._theme]
        self.setObjectName("RightMonitorPanel")
        self.setFrameShape(QFrame.StyledPanel)

        self._cpu_series: deque[float] = deque([0.0] * 90, maxlen=90)
        self._ram_series: deque[float] = deque([0.0] * 90, maxlen=90)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("MONITOR")
        title.setObjectName("PanelTitle")
        layout.addWidget(title)

        self._tabs = QTabWidget()
        self._tabs.setObjectName("MonitorTabs")
        layout.addWidget(self._tabs, 1)

        self._agents_list = QListWidget()
        self._workers_list = QListWidget()
        self._tasks_list = QListWidget()
        self._progress_list = QListWidget()

        self._tabs.addTab(self._build_metrics_tab(), "CPU/GPU")
        self._tabs.addTab(self._build_list_tab(self._agents_list), "Agents")
        self._tabs.addTab(self._build_list_tab(self._workers_list), "Workers")
        self._tabs.addTab(self._build_list_tab(self._tasks_list), "Tasks")
        self._tabs.addTab(self._build_list_tab(self._progress_list), "Task progress")
        self._progress_list.addItem("No task runs yet")

        self._timer: QTimer | None = None
        if psutil is not None:
            self._timer = QTimer(self)
            self._timer.setInterval(1000)
            self._timer.timeout.connect(self._update_metrics)
            self._timer.start()
            self._update_metrics()

        self.refresh_runtime_lists()
        self._apply_plot_theme()

    def _build_metrics_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(4)

        cpu_title = QLabel("CPU:")
        ram_title = QLabel("RAM:")
        gpu_title = QLabel("GPU:")
        cpu_title.setObjectName("MetricLabel")
        ram_title.setObjectName("MetricLabel")
        gpu_title.setObjectName("MetricLabel")

        self._cpu_value = QLabel("--.-%")
        self._ram_value = QLabel("--.-%")
        self._gpu_value = QLabel("N/A")
        self._cpu_value.setObjectName("MetricValue")
        self._ram_value.setObjectName("MetricValue")
        self._gpu_value.setObjectName("MetricValue")

        grid.addWidget(cpu_title, 0, 0)
        grid.addWidget(self._cpu_value, 0, 1)
        grid.addWidget(ram_title, 1, 0)
        grid.addWidget(self._ram_value, 1, 1)
        grid.addWidget(gpu_title, 2, 0)
        grid.addWidget(self._gpu_value, 2, 1)
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)

        if pg is None or psutil is None:
            fallback = QLabel("Install pyqtgraph + psutil for live metrics.")
            fallback.setObjectName("MetricFallback")
            fallback.setWordWrap(True)
            layout.addWidget(fallback)
            layout.addStretch(1)
            self._plot = None
            self._cpu_curve = None
            self._ram_curve = None
            return widget

        plot = pg.PlotWidget()
        plot.setObjectName("MetricsPlot")
        plot.setBackground(self._colors["input_bg"])
        plot.showGrid(x=True, y=True, alpha=0.12)
        plot.setYRange(0, 100)
        plot.setMouseEnabled(False, False)
        plot.hideButtons()
        plot.setMenuEnabled(False)
        plot.getAxis("left").setPen(pg.mkPen(self._colors["border"]))
        plot.getAxis("bottom").setPen(pg.mkPen(self._colors["border"]))
        plot.getAxis("left").setTextPen(pg.mkPen(self._colors["muted"]))
        plot.getAxis("bottom").setTextPen(pg.mkPen(self._colors["muted"]))
        plot.setLabel("left", "%")
        plot.setLabel("bottom", "s")

        self._cpu_curve = plot.plot(pen=pg.mkPen(self._colors["primary"], width=2))
        self._ram_curve = plot.plot(pen=pg.mkPen(self._colors["ram_plot"], width=2))
        self._plot = plot
        layout.addWidget(plot, 1)
        return widget

    def _build_list_tab(self, list_widget: QListWidget) -> QWidget:
        list_widget.setObjectName("MonitorList")
        list_widget.setAlternatingRowColors(True)
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(list_widget)
        return wrapper

    def _update_metrics(self) -> None:
        if psutil is None:
            return
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        self._cpu_value.setText(f"{cpu:5.1f}%")
        self._ram_value.setText(f"{ram:5.1f}%")

        self._cpu_series.append(cpu)
        self._ram_series.append(ram)

        if self._cpu_curve is not None and self._ram_curve is not None:
            x_data = list(range(len(self._cpu_series)))
            self._cpu_curve.setData(x_data, list(self._cpu_series))
            self._ram_curve.setData(x_data, list(self._ram_series))

    def refresh_runtime_lists(self) -> None:
        self._populate_named_list(self._agents_list, sorted(self._cli.runtime.agents.keys()))
        self._populate_named_list(self._workers_list, sorted(self._cli.runtime.workers.keys()))
        self._populate_named_list(self._tasks_list, sorted(self._cli.runtime.tasks.keys()))

    def record_command_result(self, line: str, exit_code: int) -> None:
        verb, args = self._split_line(line)
        if verb != "run" or len(args) < 2:
            return
        stamp = datetime.now().strftime("%H:%M:%S")
        state = "OK" if exit_code == 0 else f"FAIL {exit_code}"
        row = f"{stamp}  {state:<7} {args[0]}/{args[1]}"
        item = QListWidgetItem(row)
        if exit_code != 0:
            item.setForeground(QColor(self._colors["alert"]))
        self._progress_list.insertItem(0, item)
        while self._progress_list.count() > 20:
            self._progress_list.takeItem(self._progress_list.count() - 1)

    def _populate_named_list(self, target: QListWidget, names: list[str]) -> None:
        target.clear()
        if not names:
            target.addItem("(none)")
            return
        width = max(len(name) for name in names)
        for idx, name in enumerate(names, start=1):
            target.addItem(f"{idx:>2}  {name:<{width}}")

    def set_theme(self, theme: str) -> None:
        self._theme = theme if theme in THEMES else "dark"
        self._colors = THEMES[self._theme]
        self._apply_plot_theme()

    def _apply_plot_theme(self) -> None:
        if pg is None or self._plot is None:
            return
        self._plot.setBackground(self._colors["input_bg"])
        self._plot.getAxis("left").setPen(pg.mkPen(self._colors["border"]))
        self._plot.getAxis("bottom").setPen(pg.mkPen(self._colors["border"]))
        self._plot.getAxis("left").setTextPen(pg.mkPen(self._colors["muted"]))
        self._plot.getAxis("bottom").setTextPen(pg.mkPen(self._colors["muted"]))
        if self._cpu_curve is not None:
            self._cpu_curve.setPen(pg.mkPen(self._colors["primary"], width=2))
        if self._ram_curve is not None:
            self._ram_curve.setPen(pg.mkPen(self._colors["ram_plot"], width=2))

    @staticmethod
    def _split_line(line: str) -> tuple[str, list[str]]:
        try:
            parts = shlex.split(line)
        except ValueError:
            return "", []
        if not parts:
            return "", []
        return parts[0], parts[1:]


class BottomFileExplorer(QFrame):
    """Bottom file explorer rooted at sandbox workspace."""

    def __init__(self, cli: PsykerCLI, terminal: EmbeddedTerminal, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cli = cli
        self._terminal = terminal
        self.setObjectName("BottomFileExplorer")
        self.setFrameShape(QFrame.StyledPanel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        title = QLabel("WORKSPACE FILE EXPLORER")
        title.setObjectName("PanelTitle")
        self._root_label = QLabel("")
        self._root_label.setObjectName("ExplorerRoot")
        layout.addWidget(title)
        layout.addWidget(self._root_label)

        self._model = QFileSystemModel(self)
        self._tree = QTreeView(self)
        self._tree.setObjectName("ExplorerTree")
        self._tree.setModel(self._model)
        self._tree.setAnimated(False)
        self._tree.setIndentation(16)
        self._tree.setSortingEnabled(True)
        self._tree.sortByColumn(0, Qt.AscendingOrder)
        self._tree.doubleClicked.connect(self._on_double_clicked)
        self._tree.setHeaderHidden(False)
        self._tree.setColumnWidth(0, 360)
        layout.addWidget(self._tree, 1)

        self.refresh_root()

    def refresh_root(self) -> None:
        self._cli.runtime.sandbox.ensure_layout()
        workspace = self._cli.runtime.sandbox.workspace
        self._root_label.setText(f"ROOT: {workspace}")

        self._model.setFilter(QDir.AllDirs | QDir.NoDotAndDotDot | QDir.Files)
        self._model.setNameFilters(["*"])  # Show all so workspace updates when files are created
        self._model.setNameFilterDisables(False)

        root_index = self._model.setRootPath(str(workspace))
        self._tree.setRootIndex(root_index)
        self._tree.expand(root_index)

    def _on_double_clicked(self, index) -> None:  # noqa: ANN001 - Qt index type
        if self._model.isDir(index):
            return
        path = Path(self._model.filePath(index))
        if path.suffix.lower() not in LOADABLE_SUFFIXES:
            return
        self._terminal.execute_command(f'load "{path}"')


class ScanlineOverlay(QWidget):
    """Low-opacity scanline overlay (background effect only)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)

    def paintEvent(self, _event) -> None:  # noqa: ANN001 - Qt event type
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        color = QColor(121, 192, 255, 10)
        for y in range(0, self.height(), 4):
            painter.setPen(color)
            painter.drawLine(QPoint(0, y), QPoint(self.width(), y))


class PsykerDashboard(QWidget):
    """Main dashboard widget combining top bar, REPL, monitor, and file explorer."""

    def __init__(self, cli: PsykerCLI | None = None, theme: str = "dark", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PsykerDashboard")
        self._cli = cli or create_default_cli()
        self._theme = theme if theme in THEMES else "dark"

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        self._top = TopContextBar(self._cli)
        root.addWidget(self._top, 0)

        self._terminal = EmbeddedTerminal(cli=self._cli)
        self._monitor = RightMonitorPanel(self._cli, theme=self._theme)
        self._explorer = BottomFileExplorer(self._cli, self._terminal)

        upper_splitter = QSplitter(Qt.Horizontal)
        upper_splitter.addWidget(self._terminal)
        upper_splitter.addWidget(self._monitor)
        upper_splitter.setStretchFactor(0, 8)
        upper_splitter.setStretchFactor(1, 2)

        lower_splitter = QSplitter(Qt.Vertical)
        lower_splitter.addWidget(upper_splitter)
        lower_splitter.addWidget(self._explorer)
        lower_splitter.setStretchFactor(0, 6)
        lower_splitter.setStretchFactor(1, 1)

        root.addWidget(lower_splitter, 1)

        self._scanline = ScanlineOverlay(self)
        self._scanline.raise_()

        self._terminal.commandExecuted.connect(self._on_command_executed)
        self.set_theme(self._theme)
        self._refresh_panels()

    def resizeEvent(self, event) -> None:  # noqa: ANN001 - Qt event type
        super().resizeEvent(event)
        self._scanline.setGeometry(self.rect())

    def _on_command_executed(self, line: str, code: int) -> None:
        self._monitor.record_command_result(line, code)
        self._refresh_panels()

    def _refresh_panels(self) -> None:
        self._top.refresh()
        self._monitor.refresh_runtime_lists()
        self._explorer.refresh_root()

    def set_theme(self, theme: str) -> None:
        self._theme = theme if theme in THEMES else "dark"
        self._terminal.set_theme(self._theme)
        self._monitor.set_theme(self._theme)
        self._apply_styles()

    def _apply_styles(self) -> None:
        colors = THEMES[self._theme]
        self.setStyleSheet(
            f"""
            QWidget#PsykerDashboard {{
                background-color: {colors['bg']};
                color: {colors['text']};
                font-family: Consolas, 'JetBrains Mono', monospace;
                font-size: 13px;
            }}
            QFrame#TopContextBar, QFrame#RightMonitorPanel, QFrame#BottomFileExplorer {{
                background-color: {colors['panel_bg']};
                border: 1px solid {colors['border']};
                border-radius: 8px;
            }}
            QLabel#ContextTitle {{
                color: {colors['primary']};
                font-weight: 700;
            }}
            QLabel#ContextSandbox {{
                color: {colors['text']};
            }}
            QLabel#ContextCounts {{
                color: {colors['primary']};
            }}
            QLabel#PanelTitle {{
                color: {colors['primary']};
                font-weight: 700;
                letter-spacing: 0.5px;
            }}
            QLabel#ExplorerRoot {{
                color: {colors['muted']};
            }}
            QTabWidget#MonitorTabs::pane {{
                border: 1px solid {colors['border']};
                background: {colors['input_bg']};
                top: -1px;
            }}
            QTabBar::tab {{
                background: {colors['panel_bg']};
                color: {colors['muted']};
                padding: 6px 10px;
                border: 1px solid {colors['border']};
                border-bottom: none;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                color: {colors['primary']};
                background: {colors['input_bg']};
            }}
            QListWidget#MonitorList {{
                border: 1px solid {colors['border']};
                background: {colors['input_bg']};
                padding: 4px;
                outline: none;
            }}
            QListWidget#MonitorList::item {{
                padding: 3px 6px;
            }}
            QListWidget#MonitorList::item:selected {{
                background: {colors['selected_bg']};
                color: {colors['primary']};
            }}
            QLabel#MetricLabel {{
                color: {colors['primary']};
                font-weight: 700;
            }}
            QLabel#MetricValue {{
                color: {colors['text']};
            }}
            QLabel#MetricFallback {{
                color: {colors['muted']};
            }}
            QTreeView#ExplorerTree {{
                border: 1px solid {colors['border']};
                background: {colors['input_bg']};
                alternate-background-color: {colors['tree_alt_bg']};
                padding: 4px;
            }}
            QTreeView#ExplorerTree::item {{
                padding: 3px 6px;
            }}
            QTreeView#ExplorerTree::item:selected {{
                background: {colors['selected_bg']};
                color: {colors['primary']};
            }}
            """
        )
