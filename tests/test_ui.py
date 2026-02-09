"""Tests for UI components using pytest-qt."""

import numpy as np
from pytestqt.qtbot import QtBot

from ui.controls import ControlPanel
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
