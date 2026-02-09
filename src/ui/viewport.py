"""Camera viewport widget for displaying live video."""

from __future__ import annotations

from typing import TYPE_CHECKING

import cv2
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel, QSizePolicy

if TYPE_CHECKING:
    import numpy.typing as npt


class CameraViewport(QLabel):
    """Widget that displays camera frames."""

    def __init__(self, width: int = 1280, height: int = 720) -> None:
        super().__init__()
        self._display_width = width
        self._display_height = height

        self.setMinimumSize(640, 480)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background-color: #1a1a1a; border: 1px solid #333;")

        self._show_placeholder()

    def _show_placeholder(self) -> None:
        """Show placeholder text when no frame is available."""
        self.setText("No Camera Feed")
        self.setStyleSheet(
            "background-color: #1a1a1a; border: 1px solid #333; "
            "color: #666; font-size: 24px;"
        )

    def update_frame(self, frame: npt.NDArray[np.uint8]) -> None:
        """Update the display with a new frame."""
        if frame is None:
            self._show_placeholder()
            return

        # Resize frame to fit display
        h, w = frame.shape[:2]
        scale = min(self._display_width / w, self._display_height / h)
        new_w, new_h = int(w * scale), int(h * scale)
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        # Convert BGR to RGB for Qt
        if len(resized.shape) == 3:
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            bytes_per_line = ch * w
            image = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        else:
            # Grayscale
            h, w = resized.shape
            image = QImage(resized.data, w, h, w, QImage.Format.Format_Grayscale8)

        self.setPixmap(QPixmap.fromImage(image))

    def resizeEvent(self, event: object) -> None:
        """Handle resize to update display dimensions."""
        super().resizeEvent(event)  # type: ignore[arg-type]
        size = self.size()
        self._display_width = size.width()
        self._display_height = size.height()
