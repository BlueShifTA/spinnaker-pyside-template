"""Projection widget for X/Y axis projections with statistics.

This module provides widgets for displaying 1D projections with:
- Multiple projection modes (sum, min, max, average)
- FWHM calculation for beam profiling
- Normalization option
- Axis labels with position markers
- Expandable popup for detailed analysis
- Export capabilities
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.projection import ProjectionStats

if TYPE_CHECKING:
    import numpy.typing as npt


class ProjectionPlot(QFrame):
    """Widget that displays a 1D projection plot with axis labels.

    Features:
    - Efficient QPainterPath rendering with downsampling
    - Axis labels showing position and intensity
    - FWHM markers when available
    - Mean line indicator
    """

    # Signal emitted when user clicks to expand
    expand_requested = Signal()

    def __init__(self, orientation: str = "horizontal") -> None:
        """Initialize projection plot.

        Args:
            orientation: "horizontal" for X projection, "vertical" for Y.
        """
        super().__init__()
        self._orientation = orientation
        self._data: npt.NDArray[np.float64] | None = None
        self._stats: ProjectionStats | None = None
        self._normalized = False
        self._show_axis = True

        # Cached rendering
        self._cached_path: QPainterPath | None = None
        self._cached_mean_pos: int = 0
        self._cached_fwhm_left: int | None = None
        self._cached_fwhm_right: int | None = None

        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Sunken)
        self.setStyleSheet("background-color: #1a1a1a; border: 1px solid #333;")

        if orientation == "horizontal":
            self.setMinimumHeight(100)
            self.setMaximumHeight(150)
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        else:
            self.setMinimumWidth(100)
            self.setMaximumWidth(150)
            self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

    def update_data(
        self,
        data: npt.NDArray[np.float64],
        stats: ProjectionStats,
        normalized: bool = False,
    ) -> None:
        """Update projection data with statistics.

        Args:
            data: 1D projection array.
            stats: Pre-calculated statistics including FWHM.
            normalized: Whether the data is normalized to [0, 1].
        """
        self._data = data
        self._stats = stats
        self._normalized = normalized
        self._cached_path = None
        self.update()

    @property
    def stats(self) -> ProjectionStats | None:
        """Get current projection statistics."""
        return self._stats

    @property
    def mean(self) -> float:
        """Get mean value (for backward compatibility)."""
        return self._stats.mean if self._stats else 0.0

    @property
    def std(self) -> float:
        """Get standard deviation (for backward compatibility)."""
        return self._stats.std if self._stats else 0.0

    def set_show_axis(self, show: bool) -> None:
        """Enable or disable axis labels."""
        self._show_axis = show
        self.update()

    def _build_path(self) -> None:
        """Build cached QPainterPath for efficient drawing."""
        if self._data is None or len(self._data) == 0:
            self._cached_path = None
            return

        data = self._data
        w, h = self.width(), self.height()
        axis_margin = 30 if self._show_axis else 5
        margin = 5

        data_min = float(np.min(data))
        data_max = float(np.max(data))
        data_range = data_max - data_min if data_max > data_min else 1.0

        path = QPainterPath()

        if self._orientation == "horizontal":
            plot_w = w - margin - axis_margin
            plot_h = h - margin - axis_margin

            step = max(1, len(data) // 500)
            sampled = data[::step]

            x_scale = plot_w / max(len(sampled) - 1, 1)
            y_scale = plot_h / data_range

            x0 = axis_margin
            y0 = h - axis_margin - int((sampled[0] - data_min) * y_scale)
            path.moveTo(x0, y0)

            for i in range(1, len(sampled)):
                x = axis_margin + int(i * x_scale)
                y = h - axis_margin - int((sampled[i] - data_min) * y_scale)
                path.lineTo(x, y)

            self._cached_mean_pos = (
                h - axis_margin - int((self._stats.mean - data_min) * y_scale)
                if self._stats
                else 0
            )

            # FWHM positions
            if self._stats and self._stats.fwhm_left is not None:
                fwhm_scale = plot_w / max(len(data) - 1, 1)
                self._cached_fwhm_left = axis_margin + int(
                    self._stats.fwhm_left * fwhm_scale
                )
                self._cached_fwhm_right = (
                    axis_margin + int(self._stats.fwhm_right * fwhm_scale)
                    if self._stats.fwhm_right
                    else None
                )
            else:
                self._cached_fwhm_left = None
                self._cached_fwhm_right = None
        else:
            plot_w = w - margin - axis_margin
            plot_h = h - margin - axis_margin

            step = max(1, len(data) // 500)
            sampled = data[::step]

            y_scale = plot_h / max(len(sampled) - 1, 1)
            x_scale = plot_w / data_range

            x0 = axis_margin + int((sampled[0] - data_min) * x_scale)
            y0 = margin
            path.moveTo(x0, y0)

            for i in range(1, len(sampled)):
                x = axis_margin + int((sampled[i] - data_min) * x_scale)
                y = margin + int(i * y_scale)
                path.lineTo(x, y)

            self._cached_mean_pos = (
                axis_margin + int((self._stats.mean - data_min) * x_scale)
                if self._stats
                else 0
            )

            if self._stats and self._stats.fwhm_left is not None:
                fwhm_scale = plot_h / max(len(data) - 1, 1)
                self._cached_fwhm_left = margin + int(
                    self._stats.fwhm_left * fwhm_scale
                )
                self._cached_fwhm_right = (
                    margin + int(self._stats.fwhm_right * fwhm_scale)
                    if self._stats.fwhm_right
                    else None
                )
            else:
                self._cached_fwhm_left = None
                self._cached_fwhm_right = None

        self._cached_path = path

    def paintEvent(self, event: object) -> None:
        """Draw the projection plot with axis and FWHM markers."""
        super().paintEvent(event)  # type: ignore[arg-type]

        if self._data is None or len(self._data) == 0:
            return

        if self._cached_path is None:
            self._build_path()

        if self._cached_path is None:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        axis_margin = 30 if self._show_axis else 5
        margin = 5

        # Draw axis if enabled
        if self._show_axis:
            self._draw_axis(painter, w, h, axis_margin, margin)

        # Draw FWHM region
        if self._cached_fwhm_left is not None and self._cached_fwhm_right is not None:
            fwhm_pen = QPen(QColor(100, 255, 100, 80))
            fwhm_pen.setWidth(1)
            painter.setPen(fwhm_pen)
            painter.setBrush(QColor(100, 255, 100, 30))

            if self._orientation == "horizontal":
                painter.drawRect(
                    self._cached_fwhm_left,
                    margin,
                    self._cached_fwhm_right - self._cached_fwhm_left,
                    h - axis_margin - margin,
                )
            else:
                painter.drawRect(
                    axis_margin,
                    self._cached_fwhm_left,
                    w - axis_margin - margin,
                    self._cached_fwhm_right - self._cached_fwhm_left,
                )

        # Draw plot line
        pen = QPen(QColor(0, 200, 255))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(self._cached_path)

        # Draw mean line
        mean_pen = QPen(QColor(255, 200, 0))
        mean_pen.setWidth(1)
        mean_pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(mean_pen)

        if self._orientation == "horizontal":
            painter.drawLine(
                axis_margin, self._cached_mean_pos, w - margin, self._cached_mean_pos
            )
        else:
            painter.drawLine(
                self._cached_mean_pos, margin, self._cached_mean_pos, h - axis_margin
            )

        painter.end()

    def _draw_axis(
        self, painter: QPainter, w: int, h: int, axis_margin: int, margin: int
    ) -> None:
        """Draw axis labels and tick marks."""
        if self._data is None or self._stats is None:
            return

        axis_pen = QPen(QColor(150, 150, 150))
        axis_pen.setWidth(1)
        painter.setPen(axis_pen)

        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)

        data_min = self._stats.min_val
        data_max = self._stats.max_val

        if self._orientation == "horizontal":
            # X axis (position)
            painter.drawLine(axis_margin, h - axis_margin, w - margin, h - axis_margin)
            # Y axis (intensity)
            painter.drawLine(axis_margin, margin, axis_margin, h - axis_margin)

            # X labels (position: 0, mid, max)
            painter.drawText(axis_margin, h - 5, "0")
            mid_x = axis_margin + (w - axis_margin - margin) // 2
            painter.drawText(mid_x - 10, h - 5, str(len(self._data) // 2))
            painter.drawText(w - margin - 30, h - 5, str(len(self._data)))

            # Y labels (intensity)
            if self._normalized:
                painter.drawText(5, margin + 10, "1.0")
                painter.drawText(5, h - axis_margin, "0.0")
            else:
                painter.drawText(5, margin + 10, f"{data_max:.0f}")
                painter.drawText(5, h - axis_margin, f"{data_min:.0f}")
        else:
            # Y axis (position)
            painter.drawLine(axis_margin, margin, axis_margin, h - axis_margin)
            # X axis (intensity)
            painter.drawLine(axis_margin, h - axis_margin, w - margin, h - axis_margin)

            # Y labels (position)
            painter.drawText(5, margin + 10, "0")
            painter.drawText(5, h - axis_margin, str(len(self._data)))

            # X labels (intensity)
            if self._normalized:
                painter.drawText(axis_margin, h - 5, "0")
                painter.drawText(w - margin - 20, h - 5, "1.0")
            else:
                painter.drawText(axis_margin, h - 5, f"{data_min:.0f}")
                painter.drawText(w - margin - 25, h - 5, f"{data_max:.0f}")

    def resizeEvent(self, event: object) -> None:
        """Invalidate cache on resize."""
        super().resizeEvent(event)  # type: ignore[arg-type]
        self._cached_path = None

    def mouseDoubleClickEvent(self, event: object) -> None:
        """Emit expand signal on double-click."""
        self.expand_requested.emit()


class ProjectionPanel(QWidget):
    """Panel containing X projection plot and statistics with controls.

    Features:
    - Projection mode selector (sum, min, max, average)
    - Normalization toggle
    - FWHM, mean, and SD display
    - Export button
    - Expand button for detailed view
    """

    # Signals for settings changes
    mode_changed = Signal(str)
    normalize_changed = Signal(bool)
    export_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._visible = False
        self._current_data: npt.NDArray[np.float64] | None = None
        self._current_stats: ProjectionStats | None = None
        self._current_normalized = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)

        # Header with title and controls
        header = QHBoxLayout()

        self._title = QLabel("X Projection")
        self._title.setStyleSheet("color: #0cf; font-weight: bold;")
        header.addWidget(self._title)

        header.addStretch()

        # Mode selector
        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["Average", "Sum", "Min", "Max"])
        self._mode_combo.setFixedWidth(70)
        self._mode_combo.setStyleSheet("font-size: 10px;")
        self._mode_combo.currentTextChanged.connect(self._on_mode_changed)
        header.addWidget(self._mode_combo)

        # Normalize checkbox
        self._normalize_check = QCheckBox("Norm")
        self._normalize_check.setStyleSheet("font-size: 10px;")
        self._normalize_check.stateChanged.connect(
            lambda s: self.normalize_changed.emit(s == 2)
        )
        header.addWidget(self._normalize_check)

        # Export button
        self._export_btn = QPushButton("📥")
        self._export_btn.setFixedSize(24, 24)
        self._export_btn.setToolTip("Export projection data")
        self._export_btn.clicked.connect(self.export_requested.emit)
        header.addWidget(self._export_btn)

        # Expand button
        self._expand_btn = QPushButton("⛶")
        self._expand_btn.setFixedSize(24, 24)
        self._expand_btn.setToolTip("Expand projection view")
        self._expand_btn.clicked.connect(self._show_expanded)
        header.addWidget(self._expand_btn)

        layout.addLayout(header)

        # Stats row
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(10)

        self._mean_label = QLabel("μ: --")
        self._mean_label.setStyleSheet("color: #fc0; font-size: 11px;")
        stats_layout.addWidget(self._mean_label)

        self._std_label = QLabel("σ: --")
        self._std_label.setStyleSheet("color: #aaa; font-size: 11px;")
        stats_layout.addWidget(self._std_label)

        self._fwhm_label = QLabel("FWHM: --")
        self._fwhm_label.setStyleSheet("color: #6f6; font-size: 11px;")
        stats_layout.addWidget(self._fwhm_label)

        self._peak_label = QLabel("Peak: --")
        self._peak_label.setStyleSheet("color: #f6f; font-size: 11px;")
        stats_layout.addWidget(self._peak_label)

        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        # Projection plot
        self._plot = ProjectionPlot("horizontal")
        self._plot.expand_requested.connect(self._show_expanded)
        layout.addWidget(self._plot)

    def _on_mode_changed(self, text: str) -> None:
        """Handle mode selection change."""
        mode_map = {"Average": "avg", "Sum": "sum", "Min": "min", "Max": "max"}
        self.mode_changed.emit(mode_map.get(text, "avg"))

    def update_projection(
        self,
        data: npt.NDArray[np.float64],
        stats: ProjectionStats,
        normalized: bool = False,
    ) -> None:
        """Update projection with data and statistics."""
        self._current_data = data
        self._current_stats = stats
        self._current_normalized = normalized

        self._plot.update_data(data, stats, normalized)

        # Update stat labels
        self._mean_label.setText(f"μ: {stats.mean:.1f}")
        self._std_label.setText(f"σ: {stats.std:.1f}")

        if stats.fwhm is not None:
            self._fwhm_label.setText(f"FWHM: {stats.fwhm:.1f}")
        else:
            self._fwhm_label.setText("FWHM: --")

        self._peak_label.setText(f"Peak: {stats.peak_pos}")

    def _show_expanded(self) -> None:
        """Show expanded projection view in a dialog."""
        if self._current_data is None:
            return

        dialog = ExpandedProjectionDialog(
            self._current_data,
            self._current_stats,
            "X Projection",
            "horizontal",
            self._current_normalized,
            self,
        )
        dialog.exec()

    def set_visible(self, visible: bool) -> None:
        """Show or hide the projection panel."""
        self._visible = visible
        self.setVisible(visible)

    @property
    def mode(self) -> str:
        """Get current projection mode."""
        return self._mode_combo.currentText().lower()

    @property
    def normalize(self) -> bool:
        """Get normalization state."""
        return self._normalize_check.isChecked()


class YProjectionPanel(QWidget):
    """Panel for Y projection (vertical, left of image)."""

    mode_changed = Signal(str)
    normalize_changed = Signal(bool)
    export_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._visible = False
        self._current_data: npt.NDArray[np.float64] | None = None
        self._current_stats: ProjectionStats | None = None
        self._current_normalized = False
        self.setMinimumWidth(130)
        self.setMaximumWidth(160)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(4)

        # Title
        self._title = QLabel("Y Projection")
        self._title.setStyleSheet("color: #0cf; font-weight: bold; font-size: 10px;")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._title)

        # Mode selector
        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["Average", "Sum", "Min", "Max"])
        self._mode_combo.setStyleSheet("font-size: 9px;")
        self._mode_combo.currentTextChanged.connect(self._on_mode_changed)
        layout.addWidget(self._mode_combo)

        # Normalize checkbox
        self._normalize_check = QCheckBox("Normalize")
        self._normalize_check.setStyleSheet("font-size: 9px;")
        self._normalize_check.stateChanged.connect(
            lambda s: self.normalize_changed.emit(s == 2)
        )
        layout.addWidget(self._normalize_check)

        # Stats labels (vertical stack)
        self._mean_label = QLabel("μ: --")
        self._mean_label.setStyleSheet("color: #fc0; font-size: 9px;")
        layout.addWidget(self._mean_label)

        self._std_label = QLabel("σ: --")
        self._std_label.setStyleSheet("color: #aaa; font-size: 9px;")
        layout.addWidget(self._std_label)

        self._fwhm_label = QLabel("FWHM: --")
        self._fwhm_label.setStyleSheet("color: #6f6; font-size: 9px;")
        layout.addWidget(self._fwhm_label)

        # Buttons (vertical)
        self._export_btn = QPushButton("📥 Export")
        self._export_btn.setStyleSheet("font-size: 9px;")
        self._export_btn.setToolTip("Export projection data")
        self._export_btn.clicked.connect(self.export_requested.emit)
        layout.addWidget(self._export_btn)

        self._expand_btn = QPushButton("⛶ Expand")
        self._expand_btn.setStyleSheet("font-size: 9px;")
        self._expand_btn.setToolTip("Expand view")
        self._expand_btn.clicked.connect(self._show_expanded)
        layout.addWidget(self._expand_btn)

        # Projection plot
        self._plot = ProjectionPlot("vertical")
        self._plot.expand_requested.connect(self._show_expanded)
        layout.addWidget(self._plot, stretch=1)

    def _on_mode_changed(self, text: str) -> None:
        mode_map = {"Average": "avg", "Sum": "sum", "Min": "min", "Max": "max"}
        self.mode_changed.emit(mode_map.get(text, "avg"))

    def update_projection(
        self,
        data: npt.NDArray[np.float64],
        stats: ProjectionStats,
        normalized: bool = False,
    ) -> None:
        """Update projection with data and statistics."""
        self._current_data = data
        self._current_stats = stats
        self._current_normalized = normalized

        self._plot.update_data(data, stats, normalized)

        self._mean_label.setText(f"μ: {stats.mean:.1f}")
        self._std_label.setText(f"σ: {stats.std:.1f}")

        if stats.fwhm is not None:
            self._fwhm_label.setText(f"FWHM: {stats.fwhm:.1f}")
        else:
            self._fwhm_label.setText("FWHM: --")

    def _show_expanded(self) -> None:
        if self._current_data is None:
            return

        dialog = ExpandedProjectionDialog(
            self._current_data,
            self._current_stats,
            "Y Projection",
            "vertical",
            self._current_normalized,
            self,
        )
        dialog.exec()

    def set_visible(self, visible: bool) -> None:
        self._visible = visible
        self.setVisible(visible)

    @property
    def mode(self) -> str:
        return self._mode_combo.currentText().lower()

    @property
    def normalize(self) -> bool:
        return self._normalize_check.isChecked()


class ExpandedProjectionDialog(QDialog):
    """Dialog showing expanded projection view for detailed analysis."""

    def __init__(
        self,
        data: npt.NDArray[np.float64] | None,
        stats: ProjectionStats | None,
        title: str,
        orientation: str,
        normalized: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(800, 400)

        self._data = data
        self._stats = stats
        self._normalized = normalized

        layout = QVBoxLayout(self)

        # Large projection plot (always horizontal in expanded view)
        self._plot = ProjectionPlot("horizontal")
        self._plot.setMinimumHeight(250)
        self._plot.setMaximumHeight(500)
        if data is not None and stats is not None:
            self._plot.update_data(data, stats, normalized)
        layout.addWidget(self._plot)

        # Stats display
        if stats:
            stats_layout = QFormLayout()
            stats_layout.addRow("Mean:", QLabel(f"{stats.mean:.2f}"))
            stats_layout.addRow("Std Dev:", QLabel(f"{stats.std:.2f}"))
            stats_layout.addRow("Min:", QLabel(f"{stats.min_val:.2f}"))
            stats_layout.addRow("Max:", QLabel(f"{stats.max_val:.2f}"))
            stats_layout.addRow("Peak Position:", QLabel(f"{stats.peak_pos}"))
            if stats.fwhm is not None:
                stats_layout.addRow("FWHM:", QLabel(f"{stats.fwhm:.2f} px"))
                if stats.fwhm_left is not None and stats.fwhm_right is not None:
                    stats_layout.addRow(
                        "FWHM Range:",
                        QLabel(f"{stats.fwhm_left:.1f} - {stats.fwhm_right:.1f}"),
                    )
            layout.addLayout(stats_layout)

        # Export buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        export_csv_btn = QPushButton("Export CSV")
        export_csv_btn.clicked.connect(self._export_csv)
        btn_layout.addWidget(export_csv_btn)

        export_png_btn = QPushButton("Export PNG")
        export_png_btn.clicked.connect(self._export_png)
        btn_layout.addWidget(export_png_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _export_csv(self) -> None:
        """Export projection data to CSV."""
        if self._data is None:
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Projection Data", "", "CSV Files (*.csv)"
        )
        if path:
            np.savetxt(path, self._data, delimiter=",", header="intensity")

    def _export_png(self) -> None:
        """Export projection plot as PNG."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Projection Plot", "", "PNG Files (*.png)"
        )
        if path:
            pixmap = self._plot.grab()
            pixmap.save(path, "PNG")
