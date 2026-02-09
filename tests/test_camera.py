"""Tests for mock camera."""

import numpy as np

from camera.mock import MockCamera


def test_mock_camera_connect() -> None:
    camera = MockCamera()
    assert not camera.is_connected

    camera.connect()
    assert camera.is_connected

    camera.disconnect()
    assert not camera.is_connected


def test_mock_camera_acquisition() -> None:
    camera = MockCamera(width=640, height=480)
    camera.connect()

    assert not camera.is_acquiring
    camera.start_acquisition()
    assert camera.is_acquiring

    frame = camera.get_frame()
    assert frame is not None
    assert isinstance(frame, np.ndarray)
    assert frame.shape == (480, 640, 3)
    assert frame.dtype == np.uint8

    camera.stop_acquisition()
    assert not camera.is_acquiring

    camera.disconnect()


def test_mock_camera_settings() -> None:
    camera = MockCamera()
    camera.connect()

    camera.set_exposure(20000)
    camera.set_gain(5.0)
    camera.set_fps(60)

    camera.disconnect()
