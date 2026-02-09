"""Spinnaker camera implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from .protocol import CameraProtocol

if TYPE_CHECKING:
    import numpy.typing as npt

# Spinnaker SDK import (may not be available)
try:
    import PySpin

    SPINNAKER_AVAILABLE = True
except ImportError:
    SPINNAKER_AVAILABLE = False
    PySpin = None


class SpinnakerCamera(CameraProtocol):
    """FLIR Spinnaker camera implementation."""

    def __init__(self, serial: str | None = None) -> None:
        if not SPINNAKER_AVAILABLE:
            raise ImportError(
                "Spinnaker SDK not installed. "
                "Download from https://www.flir.com/products/spinnaker-sdk/"
            )

        self._serial = serial
        self._system: PySpin.System | None = None
        self._camera: PySpin.Camera | None = None
        self._connected = False
        self._acquiring = False

    def connect(self) -> None:
        """Initialize Spinnaker system and connect to camera."""
        self._system = PySpin.System.GetInstance()
        cam_list = self._system.GetCameras()

        if cam_list.GetSize() == 0:
            cam_list.Clear()
            self._system.ReleaseInstance()
            raise RuntimeError("No cameras detected")

        # Find camera by serial or use first available
        if self._serial:
            for i in range(cam_list.GetSize()):
                cam = cam_list.GetByIndex(i)
                cam.Init()
                if cam.DeviceSerialNumber.GetValue() == self._serial:
                    self._camera = cam
                    break
                cam.DeInit()
            if self._camera is None:
                cam_list.Clear()
                raise RuntimeError(f"Camera with serial {self._serial} not found")
        else:
            self._camera = cam_list.GetByIndex(0)
            self._camera.Init()

        cam_list.Clear()
        self._connected = True
        print(
            f"[Spinnaker] Connected to camera: {self._camera.DeviceSerialNumber.GetValue()}"
        )

    def disconnect(self) -> None:
        """Release camera and system resources."""
        if self._acquiring:
            self.stop_acquisition()

        if self._camera is not None:
            self._camera.DeInit()
            del self._camera
            self._camera = None

        if self._system is not None:
            self._system.ReleaseInstance()
            self._system = None

        self._connected = False
        print("[Spinnaker] Disconnected")

    def start_acquisition(self) -> None:
        """Start continuous acquisition."""
        if self._camera is None:
            raise RuntimeError("Camera not connected")

        # Set acquisition mode to continuous
        self._camera.AcquisitionMode.SetValue(PySpin.AcquisitionMode_Continuous)
        self._camera.BeginAcquisition()
        self._acquiring = True
        print("[Spinnaker] Acquisition started")

    def stop_acquisition(self) -> None:
        """Stop acquisition."""
        if self._camera is not None and self._acquiring:
            self._camera.EndAcquisition()
            self._acquiring = False
            print("[Spinnaker] Acquisition stopped")

    def get_frame(self) -> npt.NDArray[np.uint8] | None:
        """Get next frame from camera."""
        if self._camera is None or not self._acquiring:
            return None

        try:
            image_result = self._camera.GetNextImage(1000)  # 1 second timeout

            if image_result.IsIncomplete():
                image_result.Release()
                return None

            # Convert to BGR for OpenCV compatibility
            image_converted = image_result.Convert(PySpin.PixelFormat_BGR8)
            frame: npt.NDArray[np.uint8] = image_converted.GetNDArray().copy()

            image_result.Release()
            return frame

        except PySpin.SpinnakerException:
            return None

    def set_exposure(self, exposure_us: int) -> None:
        """Set exposure time in microseconds."""
        if self._camera is None:
            return

        self._camera.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
        self._camera.ExposureTime.SetValue(float(exposure_us))
        print(f"[Spinnaker] Exposure set to {exposure_us} us")

    def set_gain(self, gain_db: float) -> None:
        """Set gain in dB."""
        if self._camera is None:
            return

        self._camera.GainAuto.SetValue(PySpin.GainAuto_Off)
        self._camera.Gain.SetValue(gain_db)
        print(f"[Spinnaker] Gain set to {gain_db} dB")

    def set_fps(self, fps: int) -> None:
        """Set acquisition frame rate."""
        if self._camera is None:
            return

        self._camera.AcquisitionFrameRateEnable.SetValue(True)
        self._camera.AcquisitionFrameRate.SetValue(float(fps))
        print(f"[Spinnaker] FPS set to {fps}")

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def is_acquiring(self) -> bool:
        return self._acquiring
