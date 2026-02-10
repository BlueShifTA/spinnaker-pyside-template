"""Main application window.

Provides the main UI for camera QC application including:
- Camera viewport with overlays
- X and Y projection panels
- Control panel with settings
- Image export capabilities
- Hideable control panel
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import numpy as np
from PySide6.QtCore import QThread, QTimer, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from camera.mock import MockCamera
from camera.spinnaker import SPINNAKER_AVAILABLE, SpinnakerCamera
from core.config import config
from core.projection import ProjectionAnalyzer, ProjectionMode
from ui.controls import ControlPanel
from ui.projections import ProjectionPanel, YProjectionPanel
from ui.viewport import CameraViewport

if TYPE_CHECKING:
    import numpy.typing as npt

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
    """Main application window for Camera Analysis QC."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Camera Analysis QC")
        self.setMinimumSize(1024, 768)

        self._camera: CameraProtocol | None = None
        self._thread: AcquisitionThread | None = None
        self._frame_count = 0
        self._last_fps_time = time.time()
        self._fps = 0.0
        self._current_frame: npt.NDArray[np.uint8] | None = None

        # Projection analyzers for X and Y
        self._x_analyzer = ProjectionAnalyzer(mode=ProjectionMode.AVERAGE)
        self._y_analyzer = ProjectionAnalyzer(mode=ProjectionMode.AVERAGE)

        self._setup_ui()
        self._setup_camera()
        self._connect_signals()
        self._setup_shortcuts()

        # FPS update timer
        self._stats_timer = QTimer()
        self._stats_timer.timeout.connect(self._update_stats)
        self._stats_timer.start(500)

    def _setup_ui(self) -> None:
        """Set up the main UI layout."""
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

        # Control panel in a scroll area (prevents overlap with camera view)
        self._controls = ControlPanel()

        scroll = QScrollArea()
        scroll.setWidget(self._controls)
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(320)
        scroll.setHorizontalScrollBarPolicy(
            scroll.horizontalScrollBarPolicy().ScrollBarAlwaysOff
        )
        scroll.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        self._controls_container = scroll
        main_layout.addWidget(self._controls_container)

        # Hide panel button (always visible at edge)
        self._hide_btn = QPushButton("◀")
        self._hide_btn.setFixedWidth(20)
        self._hide_btn.setToolTip("Hide/Show control panel (H)")
        self._hide_btn.clicked.connect(self._toggle_controls)
        main_layout.addWidget(self._hide_btn)

    def _connect_signals(self) -> None:
        """Connect control panel signals."""
        # Camera selection
        self._controls.camera_selected.connect(self._on_camera_selected)
        self._controls.refresh_cameras_clicked.connect(self._refresh_cameras)

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
        self._controls.crosshair_extend_changed.connect(
            self._viewport.set_crosshair_extend
        )
        self._controls.crosshair_width_changed.connect(
            self._viewport.set_crosshair_width
        )

        # Projection controls
        self._controls.show_x_projection_changed.connect(self._x_projection.set_visible)
        self._controls.show_y_projection_changed.connect(self._y_projection.set_visible)

        # Projection panel settings
        self._x_projection.mode_changed.connect(self._on_x_mode_changed)
        self._x_projection.normalize_changed.connect(self._on_x_normalize_changed)
        self._y_projection.mode_changed.connect(self._on_y_mode_changed)
        self._y_projection.normalize_changed.connect(self._on_y_normalize_changed)

        # Export
        self._controls.export_image_clicked.connect(self._export_image)

        # Window controls
        self._controls.fullscreen_clicked.connect(self._toggle_fullscreen)

    def _setup_shortcuts(self) -> None:
        """Set up keyboard shortcuts."""
        # H to hide/show controls
        hide_shortcut = QShortcut(QKeySequence("H"), self)
        hide_shortcut.activated.connect(self._toggle_controls)

        # F for fullscreen
        fullscreen_shortcut = QShortcut(QKeySequence("F"), self)
        fullscreen_shortcut.activated.connect(self._toggle_fullscreen)

        # Escape to exit fullscreen
        escape_shortcut = QShortcut(QKeySequence("Escape"), self)
        escape_shortcut.activated.connect(self._exit_fullscreen)

    def _setup_camera(self) -> None:
        """Initialize camera discovery."""
        self._selected_serial: str | None = None

        if config.mock_camera or not SPINNAKER_AVAILABLE:
            if not SPINNAKER_AVAILABLE:
                print("⚠️  Spinnaker SDK not installed - using mock camera")
                print(
                    "   Download from: https://www.teledynevisionsolutions.com/support/support-center/software-firmware-downloads/iis/spinnaker-sdk-download/spinnaker-sdk--download-files/"
                )
            else:
                print("Using mock camera (mock mode enabled)")
            self._camera = MockCamera(
                width=config.display.width,
                height=config.display.height,
            )
            # Set mock camera in dropdown
            self._controls.set_cameras(
                [
                    {
                        "model": "Mock Camera",
                        "serial": "MOCK-001",
                        "vendor": "Simulator",
                    }
                ]
            )
        else:
            # Discover real cameras
            self._refresh_cameras()

    def _refresh_cameras(self) -> None:
        """Refresh the list of available cameras."""
        from camera.discover import discover_cameras

        cameras = discover_cameras()
        self._controls.set_cameras(cameras)

        if cameras:
            print(f"Found {len(cameras)} camera(s)")
            self._selected_serial = cameras[0]["serial"]
        else:
            print("No cameras detected")
            self._selected_serial = None

    def _on_camera_selected(self, serial: str) -> None:
        """Handle camera selection from dropdown."""
        self._selected_serial = serial
        print(f"Selected camera: {serial}")

    def _start_acquisition(self) -> None:
        """Start camera acquisition."""
        # Create camera instance with selected serial
        if config.mock_camera or not SPINNAKER_AVAILABLE:
            if self._camera is None:
                self._camera = MockCamera(
                    width=config.display.width,
                    height=config.display.height,
                )
        else:
            if self._selected_serial is None:
                print("No camera selected")
                return
            self._camera = SpinnakerCamera(serial=self._selected_serial)

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
        if not isinstance(frame, np.ndarray):
            return

        self._current_frame = frame
        self._viewport.update_frame(frame)
        self._frame_count += 1

        # Update projections if visible
        show_x = self._controls.show_x_projection
        show_y = self._controls.show_y_projection

        if show_x:
            data, stats = self._x_analyzer.analyze_x(frame)
            self._x_projection.update_projection(
                data, stats, self._x_analyzer.normalize
            )

        if show_y:
            data, stats = self._y_analyzer.analyze_y(frame)
            self._y_projection.update_projection(
                data, stats, self._y_analyzer.normalize
            )

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

    def _on_x_mode_changed(self, mode: str) -> None:
        """Handle X projection mode change."""
        mode_map = {
            "avg": ProjectionMode.AVERAGE,
            "sum": ProjectionMode.SUM,
            "min": ProjectionMode.MIN,
            "max": ProjectionMode.MAX,
        }
        self._x_analyzer.mode = mode_map.get(mode, ProjectionMode.AVERAGE)

    def _on_y_mode_changed(self, mode: str) -> None:
        """Handle Y projection mode change."""
        mode_map = {
            "avg": ProjectionMode.AVERAGE,
            "sum": ProjectionMode.SUM,
            "min": ProjectionMode.MIN,
            "max": ProjectionMode.MAX,
        }
        self._y_analyzer.mode = mode_map.get(mode, ProjectionMode.AVERAGE)

    def _on_x_normalize_changed(self, normalize: bool) -> None:
        """Handle X projection normalize toggle."""
        self._x_analyzer.normalize = normalize

    def _on_y_normalize_changed(self, normalize: bool) -> None:
        """Handle Y projection normalize toggle."""
        self._y_analyzer.normalize = normalize

    def _export_image(self) -> None:
        """Export current frame to file."""
        if self._current_frame is None:
            return

        path, filter_used = QFileDialog.getSaveFileName(
            self,
            "Export Image",
            "",
            "TIFF Files (*.tiff *.tif);;PNG Files (*.png);;All Files (*)",
        )

        if path:
            import cv2

            # Save raw frame (BGR or grayscale)
            cv2.imwrite(path, self._current_frame)
            print(f"Image saved to: {path}")

    def _toggle_controls(self) -> None:
        """Toggle control panel visibility."""
        visible = self._controls_container.isVisible()
        self._controls_container.setVisible(not visible)
        self._hide_btn.setText("▶" if visible else "◀")

    def _toggle_fullscreen(self) -> None:
        """Toggle fullscreen mode."""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _exit_fullscreen(self) -> None:
        """Exit fullscreen mode."""
        if self.isFullScreen():
            self.showNormal()

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
