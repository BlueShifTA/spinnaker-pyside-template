from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class CameraConfig:
    """Camera configuration settings."""

    serial: str | None = None
    fps: int = 30
    exposure_us: int = 10000
    gain_db: float = 0.0


@dataclass(frozen=True)
class DisplayConfig:
    """Display configuration settings."""

    width: int = 1280
    height: int = 720


@dataclass(frozen=True)
class AppConfig:
    """Application configuration loaded from environment."""

    camera: CameraConfig
    display: DisplayConfig
    mock_camera: bool = False

    @classmethod
    def from_env(cls) -> AppConfig:
        """Load configuration from environment variables."""
        return cls(
            camera=CameraConfig(
                serial=os.getenv("CAMERA_SERIAL") or None,
                fps=int(os.getenv("CAMERA_FPS", "30")),
                exposure_us=int(os.getenv("CAMERA_EXPOSURE_US", "10000")),
                gain_db=float(os.getenv("CAMERA_GAIN_DB", "0")),
            ),
            display=DisplayConfig(
                width=int(os.getenv("DISPLAY_WIDTH", "1280")),
                height=int(os.getenv("DISPLAY_HEIGHT", "720")),
            ),
            mock_camera=os.getenv("MOCK_CAMERA", "0") == "1",
        )


config = AppConfig.from_env()
