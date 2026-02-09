"""Main application window."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from PySide6.QtCore import QThread, QTimer, Signal
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QWidget

from camera.mock import MockCamera
from camera.spinnaker import SPINNAKER_AVAILABLE, SpinnakerCamera
from core.config import config
from ui.controls import ControlPanel
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
        self.setWindowTitle("Spinnaker Camera Viewer")
        self.setMinimumSize(1024, 768)

        self._camera: CameraProtocol | None = None
        self._thread: AcquisitionThread | None = None
        self._frame_count = 0
        self._last_fps_time = time.time()
        self._fps = 0.0

        self._setup_ui()
        self._setup_camera()

        # FPS update timer
        self._stats_timer = QTimer()
        self._stats_timer.timeout.connect(self._update_stats)
        self._stats_timer.start(500)

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Camera viewport
        self._viewport = CameraViewport(
            config.display.width,
            config.display.height,
        )
        layout.addWidget(self._viewport, stretch=1)

        # Control panel
        self._controls = ControlPanel()
        self._controls.start_clicked.connect(self._start_acquisition)
        self._controls.stop_clicked.connect(self._stop_acquisition)
        self._controls.exposure_changed.connect(self._on_exposure_changed)
        self._controls.gain_changed.connect(self._on_gain_changed)
        self._controls.fps_changed.connect(self._on_fps_changed)
        layout.addWidget(self._controls)

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
