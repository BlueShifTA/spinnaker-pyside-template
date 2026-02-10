"""Mock camera for development without hardware."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import numpy as np

from .protocol import CameraProtocol

if TYPE_CHECKING:
    import numpy.typing as npt


class MockCamera(CameraProtocol):
    """Mock camera that generates test patterns."""

    def __init__(self, width: int = 1280, height: int = 720) -> None:
        self._width = width
        self._height = height
        self._connected = False
        self._acquiring = False
        self._exposure_us = 10000
        self._gain_db = 0.0
        self._fps = 30
        self._frame_count = 0
        self._last_frame_time = 0.0

    def connect(self) -> None:
        self._connected = True
        print("[MockCamera] Connected")

    def disconnect(self) -> None:
        self.stop_acquisition()
        self._connected = False
        print("[MockCamera] Disconnected")

    def start_acquisition(self) -> None:
        if not self._connected:
            raise RuntimeError("Camera not connected")
        self._acquiring = True
        self._frame_count = 0
        self._last_frame_time = time.time()
        print("[MockCamera] Acquisition started")

    def stop_acquisition(self) -> None:
        self._acquiring = False
        print("[MockCamera] Acquisition stopped")

    def get_frame(self) -> npt.NDArray[np.uint8] | None:
        if not self._acquiring:
            return None

        # Rate limit to target FPS
        now = time.time()
        elapsed = now - self._last_frame_time
        target_interval = 1.0 / self._fps
        if elapsed < target_interval:
            time.sleep(target_interval - elapsed)

        self._last_frame_time = time.time()
        self._frame_count += 1

        # Generate grayscale test pattern with moving element
        frame = np.zeros((self._height, self._width), dtype=np.uint8)

        # Horizontal gradient
        gradient = np.linspace(0, 255, self._width, dtype=np.uint8)
        frame[:, :] = gradient  # Fill with horizontal gradient

        # Add vertical gradient component
        gradient_v = np.linspace(0, 128, self._height, dtype=np.uint8)
        frame = np.clip(
            frame.astype(np.int16) + gradient_v[:, np.newaxis] - 64, 0, 255
        ).astype(np.uint8)

        # Moving circle
        cx = int((self._frame_count * 5) % self._width)
        cy = self._height // 2
        y, x = np.ogrid[: self._height, : self._width]
        mask = (x - cx) ** 2 + (y - cy) ** 2 < 50**2
        frame[mask] = 255  # White circle

        # Apply simulated gain/exposure
        brightness = min(255, int(self._gain_db * 10 + self._exposure_us / 100))
        frame = np.clip(frame.astype(np.int16) + brightness - 100, 0, 255).astype(
            np.uint8
        )

        return frame

    def set_exposure(self, exposure_us: int) -> None:
        self._exposure_us = exposure_us
        print(f"[MockCamera] Exposure set to {exposure_us} us")

    def set_gain(self, gain_db: float) -> None:
        self._gain_db = gain_db
        print(f"[MockCamera] Gain set to {gain_db} dB")

    def set_fps(self, fps: int) -> None:
        self._fps = max(1, fps)
        print(f"[MockCamera] FPS set to {fps}")

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def is_acquiring(self) -> bool:
        return self._acquiring
