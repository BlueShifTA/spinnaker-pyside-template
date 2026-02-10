"""Camera viewport widget for displaying live video."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import cv2
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QLabel, QSizePolicy

if TYPE_CHECKING:
    import numpy.typing as npt


@dataclass
class OverlaySettings:
    """Settings for viewport overlays."""

    show_grid: bool = False
    show_crosshair: bool = True
    grid_spacing: int = 50
    crosshair_size: int = 40
    crosshair_extend: bool = False
    crosshair_width: int = 2
    grid_color: tuple[int, int, int] = (100, 100, 100)
    crosshair_color: tuple[int, int, int] = (0, 255, 0)


class CameraViewport(QLabel):
    """Widget that displays camera frames with optional overlays."""

    def __init__(self, width: int = 1280, height: int = 720) -> None:
        super().__init__()
        self._display_width = width
        self._display_height = height
        self._overlay = OverlaySettings()
        self._current_frame: npt.NDArray[np.uint8] | None = None

        self.setMinimumSize(320, 240)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setScaledContents(False)  # Don't stretch pixmap beyond widget
        self.setStyleSheet("background-color: #1a1a1a; border: 1px solid #333;")

        self._show_placeholder()

    def _show_placeholder(self) -> None:
        """Show placeholder text when no frame is available."""
        self.setText("No Camera Feed")
        self.setStyleSheet(
            "background-color: #1a1a1a; border: 1px solid #333; "
            "color: #666; font-size: 24px;"
        )

    def set_overlay_settings(self, settings: OverlaySettings) -> None:
        """Update overlay settings."""
        self._overlay = settings
        if self._current_frame is not None:
            self._render_frame(self._current_frame)

    def set_show_grid(self, show: bool) -> None:
        self._overlay.show_grid = show
        if self._current_frame is not None:
            self._render_frame(self._current_frame)

    def set_show_crosshair(self, show: bool) -> None:
        self._overlay.show_crosshair = show
        if self._current_frame is not None:
            self._render_frame(self._current_frame)

    def set_grid_spacing(self, spacing: int) -> None:
        self._overlay.grid_spacing = spacing
        if self._current_frame is not None:
            self._render_frame(self._current_frame)

    def set_crosshair_size(self, size: int) -> None:
        self._overlay.crosshair_size = size
        if self._current_frame is not None:
            self._render_frame(self._current_frame)

    def set_crosshair_extend(self, extend: bool) -> None:
        """Set whether crosshair extends to image edges."""
        self._overlay.crosshair_extend = extend
        if self._current_frame is not None:
            self._render_frame(self._current_frame)

    def set_crosshair_width(self, width: int) -> None:
        """Set crosshair line width in pixels."""
        self._overlay.crosshair_width = width
        if self._current_frame is not None:
            self._render_frame(self._current_frame)

    def update_frame(self, frame: npt.NDArray[np.uint8]) -> None:
        """Update the display with a new frame."""
        if frame is None:
            self._show_placeholder()
            return

        self._current_frame = frame
        self._render_frame(frame)

    def clear_frame(self) -> None:
        """Clear current frame and free memory."""
        self._current_frame = None
        self._show_placeholder()

    def _render_frame(self, frame: npt.NDArray[np.uint8]) -> None:
        """Render grayscale frame with overlays."""
        # Use actual widget size for scaling (respects layout constraints)
        display_w = max(self.width(), 320)
        display_h = max(self.height(), 240)

        # Resize frame to fit display
        h, w = frame.shape[:2]
        scale = min(display_w / w, display_h / h)
        new_w, new_h = int(w * scale), int(h * scale)
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        # Ensure contiguous memory for QImage
        resized = np.ascontiguousarray(resized)

        # Create QImage directly from grayscale data
        h, w = resized.shape
        bytes_per_line = w

        # Create QImage with copy of data (prevents memory issues)
        image = QImage(
            resized.data, w, h, bytes_per_line, QImage.Format.Format_Grayscale8
        ).copy()
        pixmap = QPixmap.fromImage(image)

        # Draw overlays
        if self._overlay.show_grid or self._overlay.show_crosshair:
            pixmap = self._draw_overlays(pixmap)

        self.setPixmap(pixmap)

    def _draw_overlays(self, pixmap: QPixmap) -> QPixmap:
        """Draw grid and crosshair overlays on pixmap."""
        result = QPixmap(pixmap)
        painter = QPainter(result)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = result.width(), result.height()
        cx, cy = w // 2, h // 2

        # Draw grid
        if self._overlay.show_grid:
            grid_pen = QPen(
                Qt.GlobalColor.gray
                if self._overlay.grid_color == (100, 100, 100)
                else Qt.GlobalColor.white
            )
            grid_pen.setWidth(1)
            grid_pen.setStyle(Qt.PenStyle.DotLine)
            painter.setPen(grid_pen)

            spacing = self._overlay.grid_spacing

            # Vertical lines
            x = cx
            while x < w:
                painter.drawLine(x, 0, x, h)
                if cx - (x - cx) >= 0:
                    painter.drawLine(cx - (x - cx), 0, cx - (x - cx), h)
                x += spacing

            # Horizontal lines
            y = cy
            while y < h:
                painter.drawLine(0, y, w, y)
                if cy - (y - cy) >= 0:
                    painter.drawLine(0, cy - (y - cy), w, cy - (y - cy))
                y += spacing

        # Draw crosshair
        if self._overlay.show_crosshair:
            crosshair_pen = QPen(Qt.GlobalColor.green)
            crosshair_pen.setWidth(self._overlay.crosshair_width)
            painter.setPen(crosshair_pen)

            if self._overlay.crosshair_extend:
                # Extend to edges
                painter.drawLine(0, cy, w, cy)  # Horizontal
                painter.drawLine(cx, 0, cx, h)  # Vertical
            else:
                # Fixed size from center
                size = self._overlay.crosshair_size
                painter.drawLine(cx - size, cy, cx + size, cy)
                painter.drawLine(cx, cy - size, cx, cy + size)

            # Center circle
            painter.drawEllipse(cx - 5, cy - 5, 10, 10)

        painter.end()
        return result

    def get_current_frame(self) -> npt.NDArray[np.uint8] | None:
        """Get the current frame for analysis."""
        return self._current_frame

    def resizeEvent(self, event: object) -> None:
        """Handle resize to update display dimensions."""
        super().resizeEvent(event)  # type: ignore[arg-type]
        size = self.size()
        self._display_width = size.width()
        self._display_height = size.height()
