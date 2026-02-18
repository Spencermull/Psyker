"""Psyker GUI dashboard layout and panels."""

from __future__ import annotations

from collections import deque
from datetime import datetime
from pathlib import Path
import shlex

from PySide6.QtCore import QEasingCurve, QDir, QPoint, QPropertyAnimation, QSize, QTimer, Qt
from PySide6.QtGui import QColor, QIcon, QLinearGradient, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QFileSystemModel,
    QFrame,
    QGraphicsDropShadowEffect,
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
from .visuals import DecalOverlay, render_svg_icon

try:  # pragma: no cover - optional GUI dependency
    import psutil
except Exception:  # pragma: no cover - optional GUI dependency
    psutil = None

try:  # pragma: no cover - optional GUI dependency
    import pyqtgraph as pg
except Exception:  # pragma: no cover - optional GUI dependency
    pg = None

try:  # pragma: no cover - optional GUI dependency
    import numpy as np
    from vispy import app as vispy_app
    from vispy import scene
except Exception:  # pragma: no cover - optional GUI dependency
    np = None
    vispy_app = None
    scene = None


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


class TronBackdrop(QWidget):
    """Animated cyberpunk background layer (VisPy when available, painter fallback otherwise)."""

    def __init__(self, theme: str = "dark", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme = theme if theme in THEMES else "dark"
        self._colors = THEMES[self._theme]
        self.setObjectName("TronBackdrop")
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._phase = 0.0
        self._vispy_ready = False
        self._phase_step = 0.015
        self._vertical_density = 16
        self._horizontal_density = 20
        self._fallback_spacing = 32

        self._timer = QTimer(self)
        self._timer.setInterval(90)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

        if vispy_app is not None and scene is not None and np is not None:
            try:
                vispy_app.use_app("pyside6")
                self._canvas = scene.SceneCanvas(keys=None, bgcolor=self._colors["bg"], show=False)
                self._native = self._canvas.native
                self._native.setParent(self)
                self._view = self._canvas.central_widget.add_view()
                self._view.camera = scene.cameras.PanZoomCamera(aspect=1)
                self._view.camera.set_range(x=(-1.0, 1.0), y=(-1.0, 1.0))
                self._view.camera.interactive = False
                self._grid = scene.visuals.Line(parent=self._view.scene, width=1)
                self._pulse = scene.visuals.Line(parent=self._view.scene, width=2)
                self._vispy_ready = True
                self._update_vispy_frame()
            except Exception:
                self._vispy_ready = False

    def set_performance_profile(self, fullscreen_mode: bool) -> None:
        if fullscreen_mode:
            self._timer.setInterval(140)
            self._phase_step = 0.010
            self._vertical_density = 10
            self._horizontal_density = 12
            self._fallback_spacing = 48
        else:
            self._timer.setInterval(90)
            self._phase_step = 0.015
            self._vertical_density = 16
            self._horizontal_density = 20
            self._fallback_spacing = 32
        self.update()

    def set_theme(self, theme: str) -> None:
        self._theme = theme if theme in THEMES else "dark"
        self._colors = THEMES[self._theme]
        if self._vispy_ready:
            self._canvas.bgcolor = self._colors["bg"]
            self._update_vispy_frame()
        self.update()

    def resizeEvent(self, event) -> None:  # noqa: ANN001 - Qt event
        super().resizeEvent(event)
        if self._vispy_ready:
            self._native.setGeometry(self.rect())

    def _tick(self) -> None:
        if not self.isVisible():
            return
        self._phase = (self._phase + self._phase_step) % 1.0
        if self._vispy_ready:
            self._update_vispy_frame()
        else:
            self.update()

    def _update_vispy_frame(self) -> None:
        if not self._vispy_ready or np is None:
            return
        primary = QColor(self._colors["primary"])
        grid_color = (primary.redF(), primary.greenF(), primary.blueF(), 0.12)
        pulse_color = (primary.redF(), primary.greenF(), primary.blueF(), 0.28)

        vertical: list[list[float]] = []
        for x in np.linspace(-1.0, 1.0, self._vertical_density):
            vertical.append([float(x), -1.0])
            vertical.append([float(x), 1.0])

        horizontal: list[list[float]] = []
        y_values = np.linspace(-1.0, 1.0, self._horizontal_density) + (self._phase * 0.35)
        for y in y_values:
            wrapped = ((float(y) + 1.0) % 2.0) - 1.0
            horizontal.append([-1.0, wrapped])
            horizontal.append([1.0, wrapped])

        points = np.array(vertical + horizontal, dtype=np.float32)
        connect = np.arange(len(points), dtype=np.int32).reshape(-1, 2)
        self._grid.set_data(pos=points, connect=connect, color=grid_color)

        pulse_y = -1.0 + (2.0 * self._phase)
        pulse_points = np.array([[-1.0, pulse_y], [1.0, pulse_y]], dtype=np.float32)
        self._pulse.set_data(pos=pulse_points, color=pulse_color)

    def paintEvent(self, _event) -> None:  # noqa: ANN001 - Qt event
        if self._vispy_ready:
            return
        painter = QPainter(self)
        grad = QLinearGradient(0, 0, self.width(), self.height())
        if self._theme == "dark":
            grad.setColorAt(0.0, QColor("#060a12"))
            grad.setColorAt(0.55, QColor("#0b1020"))
            grad.setColorAt(1.0, QColor("#111a2d"))
        else:
            grad.setColorAt(0.0, QColor("#eef2ff"))
            grad.setColorAt(0.55, QColor("#e2e8f0"))
            grad.setColorAt(1.0, QColor("#dbeafe"))
        painter.fillRect(self.rect(), grad)

        line_color = QColor(self._colors["primary"])
        line_color.setAlpha(26)
        painter.setPen(QPen(line_color, 1))
        spacing = self._fallback_spacing
        offset = int(self._phase * spacing)
        for x in range(-self.height(), self.width() + self.height(), spacing):
            painter.drawLine(QPoint(x + offset, self.height()), QPoint(x + self.height() + offset, 0))


class HudFrame(QFrame):
    """Panel base with subtle HUD decals (corner brackets and segmented borders)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._hud_colors = THEMES["dark"]

    def set_hud_theme(self, colors: dict[str, str]) -> None:
        self._hud_colors = colors
        self.update()

    def paintEvent(self, event) -> None:  # noqa: ANN001 - Qt event
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = self.rect().adjusted(1, 1, -2, -2)

        border = QColor(self._hud_colors["border"])
        border.setAlpha(175)
        painter.setPen(QPen(border, 1.2))
        painter.drawRoundedRect(rect, 8, 8)

        inner = rect.adjusted(4, 4, -4, -4)
        inner_border = QColor(self._hud_colors["border"])
        inner_border.setAlpha(70)
        painter.setPen(QPen(inner_border, 1))
        painter.drawRoundedRect(inner, 6, 6)

        accent = QColor(self._hud_colors["primary"])
        accent.setAlpha(165)
        painter.setPen(QPen(accent, 1.4))
        segment = 15
        painter.drawLine(rect.left() + 8, rect.top() + 1, rect.left() + 8 + segment, rect.top() + 1)
        painter.drawLine(rect.left() + 1, rect.top() + 8, rect.left() + 1, rect.top() + 8 + segment)
        painter.drawLine(rect.right() - 8 - segment, rect.top() + 1, rect.right() - 8, rect.top() + 1)
        painter.drawLine(rect.right() - 1, rect.top() + 8, rect.right() - 1, rect.top() + 8 + segment)
        painter.drawLine(rect.left() + 1, rect.bottom() - 8 - segment, rect.left() + 1, rect.bottom() - 8)
        painter.drawLine(rect.left() + 8, rect.bottom() - 1, rect.left() + 8 + segment, rect.bottom() - 1)
        painter.drawLine(rect.right() - 1, rect.bottom() - 8 - segment, rect.right() - 1, rect.bottom() - 8)
        painter.drawLine(rect.right() - 8 - segment, rect.bottom() - 1, rect.right() - 8, rect.bottom() - 1)


class TopContextBar(HudFrame):
    """Top status bar with app identity, sandbox path, and runtime counts."""

    def __init__(self, cli: PsykerCLI, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cli = cli
        self.setObjectName("TopContextBar")
        self.setFrameShape(QFrame.StyledPanel)
        self.setFixedHeight(70)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        self._title_icon = QLabel()
        self._title_icon.setObjectName("ContextIcon")
        self._title = QLabel("\u29bf PSYKER v0.1 \u29d7")
        self._title.setObjectName("ContextTitle")
        self._sandbox_icon = QLabel()
        self._sandbox_icon.setObjectName("ContextIcon")
        self._sandbox_key = QLabel("SANDBOX")
        self._sandbox_key.setObjectName("ContextSandboxLabel")
        self._sandbox = QLabel("")
        self._sandbox.setObjectName("ContextSandbox")
        self._sandbox.setTextInteractionFlags(Qt.TextSelectableByMouse)

        layout.addWidget(self._title_icon, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._title, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addSpacing(8)
        layout.addWidget(self._sandbox_icon, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._sandbox_key, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._sandbox, 1, Qt.AlignmentFlag.AlignVCenter)

        self._count_icons: dict[str, QLabel] = {}
        self._count_values: dict[str, QLabel] = {}
        for key, title in (("agents", "AGENTS"), ("workers", "WORKERS"), ("tasks", "TASKS")):
            icon = QLabel()
            icon.setObjectName("ContextCounterIcon")
            label = QLabel(title)
            label.setObjectName("ContextCounterLabel")
            value = QLabel("00")
            value.setObjectName("ContextCounterValue")

            chip = QFrame()
            chip.setObjectName("ContextCounter")
            chip_layout = QHBoxLayout(chip)
            chip_layout.setContentsMargins(6, 2, 6, 2)
            chip_layout.setSpacing(6)
            chip_layout.addWidget(icon, 0, Qt.AlignmentFlag.AlignVCenter)
            chip_layout.addWidget(label, 0, Qt.AlignmentFlag.AlignVCenter)
            chip_layout.addWidget(value, 0, Qt.AlignmentFlag.AlignVCenter)
            layout.addWidget(chip, 0, Qt.AlignmentFlag.AlignVCenter)

            self._count_icons[key] = icon
            self._count_values[key] = value

        self._apply_icons()
        self.refresh()

    def refresh(self) -> None:
        runtime = self._cli.runtime
        self._sandbox.setText(str(runtime.sandbox.root))
        self._count_values["agents"].setText(f"{len(runtime.agents):02d}")
        self._count_values["workers"].setText(f"{len(runtime.workers):02d}")
        self._count_values["tasks"].setText(f"{len(runtime.tasks):02d}")

    def set_hud_theme(self, colors: dict[str, str]) -> None:
        super().set_hud_theme(colors)
        self._apply_icons(colors["primary"])

    def _apply_icons(self, color: str = "#79c0ff") -> None:
        icon_targets = [
            (self._title_icon, "app"),
            (self._sandbox_icon, "sandbox"),
            (self._count_icons["agents"], "agents"),
            (self._count_icons["workers"], "workers"),
            (self._count_icons["tasks"], "tasks"),
        ]
        for label, icon_name in icon_targets:
            pixmap = render_svg_icon(icon_name, color, size=14)
            if pixmap is None:
                label.clear()
            else:
                label.setPixmap(pixmap)


class RightMonitorPanel(HudFrame):
    """Monitor panel with metrics and runtime lists."""

    def __init__(self, cli: PsykerCLI, theme: str = "dark", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cli = cli
        self._theme = theme if theme in THEMES else "dark"
        self._colors = THEMES[self._theme]
        self.setObjectName("RightMonitorPanel")
        self.setFrameShape(QFrame.StyledPanel)
        self.set_hud_theme(self._colors)

        self._cpu_series: deque[float] = deque([0.0] * 90, maxlen=90)
        self._ram_series: deque[float] = deque([0.0] * 90, maxlen=90)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(6)
        self._title_icon = QLabel()
        self._title_icon.setObjectName("PanelIcon")
        self._title_label = QLabel("MONITOR")
        self._title_label.setObjectName("PanelTitle")
        title_row.addWidget(self._title_icon, 0, Qt.AlignmentFlag.AlignVCenter)
        title_row.addWidget(self._title_label, 0, Qt.AlignmentFlag.AlignVCenter)
        title_row.addStretch(1)
        layout.addLayout(title_row)

        self._tabs = QTabWidget()
        self._tabs.setObjectName("MonitorTabs")
        self._tabs.setIconSize(QSize(14, 14))
        layout.addWidget(self._tabs, 1)
        self._tab_icon_names = ["cpu", "agents", "workers", "tasks", "progress"]

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
        self._apply_icons()

    def _build_metrics_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        header = QLabel("SYSTEM")
        header.setObjectName("MetricHeader")
        layout.addWidget(header)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(2)

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
        self._cpu_value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._ram_value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._gpu_value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

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
        self._cpu_value.setText(f"{cpu:6.1f}%")
        self._ram_value.setText(f"{ram:6.1f}%")

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
            target.addItem(f"{idx:>2} | {name:<{width}}")

    def set_theme(self, theme: str) -> None:
        self._theme = theme if theme in THEMES else "dark"
        self._colors = THEMES[self._theme]
        self.set_hud_theme(self._colors)
        self._apply_icons()
        self._apply_plot_theme()

    def _apply_icons(self) -> None:
        title_icon = render_svg_icon("monitor", self._colors["primary"], size=14)
        if title_icon is None:
            self._title_icon.clear()
        else:
            self._title_icon.setPixmap(title_icon)

        for index, icon_name in enumerate(self._tab_icon_names):
            pixmap = render_svg_icon(icon_name, self._colors["primary"], size=14)
            if pixmap is None:
                self._tabs.setTabIcon(index, QIcon())
            else:
                self._tabs.setTabIcon(index, QIcon(pixmap))

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


class BottomFileExplorer(HudFrame):
    """Bottom file explorer rooted at sandbox workspace."""

    def __init__(self, cli: PsykerCLI, terminal: EmbeddedTerminal, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cli = cli
        self._terminal = terminal
        self._workspace_root: Path | None = None
        self.setObjectName("BottomFileExplorer")
        self.setFrameShape(QFrame.StyledPanel)
        self.set_hud_theme(THEMES["dark"])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(6)
        self._title_icon = QLabel()
        self._title_icon.setObjectName("PanelIcon")
        title = QLabel("FILES")
        title.setObjectName("PanelTitle")
        title_row.addWidget(self._title_icon, 0, Qt.AlignmentFlag.AlignVCenter)
        title_row.addWidget(title, 0, Qt.AlignmentFlag.AlignVCenter)
        title_row.addStretch(1)
        self._root_label = QLabel("")
        self._root_label.setObjectName("ExplorerRoot")
        layout.addLayout(title_row)
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

        self._model.setFilter(QDir.AllDirs | QDir.NoDotAndDotDot | QDir.Files)
        self._model.setNameFilters(["*"])  # QFileSystemModel handles live updates from filesystem watchers.
        self._model.setNameFilterDisables(False)
        self.refresh_root(force=True)
        self._apply_icon()

    def refresh_root(self, force: bool = False) -> None:
        self._cli.runtime.sandbox.ensure_layout()
        workspace = self._cli.runtime.sandbox.workspace
        self._root_label.setText(f"WORKSPACE: {workspace}")

        if not force and self._workspace_root == workspace:
            return

        root_index = self._model.setRootPath(str(workspace))
        self._tree.setRootIndex(root_index)
        self._tree.expand(root_index)
        self._workspace_root = workspace

    def _on_double_clicked(self, index) -> None:  # noqa: ANN001 - Qt index type
        if self._model.isDir(index):
            return
        path = Path(self._model.filePath(index))
        if path.suffix.lower() not in LOADABLE_SUFFIXES:
            return
        self._terminal.execute_command(f'load "{path}"')

    def set_theme(self, colors: dict[str, str]) -> None:
        self.set_hud_theme(colors)
        self._apply_icon(colors["primary"])

    def _apply_icon(self, color: str = "#79c0ff") -> None:
        pixmap = render_svg_icon("files", color, size=14)
        if pixmap is None:
            self._title_icon.clear()
        else:
            self._title_icon.setPixmap(pixmap)


class ScanlineOverlay(QWidget):
    """Low-opacity scanline overlay (background effect only)."""

    def __init__(self, theme: str = "dark", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme = theme if theme in THEMES else "dark"
        self._line_spacing = 4
        self._line_alpha = 10
        self._cache: QPixmap | None = None
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)

    def set_theme(self, theme: str) -> None:
        self._theme = theme if theme in THEMES else "dark"
        self._cache = None
        self.update()

    def set_performance_profile(self, fullscreen_mode: bool) -> None:
        if fullscreen_mode:
            self._line_spacing = 6
            self._line_alpha = 7
        else:
            self._line_spacing = 4
            self._line_alpha = 10
        self._cache = None
        self.update()

    def resizeEvent(self, event) -> None:  # noqa: ANN001 - Qt event type
        super().resizeEvent(event)
        self._cache = None

    def _build_cache(self) -> None:
        if self.width() <= 0 or self.height() <= 0:
            self._cache = None
            return
        pixmap = QPixmap(self.size())
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, False)
        if self._theme == "light":
            color = QColor(37, 99, 235, max(1, self._line_alpha - 2))
        else:
            color = QColor(121, 192, 255, self._line_alpha)
        painter.setPen(color)
        for y in range(0, self.height(), self._line_spacing):
            painter.drawLine(QPoint(0, y), QPoint(self.width(), y))
        painter.end()
        self._cache = pixmap

    def paintEvent(self, _event) -> None:  # noqa: ANN001 - Qt event type
        if self._cache is None or self._cache.size() != self.size():
            self._build_cache()
        if self._cache is None:
            return
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self._cache)


class PsykerDashboard(QWidget):
    """Main dashboard widget combining top bar, REPL, monitor, and file explorer."""

    def __init__(self, cli: PsykerCLI | None = None, theme: str = "dark", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PsykerDashboard")
        self._cli = cli or create_default_cli()
        self._theme = theme if theme in THEMES else "dark"
        self._fullscreen_perf_mode = False
        self._intro_animations: list[QPropertyAnimation] = []
        self._panel_effects: list[QGraphicsDropShadowEffect] = []

        self._backdrop = TronBackdrop(theme=self._theme, parent=self)
        self._decals = DecalOverlay(theme=self._theme, parent=self)
        self._decals.lower()
        self._backdrop.lower()

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

        self._scanline = ScanlineOverlay(theme=self._theme, parent=self)
        self._scanline.stackUnder(self._top)
        self._decals.stackUnder(self._scanline)
        self._backdrop.stackUnder(self._decals)
        self._install_panel_glow()

        self._terminal.commandExecuted.connect(self._on_command_executed)
        self.set_theme(self._theme)
        self._update_performance_profile(force=True)
        self._refresh_panels()
        self._run_intro_animation()

    def resizeEvent(self, event) -> None:  # noqa: ANN001 - Qt event type
        super().resizeEvent(event)
        self._backdrop.setGeometry(self.rect())
        self._decals.setGeometry(self.rect())
        self._scanline.setGeometry(self.rect())
        self._update_performance_profile()

    def _on_command_executed(self, line: str, code: int) -> None:
        self._monitor.record_command_result(line, code)
        if self._command_requires_runtime_refresh(line):
            self._refresh_panels()

    def _refresh_panels(self) -> None:
        self._top.refresh()
        self._monitor.refresh_runtime_lists()

    def set_theme(self, theme: str) -> None:
        self._theme = theme if theme in THEMES else "dark"
        colors = THEMES[self._theme]
        self._backdrop.set_theme(self._theme)
        self._top.set_hud_theme(colors)
        self._explorer.set_theme(colors)
        self._terminal.set_theme(self._theme)
        self._monitor.set_theme(self._theme)
        self._decals.set_theme(self._theme)
        self._scanline.set_theme(self._theme)
        glow_color = QColor(0, 212, 255, 36) if self._theme == "dark" else QColor(37, 99, 235, 24)
        for effect in self._panel_effects:
            effect.setColor(glow_color)
        self._apply_styles()
        self._update_performance_profile(force=True)

    def _update_performance_profile(self, force: bool = False) -> None:
        window = self.window()
        is_fullscreen = bool(window is not None and window.isFullScreen())
        large_surface = (self.width() * self.height()) >= 2_300_000
        enable_perf_mode = is_fullscreen or large_surface
        if not force and enable_perf_mode == self._fullscreen_perf_mode:
            return
        self._fullscreen_perf_mode = enable_perf_mode

        self._backdrop.set_performance_profile(enable_perf_mode)
        self._decals.set_performance_profile(enable_perf_mode)
        self._scanline.set_performance_profile(enable_perf_mode)
        self._terminal.set_output_glow_enabled(not enable_perf_mode)

        for effect in self._panel_effects:
            effect.setEnabled(not enable_perf_mode)

    @staticmethod
    def _command_requires_runtime_refresh(line: str) -> bool:
        try:
            parts = shlex.split(line)
        except ValueError:
            return False
        if not parts:
            return False
        return parts[0] in {"load", "sandbox"}

    def _apply_styles(self) -> None:
        colors = THEMES[self._theme]
        dark_mode = self._theme == "dark"
        panel_rgba = "rgba(15, 21, 32, 220)" if dark_mode else "rgba(248, 250, 252, 235)"
        input_rgba = "rgba(13, 17, 23, 220)" if dark_mode else "rgba(255, 255, 255, 240)"
        input_active_rgba = "rgba(13, 17, 23, 230)" if dark_mode else "rgba(255, 255, 255, 250)"
        border_rgba = "rgba(139, 92, 246, 140)" if dark_mode else "rgba(167, 139, 250, 150)"
        list_alt_rgba = "rgba(18, 26, 40, 210)" if dark_mode else "rgba(241, 245, 249, 235)"
        self.setStyleSheet(
            f"""
            QWidget#PsykerDashboard {{
                background-color: transparent;
                color: {colors['text']};
                font-family: Consolas, 'JetBrains Mono', monospace;
                font-size: 13px;
            }}
            QFrame#TopContextBar, QFrame#RightMonitorPanel, QFrame#BottomFileExplorer {{
                background-color: {panel_rgba};
                border: 1px solid transparent;
                border-radius: 8px;
            }}
            QLabel#ContextTitle {{
                color: {colors['primary']};
                font-weight: 700;
                letter-spacing: 0.6px;
            }}
            QLabel#ContextIcon, QLabel#ContextCounterIcon {{
                min-width: 14px;
                max-width: 14px;
                min-height: 14px;
                max-height: 14px;
            }}
            QLabel#ContextSandboxLabel {{
                color: {colors['primary']};
                font-weight: 700;
                letter-spacing: 0.5px;
            }}
            QLabel#ContextSandbox {{
                color: {colors['text']};
                font-size: 12px;
            }}
            QFrame#ContextCounter {{
                border: 1px solid {border_rgba};
                border-radius: 6px;
                background: {input_rgba};
            }}
            QLabel#ContextCounterLabel {{
                color: {colors['muted']};
                font-size: 11px;
            }}
            QLabel#ContextCounterValue {{
                color: {colors['primary']};
                font-weight: 700;
                font-size: 12px;
            }}
            QLabel#PanelTitle {{
                color: {colors['primary']};
                font-weight: 700;
                letter-spacing: 0.5px;
            }}
            QLabel#PanelIcon {{
                min-width: 14px;
                max-width: 14px;
                min-height: 14px;
                max-height: 14px;
            }}
            QLabel#ExplorerRoot {{
                color: {colors['muted']};
                font-size: 12px;
            }}
            QLabel#MetricHeader {{
                color: {colors['muted']};
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 0.5px;
            }}
            QTabWidget#MonitorTabs::pane {{
                border: 1px solid {border_rgba};
                background: {input_rgba};
                top: -1px;
            }}
            QTabBar::tab {{
                background: {panel_rgba};
                color: {colors['muted']};
                padding: 6px 10px;
                border: 1px solid {border_rgba};
                border-bottom: none;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                color: {colors['primary']};
                background: {input_active_rgba};
            }}
            QListWidget#MonitorList {{
                border: 1px solid {border_rgba};
                background: {input_rgba};
                padding: 4px;
                outline: none;
                font-family: Consolas, 'JetBrains Mono', monospace;
                font-size: 12px;
            }}
            QListWidget#MonitorList::item {{
                min-height: 20px;
                padding: 2px 6px;
            }}
            QListWidget#MonitorList::item:selected {{
                background: {colors['selected_bg']};
                color: {colors['primary']};
            }}
            QLabel#MetricLabel {{
                color: {colors['primary']};
                font-weight: 700;
                font-size: 12px;
            }}
            QLabel#MetricValue {{
                color: {colors['text']};
                font-family: Consolas, 'JetBrains Mono', monospace;
                font-size: 12px;
            }}
            QLabel#MetricFallback {{
                color: {colors['muted']};
            }}
            QTreeView#ExplorerTree {{
                border: 1px solid {border_rgba};
                background: {input_rgba};
                alternate-background-color: {list_alt_rgba};
                padding: 4px;
                font-family: Consolas, 'JetBrains Mono', monospace;
                font-size: 12px;
            }}
            QTreeView#ExplorerTree::item {{
                min-height: 20px;
                padding: 2px 6px;
            }}
            QTreeView#ExplorerTree::item:selected {{
                background: {colors['selected_bg']};
                color: {colors['primary']};
            }}
            """
        )

    def _install_panel_glow(self) -> None:
        self._panel_effects.clear()
        glow_targets = [self._top, self._monitor, self._explorer]
        for widget in glow_targets:
            effect = QGraphicsDropShadowEffect(widget)
            effect.setBlurRadius(10)
            effect.setOffset(0, 0)
            effect.setColor(QColor(0, 212, 255, 36))
            widget.setGraphicsEffect(effect)
            self._panel_effects.append(effect)

    def _run_intro_animation(self) -> None:
        self._intro_animations.clear()
        for delay_index, effect in enumerate(self._panel_effects):
            glow = QPropertyAnimation(effect, b"blurRadius", self)
            glow.setDuration(260 + delay_index * 90)
            glow.setStartValue(2.0)
            glow.setEndValue(26.0)
            glow.setEasingCurve(QEasingCurve.OutCubic)
            glow.start()
            self._intro_animations.append(glow)
