"""Projection widget for X/Y axis projections with statistics."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    import numpy.typing as npt


class ProjectionPlot(QFrame):
    """Widget that displays a 1D projection plot."""

    def __init__(self, orientation: str = "horizontal") -> None:
        super().__init__()
        self._orientation = orientation  # "horizontal" (X) or "vertical" (Y)
        self._data: npt.NDArray[np.float64] | None = None
        self._mean: float = 0.0
        self._std: float = 0.0

        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Sunken)
        self.setStyleSheet("background-color: #1a1a1a; border: 1px solid #333;")

        if orientation == "horizontal":
            self.setMinimumHeight(80)
            self.setMaximumHeight(120)
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        else:
            self.setMinimumWidth(80)
            self.setMaximumWidth(120)
            self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

    def update_data(self, data: npt.NDArray[np.float64]) -> None:
        """Update projection data."""
        self._data = data
        if len(data) > 0:
            self._mean = float(np.mean(data))
            self._std = float(np.std(data))
        else:
            self._mean = 0.0
            self._std = 0.0
        self.update()

    @property
    def mean(self) -> float:
        return self._mean

    @property
    def std(self) -> float:
        return self._std

    def paintEvent(self, event: object) -> None:
        """Draw the projection plot."""
        super().paintEvent(event)  # type: ignore[arg-type]

        if self._data is None or len(self._data) == 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        margin = 5

        # Normalize data to fit in widget
        data = self._data
        data_min = float(np.min(data))
        data_max = float(np.max(data))
        data_range = data_max - data_min if data_max > data_min else 1.0

        # Draw plot
        pen = QPen(QColor(0, 200, 255))
        pen.setWidth(1)
        painter.setPen(pen)

        if self._orientation == "horizontal":
            # X projection: data along width, amplitude along height
            plot_w = w - 2 * margin
            plot_h = h - 2 * margin

            x_scale = plot_w / len(data)
            y_scale = plot_h / data_range

            for i in range(len(data) - 1):
                x1 = margin + int(i * x_scale)
                x2 = margin + int((i + 1) * x_scale)
                y1 = h - margin - int((data[i] - data_min) * y_scale)
                y2 = h - margin - int((data[i + 1] - data_min) * y_scale)
                painter.drawLine(x1, y1, x2, y2)

            # Draw mean line
            mean_pen = QPen(QColor(255, 200, 0))
            mean_pen.setWidth(1)
            mean_pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(mean_pen)
            mean_y = h - margin - int((self._mean - data_min) * y_scale)
            painter.drawLine(margin, mean_y, w - margin, mean_y)

        else:
            # Y projection: data along height, amplitude along width
            plot_w = w - 2 * margin
            plot_h = h - 2 * margin

            y_scale = plot_h / len(data)
            x_scale = plot_w / data_range

            for i in range(len(data) - 1):
                y1 = margin + int(i * y_scale)
                y2 = margin + int((i + 1) * y_scale)
                x1 = margin + int((data[i] - data_min) * x_scale)
                x2 = margin + int((data[i + 1] - data_min) * x_scale)
                painter.drawLine(x1, y1, x2, y2)

            # Draw mean line
            mean_pen = QPen(QColor(255, 200, 0))
            mean_pen.setWidth(1)
            mean_pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(mean_pen)
            mean_x = margin + int((self._mean - data_min) * x_scale)
            painter.drawLine(mean_x, margin, mean_x, h - margin)

        painter.end()


class ProjectionPanel(QWidget):
    """Panel containing projection plots and statistics."""

    def __init__(self) -> None:
        super().__init__()
        self._visible = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # X projection (horizontal, below image)
        self._x_projection = ProjectionPlot("horizontal")

        # Stats labels for X
        x_stats_layout = QHBoxLayout()
        self._x_label = QLabel("X Projection")
        self._x_label.setStyleSheet("color: #0cf; font-weight: bold;")
        self._x_mean_label = QLabel("Mean: --")
        self._x_mean_label.setStyleSheet("color: #fc0;")
        self._x_std_label = QLabel("SD: --")
        self._x_std_label.setStyleSheet("color: #aaa;")
        x_stats_layout.addWidget(self._x_label)
        x_stats_layout.addStretch()
        x_stats_layout.addWidget(self._x_mean_label)
        x_stats_layout.addWidget(self._x_std_label)

        layout.addLayout(x_stats_layout)
        layout.addWidget(self._x_projection)

    def update_from_frame(self, frame: npt.NDArray[np.uint8] | None) -> None:
        """Calculate and update projections from a frame."""
        if frame is None:
            return

        # Convert to grayscale if needed
        if len(frame.shape) == 3:
            gray = np.mean(frame, axis=2)
        else:
            gray = frame.astype(np.float64)

        # X projection (mean along Y axis)
        x_projection = np.mean(gray, axis=0)
        self._x_projection.update_data(x_projection)

        # Update stats labels
        self._x_mean_label.setText(f"Mean: {self._x_projection.mean:.1f}")
        self._x_std_label.setText(f"SD: {self._x_projection.std:.1f}")

    def set_visible(self, visible: bool) -> None:
        """Show or hide the projection panel."""
        self._visible = visible
        self.setVisible(visible)


class YProjectionPanel(QWidget):
    """Panel for Y projection (vertical, side of image)."""

    def __init__(self) -> None:
        super().__init__()
        self._visible = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Stats labels for Y
        self._y_label = QLabel("Y")
        self._y_label.setStyleSheet("color: #0cf; font-weight: bold;")
        self._y_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._y_mean_label = QLabel("μ: --")
        self._y_mean_label.setStyleSheet("color: #fc0; font-size: 10px;")
        self._y_mean_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._y_std_label = QLabel("σ: --")
        self._y_std_label.setStyleSheet("color: #aaa; font-size: 10px;")
        self._y_std_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Y projection (vertical)
        self._y_projection = ProjectionPlot("vertical")

        layout.addWidget(self._y_label)
        layout.addWidget(self._y_mean_label)
        layout.addWidget(self._y_std_label)
        layout.addWidget(self._y_projection, stretch=1)

    def update_from_frame(self, frame: npt.NDArray[np.uint8] | None) -> None:
        """Calculate and update projection from a frame."""
        if frame is None:
            return

        # Convert to grayscale if needed
        if len(frame.shape) == 3:
            gray = np.mean(frame, axis=2)
        else:
            gray = frame.astype(np.float64)

        # Y projection (mean along X axis)
        y_projection = np.mean(gray, axis=1)
        self._y_projection.update_data(y_projection)

        # Update stats labels
        self._y_mean_label.setText(f"μ: {self._y_projection.mean:.1f}")
        self._y_std_label.setText(f"σ: {self._y_projection.std:.1f}")

    def set_visible(self, visible: bool) -> None:
        """Show or hide the projection panel."""
        self._visible = visible
        self.setVisible(visible)
