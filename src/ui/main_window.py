"""Main application window."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from PySide6.QtCore import QThread, QTimer, Signal
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QVBoxLayout, QWidget

from camera.mock import MockCamera
from camera.spinnaker import SPINNAKER_AVAILABLE, SpinnakerCamera
from core.config import config
from ui.controls import ControlPanel
from ui.projections import ProjectionPanel, YProjectionPanel
from ui.viewport import CameraViewport

if TYPE_CHECKING:
    from camera.protocol import CameraProtocol


class AcquisitionThread(QThread):
    """Background thread for camera acquisition."""

    frame_ready = Signal(object)  # numpy array
    error = Signal(str)

    def __init__(self, camera: CameraProtocol) -> None:
        super().__init__()
        self._camera = camera
        self._running = False

    def run(self) -> None:
        self._running = True
        while self._running:
            try:
                frame = self._camera.get_frame()
                if frame is not None:
                    self.frame_ready.emit(frame)
            except Exception as e:
                self.error.emit(str(e))
                break

    def stop(self) -> None:
        self._running = False
        self.wait()


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Camera Analysis QC")
        self.setMinimumSize(1024, 768)

        self._camera: CameraProtocol | None = None
        self._thread: AcquisitionThread | None = None
        self._frame_count = 0
        self._last_fps_time = time.time()
        self._fps = 0.0

        self._setup_ui()
        self._setup_camera()
        self._connect_signals()

        # FPS update timer
        self._stats_timer = QTimer()
        self._stats_timer.timeout.connect(self._update_stats)
        self._stats_timer.start(500)

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Left side: viewport + projections
        view_layout = QVBoxLayout()
        view_layout.setSpacing(5)

        # Viewport row with Y projection
        viewport_row = QHBoxLayout()
        viewport_row.setSpacing(5)

        # Y projection (left of viewport)
        self._y_projection = YProjectionPanel()
        self._y_projection.setVisible(False)
        viewport_row.addWidget(self._y_projection)

        # Camera viewport
        self._viewport = CameraViewport(
            config.display.width,
            config.display.height,
        )
        viewport_row.addWidget(self._viewport, stretch=1)

        view_layout.addLayout(viewport_row, stretch=1)

        # X projection (below viewport)
        self._x_projection = ProjectionPanel()
        self._x_projection.setVisible(False)
        view_layout.addWidget(self._x_projection)

        main_layout.addLayout(view_layout, stretch=1)

        # Control panel (right side)
        self._controls = ControlPanel()
        main_layout.addWidget(self._controls)

    def _connect_signals(self) -> None:
        """Connect control panel signals."""
        # Camera controls
        self._controls.start_clicked.connect(self._start_acquisition)
        self._controls.stop_clicked.connect(self._stop_acquisition)
        self._controls.exposure_changed.connect(self._on_exposure_changed)
        self._controls.gain_changed.connect(self._on_gain_changed)
        self._controls.fps_changed.connect(self._on_fps_changed)

        # Overlay controls
        self._controls.show_grid_changed.connect(self._viewport.set_show_grid)
        self._controls.show_crosshair_changed.connect(self._viewport.set_show_crosshair)
        self._controls.grid_spacing_changed.connect(self._viewport.set_grid_spacing)
        self._controls.crosshair_size_changed.connect(self._viewport.set_crosshair_size)

        # Projection controls
        self._controls.show_x_projection_changed.connect(self._x_projection.set_visible)
        self._controls.show_y_projection_changed.connect(self._y_projection.set_visible)

    def _setup_camera(self) -> None:
        """Initialize camera based on config."""
        if config.mock_camera or not SPINNAKER_AVAILABLE:
            print("Using mock camera")
            self._camera = MockCamera(
                width=config.display.width,
                height=config.display.height,
            )
        else:
            print("Using Spinnaker camera")
            self._camera = SpinnakerCamera(serial=config.camera.serial)

    def _start_acquisition(self) -> None:
        """Start camera acquisition."""
        if self._camera is None:
            return

        try:
            self._camera.connect()
            self._camera.set_exposure(self._controls.exposure)
            self._camera.set_gain(self._controls.gain)
            self._camera.set_fps(self._controls.fps)
            self._camera.start_acquisition()

            self._frame_count = 0
            self._last_fps_time = time.time()

            self._thread = AcquisitionThread(self._camera)
            self._thread.frame_ready.connect(self._on_frame)
            self._thread.error.connect(self._on_error)
            self._thread.start()

            self._controls.set_running(True)
        except Exception as e:
            print(f"Failed to start: {e}")

    def _stop_acquisition(self) -> None:
        """Stop camera acquisition."""
        if self._thread is not None:
            self._thread.stop()
            self._thread = None

        if self._camera is not None:
            self._camera.stop_acquisition()
            self._camera.disconnect()

        self._controls.set_running(False)

    def _on_frame(self, frame: object) -> None:
        """Handle new frame from camera."""
        import numpy as np

        if isinstance(frame, np.ndarray):
            self._viewport.update_frame(frame)
            self._frame_count += 1

            # Update projections if visible
            if self._controls.show_x_projection:
                self._x_projection.update_from_frame(frame)
            if self._controls.show_y_projection:
                self._y_projection.update_from_frame(frame)

    def _on_error(self, message: str) -> None:
        """Handle acquisition error."""
        print(f"Acquisition error: {message}")
        self._stop_acquisition()

    def _on_exposure_changed(self, value: int) -> None:
        if self._camera and self._camera.is_connected:
            self._camera.set_exposure(value)

    def _on_gain_changed(self, value: float) -> None:
        if self._camera and self._camera.is_connected:
            self._camera.set_gain(value)

    def _on_fps_changed(self, value: int) -> None:
        if self._camera and self._camera.is_connected:
            self._camera.set_fps(value)

    def _update_stats(self) -> None:
        """Update FPS statistics."""
        now = time.time()
        elapsed = now - self._last_fps_time
        if elapsed > 0:
            self._fps = self._frame_count / elapsed

        self._controls.update_stats(self._fps, self._frame_count)
        self._frame_count = 0
        self._last_fps_time = now

    def closeEvent(self, event: object) -> None:
        """Clean up on window close."""
        self._stop_acquisition()
        super().closeEvent(event)  # type: ignore[arg-type]
