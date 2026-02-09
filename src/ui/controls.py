"""Camera control panel widget."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
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
    """Widget with camera controls."""

    # Signals emitted when controls change
    start_clicked = Signal()
    stop_clicked = Signal()
    exposure_changed = Signal(int)
    gain_changed = Signal(float)
    fps_changed = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self.setFixedWidth(280)
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
