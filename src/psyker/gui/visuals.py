"""Visual asset helpers for Psyker GUI."""

from __future__ import annotations

from pathlib import Path
import sys

from PySide6.QtCore import QByteArray, QPoint, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QWidget


def _asset_bases() -> list[Path]:
    bases: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        bases.append(Path(meipass))
    bases.append(Path(sys.executable).resolve().parent)
    bases.append(Path(__file__).resolve().parents[3])
    return bases


def find_asset(relative_path: str | Path) -> Path | None:
    rel = Path(relative_path)
    rel_from_assets = rel if rel.parts and rel.parts[0] != "assets" else Path(*rel.parts[1:])
    for base in _asset_bases():
        candidate = base / "assets" / rel_from_assets
        if candidate.exists():
            return candidate
    return None


def render_svg_icon(icon_name: str, color: str, size: int = 16) -> QPixmap | None:
    icon_path = find_asset(Path("ui") / "icons" / f"{icon_name}.svg")
    if icon_path is None:
        return None
    try:
        svg_text = icon_path.read_text(encoding="utf-8")
    except OSError:
        return None

    svg_bytes = QByteArray(svg_text.replace("currentColor", color).encode("utf-8"))
    renderer = QSvgRenderer(svg_bytes)
    if not renderer.isValid():
        return None

    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    return QPixmap.fromImage(image)


class DecalOverlay(QWidget):
    """Low-opacity decal overlay (optional PNG assets)."""

    def __init__(self, theme: str = "dark", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme = theme
        self._opacity = 0.06
        self._full_screen_opacity = 0.035
        self._use_fullscreen_profile = False
        self._pixmaps = self._load_decals()
        self._scaled: list[QPixmap] = []
        self._scaled_for = (-1, -1)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

    def _load_decals(self) -> list[QPixmap]:
        decal_dir = find_asset(Path("ui") / "decals")
        if decal_dir is None or not decal_dir.exists():
            return []
        pixmaps: list[QPixmap] = []
        for path in sorted(decal_dir.glob("*.png")):
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                pixmaps.append(pixmap)
        return pixmaps

    def set_theme(self, theme: str) -> None:
        self._theme = theme
        self.update()

    def set_performance_profile(self, fullscreen_mode: bool) -> None:
        self._use_fullscreen_profile = bool(fullscreen_mode)
        self.update()

    def resizeEvent(self, event) -> None:  # noqa: ANN001
        super().resizeEvent(event)
        self._scaled_for = (-1, -1)

    def _ensure_scaled(self) -> None:
        size_key = (self.width(), self.height())
        if size_key == self._scaled_for:
            return
        self._scaled_for = size_key
        self._scaled = []
        if not self._pixmaps or self.width() <= 0 or self.height() <= 0:
            return

        target = max(64, min(self.width(), self.height()) // 5)
        for pixmap in self._pixmaps:
            self._scaled.append(
                pixmap.scaled(
                    target,
                    target,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

    def paintEvent(self, event) -> None:  # noqa: ANN001
        del event
        if not self._pixmaps:
            return
        self._ensure_scaled()
        if not self._scaled:
            return

        painter = QPainter(self)
        alpha = self._full_screen_opacity if self._use_fullscreen_profile else self._opacity
        painter.setOpacity(alpha)
        pads = 18

        corners = [
            QPoint(pads, pads),
            QPoint(max(pads, self.width() - self._scaled[0].width() - pads), pads),
            QPoint(pads, max(pads, self.height() - self._scaled[0].height() - pads)),
            QPoint(
                max(pads, self.width() - self._scaled[0].width() - pads),
                max(pads, self.height() - self._scaled[0].height() - pads),
            ),
        ]

        for idx, pixmap in enumerate(self._scaled[:4]):
            painter.drawPixmap(corners[idx], pixmap)

