from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    import numpy.typing as npt


class CameraProtocol(ABC):
    """Abstract camera interface for acquisition."""

    @abstractmethod
    def connect(self) -> None:
        """Initialize and connect to the camera."""

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect and release camera resources."""

    @abstractmethod
    def start_acquisition(self) -> None:
        """Start continuous image acquisition."""

    @abstractmethod
    def stop_acquisition(self) -> None:
        """Stop image acquisition."""

    @abstractmethod
    def get_frame(self) -> npt.NDArray[np.uint8] | None:
        """Get the next available frame. Returns None if no frame available."""

    @abstractmethod
    def set_exposure(self, exposure_us: int) -> None:
        """Set exposure time in microseconds."""

    @abstractmethod
    def set_gain(self, gain_db: float) -> None:
        """Set gain in dB."""

    @abstractmethod
    def set_fps(self, fps: int) -> None:
        """Set target frame rate."""

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if camera is connected."""

    @property
    @abstractmethod
    def is_acquiring(self) -> bool:
        """Check if camera is currently acquiring images."""
