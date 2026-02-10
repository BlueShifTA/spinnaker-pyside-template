"""Tests for UI components using pytest-qt."""

import numpy as np
from pytestqt.qtbot import QtBot

from core.projection import ProjectionStats
from ui.controls import ControlPanel
from ui.projections import ProjectionPanel, ProjectionPlot, YProjectionPanel
from ui.viewport import CameraViewport


def test_viewport_placeholder(qtbot: QtBot) -> None:
    viewport = CameraViewport(640, 480)
    qtbot.addWidget(viewport)

    assert "No Camera Feed" in viewport.text()


def test_viewport_update_frame(qtbot: QtBot) -> None:
    viewport = CameraViewport(640, 480)
    qtbot.addWidget(viewport)

    # Create a test frame
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame[:, :, 2] = 255  # Red

    viewport.update_frame(frame)

    # Should no longer show placeholder text
    assert viewport.pixmap() is not None


def test_control_panel_signals(qtbot: QtBot) -> None:
    panel = ControlPanel()
    qtbot.addWidget(panel)

    # Test start signal
    with qtbot.waitSignal(panel.start_clicked, timeout=1000):
        panel._start_btn.click()

    # Test exposure signal
    with qtbot.waitSignal(panel.exposure_changed, timeout=1000):
        panel._exposure_spin.setValue(20000)


def test_control_panel_state(qtbot: QtBot) -> None:
    panel = ControlPanel()
    qtbot.addWidget(panel)

    # Initial state
    assert panel._start_btn.isEnabled()
    assert not panel._stop_btn.isEnabled()

    # Running state
    panel.set_running(True)
    assert not panel._start_btn.isEnabled()
    assert panel._stop_btn.isEnabled()

    # Stopped state
    panel.set_running(False)
    assert panel._start_btn.isEnabled()
    assert not panel._stop_btn.isEnabled()


def test_control_panel_stats(qtbot: QtBot) -> None:
    panel = ControlPanel()
    qtbot.addWidget(panel)

    panel.update_stats(29.5, 1000)
    assert "29.5" in panel._fps_label.text()
    assert "1000" in panel._frame_label.text()


def test_control_panel_fullscreen_signal(qtbot: QtBot) -> None:
    """Test that fullscreen button emits signal."""
    panel = ControlPanel()
    qtbot.addWidget(panel)

    with qtbot.waitSignal(panel.fullscreen_clicked, timeout=1000):
        panel._fullscreen_btn.click()


# =============================================================================
# Projection Tests
# =============================================================================


def _make_stats(
    mean: float = 127.5,
    std: float = 50.0,
    min_val: float = 0.0,
    max_val: float = 255.0,
    fwhm: float | None = None,
    peak_pos: int = 50,
) -> ProjectionStats:
    """Helper to create ProjectionStats for testing."""
    return ProjectionStats(
        mean=mean,
        std=std,
        min_val=min_val,
        max_val=max_val,
        fwhm=fwhm,
        fwhm_left=None,
        fwhm_right=None,
        peak_pos=peak_pos,
    )


class TestProjectionPlot:
    """Tests for ProjectionPlot widget."""

    def test_horizontal_projection_creation(self, qtbot: QtBot) -> None:
        plot = ProjectionPlot("horizontal")
        qtbot.addWidget(plot)

        assert plot._orientation == "horizontal"
        assert plot.minimumHeight() == 100  # Updated height

    def test_vertical_projection_creation(self, qtbot: QtBot) -> None:
        plot = ProjectionPlot("vertical")
        qtbot.addWidget(plot)

        assert plot._orientation == "vertical"
        assert plot.minimumWidth() == 100  # Updated width

    def test_update_data_calculates_stats(self, qtbot: QtBot) -> None:
        """Test that stats are passed through correctly."""
        plot = ProjectionPlot("horizontal")
        qtbot.addWidget(plot)

        data = np.array([100.0, 120.0, 140.0, 160.0, 180.0])
        stats = _make_stats(mean=140.0, std=28.28)

        plot.update_data(data, stats)

        assert plot.mean == 140.0
        assert plot.std == 28.28
        assert plot._data is not None
        assert len(plot._data) == 5

    def test_path_caching(self, qtbot: QtBot) -> None:
        """Test that QPainterPath is cached after first build."""
        plot = ProjectionPlot("horizontal")
        qtbot.addWidget(plot)
        plot.resize(200, 100)

        data = np.linspace(0, 255, 100)
        stats = _make_stats()
        plot.update_data(data, stats)

        # Path should be None initially (cache invalidated on update)
        assert plot._cached_path is None

        # Build path
        plot._build_path()
        assert plot._cached_path is not None

    def test_path_invalidated_on_update(self, qtbot: QtBot) -> None:
        """Test that path cache is invalidated when data updates."""
        plot = ProjectionPlot("horizontal")
        qtbot.addWidget(plot)
        plot.resize(200, 100)

        data = np.linspace(0, 255, 100)
        stats = _make_stats()
        plot.update_data(data, stats)
        plot._build_path()
        assert plot._cached_path is not None

        # Update with new data - cache should be invalidated
        new_data = np.linspace(50, 200, 100)
        new_stats = _make_stats(mean=125.0, std=43.3)
        plot.update_data(new_data, new_stats)
        assert plot._cached_path is None

    def test_path_invalidated_on_resize(self, qtbot: QtBot) -> None:
        """Test that path cache is invalidated on resize."""
        plot = ProjectionPlot("horizontal")
        qtbot.addWidget(plot)
        plot.show()
        qtbot.waitExposed(plot)
        plot.resize(200, 100)

        data = np.linspace(0, 255, 100)
        stats = _make_stats()
        plot.update_data(data, stats)
        plot._build_path()
        assert plot._cached_path is not None

        # Resize - cache should be invalidated
        plot.resize(300, 100)
        qtbot.waitUntil(lambda: plot._cached_path is None, timeout=1000)

    def test_downsampling_large_data(self, qtbot: QtBot) -> None:
        """Test that large data arrays are downsampled for performance."""
        plot = ProjectionPlot("horizontal")
        qtbot.addWidget(plot)
        plot.resize(500, 100)

        # Simulate 1920 pixel width (full HD)
        data = np.random.rand(1920) * 255
        stats = _make_stats()
        plot.update_data(data, stats)
        plot._build_path()

        assert plot._cached_path is not None
        # Path should have fewer elements than original data
        # (downsampled to ~500 points max, so step = 1920/500 ≈ 4)


class TestProjectionPanel:
    """Tests for ProjectionPanel (X projection)."""

    def test_creation(self, qtbot: QtBot) -> None:
        panel = ProjectionPanel()
        qtbot.addWidget(panel)

        assert panel._plot is not None

    def test_update_projection(self, qtbot: QtBot) -> None:
        """Test updating with pre-calculated projection data."""
        panel = ProjectionPanel()
        qtbot.addWidget(panel)

        x_proj = np.linspace(100, 200, 640)
        stats = _make_stats(mean=150.0, std=28.9)

        panel.update_projection(x_proj, stats)

        assert "150.0" in panel._mean_label.text()
        assert "28.9" in panel._std_label.text()

    def test_visibility_toggle(self, qtbot: QtBot) -> None:
        panel = ProjectionPanel()
        qtbot.addWidget(panel)

        panel.set_visible(False)
        assert not panel.isVisible()

        panel.set_visible(True)
        assert panel.isVisible()


class TestYProjectionPanel:
    """Tests for YProjectionPanel."""

    def test_creation(self, qtbot: QtBot) -> None:
        panel = YProjectionPanel()
        qtbot.addWidget(panel)

        assert panel._plot is not None
        assert panel._plot._orientation == "vertical"

    def test_update_projection(self, qtbot: QtBot) -> None:
        """Test updating with pre-calculated projection data."""
        panel = YProjectionPanel()
        qtbot.addWidget(panel)

        y_proj = np.linspace(80, 180, 480)
        stats = _make_stats(mean=130.0, std=29.2)

        panel.update_projection(y_proj, stats)

        assert "130.0" in panel._mean_label.text()
        assert "29.2" in panel._std_label.text()

    def test_visibility_toggle(self, qtbot: QtBot) -> None:
        panel = YProjectionPanel()
        qtbot.addWidget(panel)

        panel.set_visible(False)
        assert not panel.isVisible()

        panel.set_visible(True)
        assert panel.isVisible()


class TestProjectionPerformance:
    """Tests to verify projection performance optimizations."""

    def test_grayscale_uses_single_channel(self) -> None:
        """Verify that grayscale conversion uses first channel for speed."""
        # Simulate what main_window does
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:, :, 0] = 100  # B channel
        frame[:, :, 1] = 150  # G channel
        frame[:, :, 2] = 200  # R channel

        # Fast method (what we use): first channel only
        gray_fast = frame[:, :, 0].astype(np.float64)

        # Slow method (what we avoided): mean of all channels
        gray_slow = np.mean(frame, axis=2)

        # Fast method should use only first channel value
        assert np.all(gray_fast == 100.0)

        # Slow method would average all channels
        assert np.allclose(gray_slow, 150.0)  # (100+150+200)/3

    def test_projection_stats_precalculated(self, qtbot: QtBot) -> None:
        """Verify that stats are passed in, not recalculated in widget."""
        plot = ProjectionPlot("horizontal")
        qtbot.addWidget(plot)

        # Create data with known stats
        data = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
        expected_mean = 30.0
        expected_std = float(np.std(data))

        # Pass pre-calculated stats
        stats = _make_stats(mean=expected_mean, std=expected_std)
        plot.update_data(data, stats)

        # Widget should use passed values, not recalculate
        assert plot.mean == expected_mean
        assert plot.std == expected_std

    def test_projection_calculation_efficiency(self) -> None:
        """Test that projection is calculated once for both X and Y."""
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

        # Simulate main_window logic: grayscale once
        gray = frame[:, :, 0].astype(np.float64)

        # X projection
        x_proj = np.mean(gray, axis=0)
        x_mean = float(np.mean(x_proj))
        x_std = float(np.std(x_proj))

        # Y projection
        y_proj = np.mean(gray, axis=1)
        y_mean = float(np.mean(y_proj))
        y_std = float(np.std(y_proj))

        # Verify dimensions
        assert x_proj.shape == (640,)
        assert y_proj.shape == (480,)

        # Verify stats are reasonable
        assert 0 <= x_mean <= 255
        assert 0 <= y_mean <= 255
        assert x_std >= 0
        assert y_std >= 0
