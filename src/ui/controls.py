"""Camera control panel widget.

Provides controls for:
- Camera connection and settings (exposure, gain, fps)
- Overlay settings (grid, crosshair)
- Projection settings
- Image export
- Window controls (fullscreen, hide panel)
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class ControlPanel(QWidget):
    """Widget with camera controls and settings.

    Emits signals when controls change so the main window can react.
    """

    # Camera control signals
    start_clicked = Signal()
    stop_clicked = Signal()
    exposure_changed = Signal(int)
    gain_changed = Signal(float)
    fps_changed = Signal(int)

    # Overlay signals
    show_grid_changed = Signal(bool)
    show_crosshair_changed = Signal(bool)
    grid_spacing_changed = Signal(int)
    crosshair_size_changed = Signal(int)
    crosshair_extend_changed = Signal(bool)
    crosshair_width_changed = Signal(int)

    # Projection signals
    show_x_projection_changed = Signal(bool)
    show_y_projection_changed = Signal(bool)
    x_projection_mode_changed = Signal(str)
    y_projection_mode_changed = Signal(str)
    x_projection_normalize_changed = Signal(bool)
    y_projection_normalize_changed = Signal(bool)

    # Export signals
    export_image_clicked = Signal()

    # Window signals
    fullscreen_clicked = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setFixedWidth(300)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Connection controls
        conn_group = QGroupBox("Connection")
        conn_layout = QHBoxLayout(conn_group)

        self._start_btn = QPushButton("Start")
        self._start_btn.setStyleSheet("background-color: #22c55e; color: black;")
        self._start_btn.clicked.connect(self.start_clicked.emit)

        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setStyleSheet("background-color: #ef4444;")
        self._stop_btn.clicked.connect(self.stop_clicked.emit)
        self._stop_btn.setEnabled(False)

        conn_layout.addWidget(self._start_btn)
        conn_layout.addWidget(self._stop_btn)
        layout.addWidget(conn_group)

        # Camera settings
        settings_group = QGroupBox("Camera Settings")
        settings_layout = QFormLayout(settings_group)

        self._exposure_spin = QSpinBox()
        self._exposure_spin.setRange(100, 1000000)
        self._exposure_spin.setValue(10000)
        self._exposure_spin.setSuffix(" µs")
        self._exposure_spin.valueChanged.connect(self.exposure_changed.emit)
        settings_layout.addRow("Exposure:", self._exposure_spin)

        self._gain_spin = QDoubleSpinBox()
        self._gain_spin.setRange(0, 48)
        self._gain_spin.setValue(0)
        self._gain_spin.setSuffix(" dB")
        self._gain_spin.valueChanged.connect(lambda v: self.gain_changed.emit(float(v)))
        settings_layout.addRow("Gain:", self._gain_spin)

        self._fps_spin = QSpinBox()
        self._fps_spin.setRange(1, 120)
        self._fps_spin.setValue(30)
        self._fps_spin.setSuffix(" fps")
        self._fps_spin.valueChanged.connect(self.fps_changed.emit)
        settings_layout.addRow("Frame Rate:", self._fps_spin)

        layout.addWidget(settings_group)

        # Overlay settings
        overlay_group = QGroupBox("Overlay")
        overlay_layout = QFormLayout(overlay_group)

        self._crosshair_check = QCheckBox()
        self._crosshair_check.setChecked(True)
        self._crosshair_check.stateChanged.connect(
            lambda s: self.show_crosshair_changed.emit(s == 2)
        )
        overlay_layout.addRow("Crosshair:", self._crosshair_check)

        self._crosshair_extend_check = QCheckBox()
        self._crosshair_extend_check.setChecked(False)
        self._crosshair_extend_check.stateChanged.connect(
            lambda s: self.crosshair_extend_changed.emit(s == 2)
        )
        overlay_layout.addRow("Extend to Edge:", self._crosshair_extend_check)

        self._crosshair_size_spin = QSpinBox()
        self._crosshair_size_spin.setRange(10, 500)
        self._crosshair_size_spin.setValue(40)
        self._crosshair_size_spin.setSuffix(" px")
        self._crosshair_size_spin.valueChanged.connect(self.crosshair_size_changed.emit)
        overlay_layout.addRow("Crosshair Size:", self._crosshair_size_spin)

        self._crosshair_width_spin = QSpinBox()
        self._crosshair_width_spin.setRange(1, 10)
        self._crosshair_width_spin.setValue(2)
        self._crosshair_width_spin.setSuffix(" px")
        self._crosshair_width_spin.valueChanged.connect(
            self.crosshair_width_changed.emit
        )
        overlay_layout.addRow("Line Width:", self._crosshair_width_spin)

        self._grid_check = QCheckBox()
        self._grid_check.setChecked(False)
        self._grid_check.stateChanged.connect(
            lambda s: self.show_grid_changed.emit(s == 2)
        )
        overlay_layout.addRow("Grid:", self._grid_check)

        self._grid_spacing_spin = QSpinBox()
        self._grid_spacing_spin.setRange(10, 200)
        self._grid_spacing_spin.setValue(50)
        self._grid_spacing_spin.setSuffix(" px")
        self._grid_spacing_spin.valueChanged.connect(self.grid_spacing_changed.emit)
        overlay_layout.addRow("Grid Spacing:", self._grid_spacing_spin)

        layout.addWidget(overlay_group)

        # Projection settings
        projection_group = QGroupBox("Projections")
        projection_layout = QFormLayout(projection_group)

        self._x_projection_check = QCheckBox()
        self._x_projection_check.setChecked(False)
        self._x_projection_check.stateChanged.connect(
            lambda s: self.show_x_projection_changed.emit(s == 2)
        )
        projection_layout.addRow("X Projection:", self._x_projection_check)

        self._y_projection_check = QCheckBox()
        self._y_projection_check.setChecked(False)
        self._y_projection_check.stateChanged.connect(
            lambda s: self.show_y_projection_changed.emit(s == 2)
        )
        projection_layout.addRow("Y Projection:", self._y_projection_check)

        layout.addWidget(projection_group)

        # Stats display
        stats_group = QGroupBox("Statistics")
        stats_layout = QFormLayout(stats_group)

        self._fps_label = QPushButton("-- fps")
        self._fps_label.setFlat(True)
        self._fps_label.setEnabled(False)
        stats_layout.addRow("Actual FPS:", self._fps_label)

        self._frame_label = QPushButton("0")
        self._frame_label.setFlat(True)
        self._frame_label.setEnabled(False)
        stats_layout.addRow("Frames:", self._frame_label)

        layout.addWidget(stats_group)

        # Action buttons
        btn_layout = QHBoxLayout()

        self._export_btn = QPushButton("📥 Export Image")
        self._export_btn.setStyleSheet("padding: 6px;")
        self._export_btn.clicked.connect(self.export_image_clicked.emit)
        btn_layout.addWidget(self._export_btn)

        self._fullscreen_btn = QPushButton("⛶ Fullscreen")
        self._fullscreen_btn.setStyleSheet("padding: 6px;")
        self._fullscreen_btn.clicked.connect(self.fullscreen_clicked.emit)
        btn_layout.addWidget(self._fullscreen_btn)

        layout.addLayout(btn_layout)
        layout.addStretch()

    def set_running(self, running: bool) -> None:
        """Update UI state based on acquisition status."""
        self._start_btn.setEnabled(not running)
        self._stop_btn.setEnabled(running)

    def update_stats(self, fps: float, frame_count: int) -> None:
        """Update statistics display."""
        self._fps_label.setText(f"{fps:.1f} fps")
        self._frame_label.setText(str(frame_count))

    @property
    def exposure(self) -> int:
        return self._exposure_spin.value()

    @property
    def gain(self) -> float:
        return self._gain_spin.value()

    @property
    def fps(self) -> int:
        return self._fps_spin.value()

    @property
    def show_crosshair(self) -> bool:
        return self._crosshair_check.isChecked()

    @property
    def crosshair_extend(self) -> bool:
        return self._crosshair_extend_check.isChecked()

    @property
    def crosshair_width(self) -> int:
        return self._crosshair_width_spin.value()

    @property
    def show_grid(self) -> bool:
        return self._grid_check.isChecked()

    @property
    def show_x_projection(self) -> bool:
        return self._x_projection_check.isChecked()

    @property
    def show_y_projection(self) -> bool:
        return self._y_projection_check.isChecked()
