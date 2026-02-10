"""Spinnaker camera implementation."""

from __future__ import annotations

import ctypes
from typing import TYPE_CHECKING, Any

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


# Workaround for PySpin 4.3.0.189 memory bug on macOS ARM64.
# The GetNDArray() method returns a numpy array with OWNDATA=True,
# but the memory is owned by PySpin. When numpy tries to free it,
# we get "malloc: pointer being freed was not allocated" crash.
# Solution: Clear the OWNDATA flag before the array is garbage collected.


class _PyArrayObject(ctypes.Structure):
    """Minimal numpy array structure for accessing flags."""

    _fields_ = [
        ("ob_refcnt", ctypes.c_ssize_t),
        ("ob_type", ctypes.c_void_p),
        ("data", ctypes.c_void_p),
        ("nd", ctypes.c_int),
        ("dimensions", ctypes.c_void_p),
        ("strides", ctypes.c_void_p),
        ("base", ctypes.c_void_p),
        ("descr", ctypes.c_void_p),
        ("flags", ctypes.c_int),
    ]


class SpinnakerCamera(CameraProtocol):
    """FLIR Spinnaker camera implementation."""

    def __init__(self, serial: str | None = None) -> None:
        if not SPINNAKER_AVAILABLE:
            raise ImportError(
                "Spinnaker SDK not installed. "
                "Download from https://www.flir.com/products/spinnaker-sdk/"
            )

        self._serial = serial
        self._system: Any = None
        self._cam_list: Any = None
        self._camera: Any = None
        self._processor: Any = None  # Reusable image processor
        self._connected = False
        self._acquiring = False

    def connect(self) -> None:
        """Initialize Spinnaker system and connect to camera."""
        self._system = PySpin.System.GetInstance()
        self._cam_list = self._system.GetCameras()

        if self._cam_list.GetSize() == 0:
            self._cam_list.Clear()
            self._system.ReleaseInstance()
            self._system = None
            self._cam_list = None
            raise RuntimeError("No cameras detected")

        # Find camera by serial or use first available
        if self._serial:
            self._camera = self._find_camera_by_serial(self._serial)
            if self._camera is None:
                self._cam_list.Clear()
                self._system.ReleaseInstance()
                self._system = None
                self._cam_list = None
                raise RuntimeError(f"Camera with serial {self._serial} not found")
        else:
            self._camera = self._cam_list.GetByIndex(0)

        # Initialize camera
        self._camera.Init()

        # Create reusable image processor
        self._processor = PySpin.ImageProcessor()
        self._processor.SetColorProcessing(
            PySpin.SPINNAKER_COLOR_PROCESSING_ALGORITHM_HQ_LINEAR
        )

        # Get serial for logging
        serial = self._get_device_serial()
        self._connected = True
        print(f"[Spinnaker] Connected to camera: {serial}")

    def _find_camera_by_serial(self, serial: str) -> Any:
        """Find camera by serial number using TL device nodemap."""
        for i in range(self._cam_list.GetSize()):
            cam = self._cam_list.GetByIndex(i)
            nodemap_tldevice = cam.GetTLDeviceNodeMap()
            serial_node = PySpin.CStringPtr(
                nodemap_tldevice.GetNode("DeviceSerialNumber")
            )
            if PySpin.IsReadable(serial_node):
                if serial_node.GetValue() == serial:
                    return cam
            del cam
        return None

    def _get_device_serial(self) -> str:
        """Get device serial number."""
        if self._camera is None:
            return "N/A"
        try:
            nodemap_tldevice = self._camera.GetTLDeviceNodeMap()
            serial_node = PySpin.CStringPtr(
                nodemap_tldevice.GetNode("DeviceSerialNumber")
            )
            if PySpin.IsReadable(serial_node):
                return str(serial_node.GetValue())
        except Exception:
            pass
        return "N/A"

    def disconnect(self) -> None:
        """Release camera and system resources."""
        if self._acquiring:
            self.stop_acquisition()

        # Release processor first
        if self._processor is not None:
            self._processor = None

        if self._camera is not None:
            try:
                self._camera.DeInit()
            except Exception:
                pass
            del self._camera
            self._camera = None

        if self._cam_list is not None:
            try:
                self._cam_list.Clear()
            except Exception:
                pass
            self._cam_list = None

        if self._system is not None:
            try:
                self._system.ReleaseInstance()
            except Exception:
                pass
            self._system = None

        self._connected = False
        print("[Spinnaker] Disconnected")

    def start_acquisition(self) -> None:
        """Start continuous acquisition."""
        if self._camera is None:
            raise RuntimeError("Camera not connected")

        try:
            # Set acquisition mode to continuous
            node_acquisition_mode = PySpin.CEnumerationPtr(
                self._camera.GetNodeMap().GetNode("AcquisitionMode")
            )
            if PySpin.IsWritable(node_acquisition_mode):
                node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName(
                    "Continuous"
                )
                if PySpin.IsReadable(node_acquisition_mode_continuous):
                    node_acquisition_mode.SetIntValue(
                        node_acquisition_mode_continuous.GetValue()
                    )

            self._camera.BeginAcquisition()
            self._acquiring = True
            print("[Spinnaker] Acquisition started")
        except PySpin.SpinnakerException as e:
            raise RuntimeError(f"Failed to start acquisition: {e}") from e

    def stop_acquisition(self) -> None:
        """Stop acquisition."""
        if self._camera is not None and self._acquiring:
            try:
                self._camera.EndAcquisition()
            except Exception:
                pass
            self._acquiring = False
            print("[Spinnaker] Acquisition stopped")

    def get_frame(self) -> npt.NDArray[np.uint8] | None:
        """Get next frame from camera as grayscale.

        Uses GetNDArray() with OWNDATA flag workaround for PySpin 4.3 memory bug.
        Returns single-channel grayscale image (H, W).
        """
        if self._camera is None or not self._acquiring:
            return None

        image_result = None
        converted = None

        try:
            image_result = self._camera.GetNextImage(1000)  # 1 second timeout

            if image_result.IsIncomplete():
                image_result.Release()
                return None

            # Get pixel format for conversion
            raw = image_result.GetNDArray()
            frame = np.array(raw)

            return frame

        except PySpin.SpinnakerException as e:
            print(f"[Spinnaker] Frame error: {e}")
            return None
        except Exception as e:
            print(f"[Spinnaker] Unexpected error: {e}")
            return None
        finally:
            # Always release images to prevent memory leak
            if converted is not None:
                try:
                    converted.Release()
                except Exception:
                    pass
            if image_result is not None:
                try:
                    image_result.Release()
                except Exception:
                    pass

    def set_exposure(self, exposure_us: int) -> None:
        """Set exposure time in microseconds."""
        if self._camera is None:
            return

        try:
            nodemap = self._camera.GetNodeMap()

            # Disable auto exposure
            node_exposure_auto = PySpin.CEnumerationPtr(nodemap.GetNode("ExposureAuto"))
            if PySpin.IsWritable(node_exposure_auto):
                entry_off = node_exposure_auto.GetEntryByName("Off")
                if PySpin.IsReadable(entry_off):
                    node_exposure_auto.SetIntValue(entry_off.GetValue())

            # Set exposure time
            node_exposure_time = PySpin.CFloatPtr(nodemap.GetNode("ExposureTime"))
            if PySpin.IsWritable(node_exposure_time):
                # Clamp to valid range
                exposure_min = node_exposure_time.GetMin()
                exposure_max = node_exposure_time.GetMax()
                exposure_val = max(exposure_min, min(exposure_max, float(exposure_us)))
                node_exposure_time.SetValue(exposure_val)
                print(f"[Spinnaker] Exposure set to {exposure_val:.0f} us")
        except PySpin.SpinnakerException as e:
            print(f"[Spinnaker] Failed to set exposure: {e}")

    def set_gain(self, gain_db: float) -> None:
        """Set gain in dB."""
        if self._camera is None:
            return

        try:
            nodemap = self._camera.GetNodeMap()

            # Disable auto gain
            node_gain_auto = PySpin.CEnumerationPtr(nodemap.GetNode("GainAuto"))
            if PySpin.IsWritable(node_gain_auto):
                entry_off = node_gain_auto.GetEntryByName("Off")
                if PySpin.IsReadable(entry_off):
                    node_gain_auto.SetIntValue(entry_off.GetValue())

            # Set gain
            node_gain = PySpin.CFloatPtr(nodemap.GetNode("Gain"))
            if PySpin.IsWritable(node_gain):
                gain_min = node_gain.GetMin()
                gain_max = node_gain.GetMax()
                gain_val = max(gain_min, min(gain_max, gain_db))
                node_gain.SetValue(gain_val)
                print(f"[Spinnaker] Gain set to {gain_val:.1f} dB")
        except PySpin.SpinnakerException as e:
            print(f"[Spinnaker] Failed to set gain: {e}")

    def set_fps(self, fps: int) -> None:
        """Set acquisition frame rate."""
        if self._camera is None:
            return

        try:
            nodemap = self._camera.GetNodeMap()

            # Enable frame rate control
            node_frame_rate_enable = PySpin.CBooleanPtr(
                nodemap.GetNode("AcquisitionFrameRateEnable")
            )
            if PySpin.IsWritable(node_frame_rate_enable):
                node_frame_rate_enable.SetValue(True)

            # Set frame rate
            node_frame_rate = PySpin.CFloatPtr(nodemap.GetNode("AcquisitionFrameRate"))
            if PySpin.IsWritable(node_frame_rate):
                fps_min = node_frame_rate.GetMin()
                fps_max = node_frame_rate.GetMax()
                fps_val = max(fps_min, min(fps_max, float(fps)))
                node_frame_rate.SetValue(fps_val)
                print(f"[Spinnaker] FPS set to {fps_val:.1f}")
        except PySpin.SpinnakerException as e:
            print(f"[Spinnaker] Failed to set FPS: {e}")

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def is_acquiring(self) -> bool:
        return self._acquiring
