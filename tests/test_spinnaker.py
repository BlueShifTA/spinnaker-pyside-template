"""Tests for Spinnaker camera with real hardware.

Run with: pytest tests/test_spinnaker.py -v --run-hardware
Skip hardware tests by default.
"""

import numpy as np
import pytest

# Check if PySpin is available
try:
    import PySpin

    PYSPIN_AVAILABLE = True
except ImportError:
    PYSPIN_AVAILABLE = False


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "hardware: mark test as requiring real camera hardware"
    )


# Skip all tests in this file if PySpin not available or --run-hardware not passed
pytestmark = [
    pytest.mark.hardware,
    pytest.mark.skipif(not PYSPIN_AVAILABLE, reason="PySpin not installed"),
]


@pytest.fixture
def spinnaker_system():
    """Fixture to get Spinnaker system instance."""
    system = PySpin.System.GetInstance()
    yield system
    system.ReleaseInstance()


@pytest.fixture
def camera_list(spinnaker_system):
    """Fixture to get camera list."""
    cam_list = spinnaker_system.GetCameras()
    yield cam_list
    cam_list.Clear()


class TestSpinnakerSystemBasics:
    """Test basic Spinnaker system operations."""

    def test_get_system_instance(self) -> None:
        """Test getting system instance."""
        system = PySpin.System.GetInstance()
        assert system is not None

        version = system.GetLibraryVersion()
        print(
            f"Spinnaker version: {version.major}.{version.minor}.{version.type}.{version.build}"
        )

        system.ReleaseInstance()

    def test_get_camera_list(self, spinnaker_system) -> None:
        """Test getting camera list."""
        cam_list = spinnaker_system.GetCameras()
        num_cameras = cam_list.GetSize()
        print(f"Found {num_cameras} camera(s)")
        assert num_cameras >= 0
        cam_list.Clear()


class TestSpinnakerCameraDiscovery:
    """Test camera discovery without initialization."""

    def test_discover_cameras_tl_nodemap(self, camera_list) -> None:
        """Test reading camera info from TL device nodemap (no Init)."""
        if camera_list.GetSize() == 0:
            pytest.skip("No cameras connected")

        cam = camera_list.GetByIndex(0)

        # Get TL device nodemap (before Init)
        nodemap_tldevice = cam.GetTLDeviceNodeMap()

        # Read serial number
        serial_node = PySpin.CStringPtr(nodemap_tldevice.GetNode("DeviceSerialNumber"))
        assert PySpin.IsReadable(serial_node)
        serial = serial_node.GetValue()
        print(f"Serial: {serial}")
        assert len(serial) > 0

        # Read model name
        model_node = PySpin.CStringPtr(nodemap_tldevice.GetNode("DeviceModelName"))
        assert PySpin.IsReadable(model_node)
        model = model_node.GetValue()
        print(f"Model: {model}")

        # Release reference
        del cam


class TestSpinnakerCameraInit:
    """Test camera initialization and deinitialization."""

    def test_init_deinit_camera(self, camera_list) -> None:
        """Test initializing and deinitializing camera."""
        if camera_list.GetSize() == 0:
            pytest.skip("No cameras connected")

        cam = camera_list.GetByIndex(0)

        # Initialize
        cam.Init()
        assert cam.IsInitialized()

        # Deinitialize
        cam.DeInit()
        assert not cam.IsInitialized()

        del cam

    def test_read_nodemap_after_init(self, camera_list) -> None:
        """Test reading nodemap after initialization."""
        if camera_list.GetSize() == 0:
            pytest.skip("No cameras connected")

        cam = camera_list.GetByIndex(0)
        cam.Init()

        try:
            nodemap = cam.GetNodeMap()
            assert nodemap is not None

            # Read pixel format
            pixel_format_node = PySpin.CEnumerationPtr(nodemap.GetNode("PixelFormat"))
            if PySpin.IsReadable(pixel_format_node):
                current_format = pixel_format_node.GetCurrentEntry()
                print(f"Current pixel format: {current_format.GetSymbolic()}")
        finally:
            cam.DeInit()
            del cam


class TestSpinnakerImageProcessor:
    """Test ImageProcessor creation and usage."""

    def test_create_image_processor(self) -> None:
        """Test creating image processor."""
        processor = PySpin.ImageProcessor()
        assert processor is not None

        # Set color processing algorithm
        processor.SetColorProcessing(
            PySpin.SPINNAKER_COLOR_PROCESSING_ALGORITHM_HQ_LINEAR
        )

    def test_processor_lifecycle(self) -> None:
        """Test processor creation and deletion."""
        for _ in range(5):
            processor = PySpin.ImageProcessor()
            processor.SetColorProcessing(
                PySpin.SPINNAKER_COLOR_PROCESSING_ALGORITHM_HQ_LINEAR
            )
            del processor


class TestSpinnakerAcquisition:
    """Test image acquisition."""

    def test_single_frame_acquisition(self, camera_list) -> None:
        """Test acquiring a single frame."""
        if camera_list.GetSize() == 0:
            pytest.skip("No cameras connected")

        cam = camera_list.GetByIndex(0)
        cam.Init()

        try:
            # Set acquisition mode
            nodemap = cam.GetNodeMap()
            node_acquisition_mode = PySpin.CEnumerationPtr(
                nodemap.GetNode("AcquisitionMode")
            )
            if PySpin.IsWritable(node_acquisition_mode):
                entry = node_acquisition_mode.GetEntryByName("Continuous")
                if PySpin.IsReadable(entry):
                    node_acquisition_mode.SetIntValue(entry.GetValue())

            # Start acquisition
            cam.BeginAcquisition()

            # Get one frame
            image_result = cam.GetNextImage(2000)
            assert not image_result.IsIncomplete()

            width = image_result.GetWidth()
            height = image_result.GetHeight()
            print(f"Image size: {width}x{height}")
            assert width > 0
            assert height > 0

            image_result.Release()

            # Stop acquisition
            cam.EndAcquisition()

        finally:
            cam.DeInit()
            del cam

    def test_get_frame_with_getdata(self) -> None:
        """Test getting frame using GetData() instead of GetNDArray().

        This test does not use fixtures to ensure complete isolation.
        """
        system = PySpin.System.GetInstance()
        cam_list = system.GetCameras()

        if cam_list.GetSize() == 0:
            cam_list.Clear()
            system.ReleaseInstance()
            pytest.skip("No cameras connected")

        cam = cam_list.GetByIndex(0)
        cam.Init()

        try:
            # Set pixel format to Mono8 if possible
            nodemap = cam.GetNodeMap()
            pixel_format_node = PySpin.CEnumerationPtr(nodemap.GetNode("PixelFormat"))
            if PySpin.IsWritable(pixel_format_node):
                mono8_entry = pixel_format_node.GetEntryByName("Mono8")
                if mono8_entry is not None and PySpin.IsReadable(mono8_entry):
                    pixel_format_node.SetIntValue(mono8_entry.GetValue())
                    print("Set pixel format to Mono8")

            # Set acquisition mode
            node_acquisition_mode = PySpin.CEnumerationPtr(
                nodemap.GetNode("AcquisitionMode")
            )
            if PySpin.IsWritable(node_acquisition_mode):
                entry = node_acquisition_mode.GetEntryByName("Continuous")
                node_acquisition_mode.SetIntValue(entry.GetValue())

            cam.BeginAcquisition()

            image_result = cam.GetNextImage(2000)
            assert not image_result.IsIncomplete()

            # Get image dimensions
            width = image_result.GetWidth()
            height = image_result.GetHeight()
            pixel_format = image_result.GetPixelFormat()
            print(f"Image: {width}x{height}, format: {pixel_format}")

            # Create an empty numpy array and copy data into it
            frame = np.empty((height, width), dtype=np.uint8)
            # Get size and copy directly
            buffer_size = image_result.GetBufferSize()
            print(f"Buffer size: {buffer_size}, expected: {width * height}")

            # Use GetData() and manually copy
            src_data = image_result.GetData()
            np.copyto(
                frame,
                np.frombuffer(src_data, dtype=np.uint8, count=width * height).reshape(
                    (height, width)
                ),
            )

            print(f"Frame shape: {frame.shape}")

            # Release the image AFTER copying
            image_result.Release()

            cam.EndAcquisition()

            # Verify the copy is still valid after release
            assert frame.shape == (height, width)
            mean_val = np.mean(frame)
            print(f"Mean pixel value: {mean_val:.1f}")

        finally:
            cam.DeInit()
            del cam
            cam_list.Clear()
            system.ReleaseInstance()

    def test_multiple_frames_acquisition(self, camera_list) -> None:
        """Test acquiring multiple frames in a loop."""
        if camera_list.GetSize() == 0:
            pytest.skip("No cameras connected")

        cam = camera_list.GetByIndex(0)
        cam.Init()

        try:
            nodemap = cam.GetNodeMap()

            # Set acquisition mode
            node_acquisition_mode = PySpin.CEnumerationPtr(
                nodemap.GetNode("AcquisitionMode")
            )
            if PySpin.IsWritable(node_acquisition_mode):
                entry = node_acquisition_mode.GetEntryByName("Continuous")
                node_acquisition_mode.SetIntValue(entry.GetValue())

            cam.BeginAcquisition()

            frames = []
            for _ in range(10):
                image_result = cam.GetNextImage(2000)
                if not image_result.IsIncomplete():
                    width = image_result.GetWidth()
                    height = image_result.GetHeight()
                    # Use GetData() for safe memory handling
                    data = image_result.GetData()
                    frame = (
                        np.frombuffer(data, dtype=np.uint8)
                        .reshape((height, width))
                        .copy()
                    )
                    frames.append(frame)
                image_result.Release()

            cam.EndAcquisition()

            assert len(frames) == 10
            print(f"Acquired {len(frames)} frames")

            # Verify all frames are valid
            for i, frame in enumerate(frames):
                assert frame.shape[0] > 0
                print(f"Frame {i}: shape={frame.shape}, mean={np.mean(frame):.1f}")

        finally:
            cam.DeInit()
            del cam

    def test_image_processor_convert(self, camera_list) -> None:
        """Test using ImageProcessor to convert images."""
        if camera_list.GetSize() == 0:
            pytest.skip("No cameras connected")

        cam = camera_list.GetByIndex(0)
        cam.Init()

        # Create processor once
        processor = PySpin.ImageProcessor()
        processor.SetColorProcessing(
            PySpin.SPINNAKER_COLOR_PROCESSING_ALGORITHM_HQ_LINEAR
        )

        try:
            nodemap = cam.GetNodeMap()
            node_acquisition_mode = PySpin.CEnumerationPtr(
                nodemap.GetNode("AcquisitionMode")
            )
            if PySpin.IsWritable(node_acquisition_mode):
                entry = node_acquisition_mode.GetEntryByName("Continuous")
                node_acquisition_mode.SetIntValue(entry.GetValue())

            cam.BeginAcquisition()

            for i in range(5):
                image_result = cam.GetNextImage(2000)
                if not image_result.IsIncomplete():
                    width = image_result.GetWidth()
                    height = image_result.GetHeight()
                    # Convert to BGR8
                    converted = processor.Convert(image_result, PySpin.PixelFormat_BGR8)

                    # Use GetData() for safe memory handling
                    data = converted.GetData()
                    frame = (
                        np.frombuffer(data, dtype=np.uint8)
                        .reshape((height, width, 3))
                        .copy()
                    )
                    print(f"Frame {i}: shape={frame.shape}")

                    assert len(frame.shape) == 3
                    assert frame.shape[2] == 3  # BGR

                image_result.Release()

            cam.EndAcquisition()

        finally:
            cam.DeInit()
            del cam


class TestSpinnakerCameraWrapper:
    """Test our SpinnakerCamera wrapper class."""

    def test_spinnaker_camera_connect_disconnect(self) -> None:
        """Test SpinnakerCamera connect and disconnect."""
        from camera.spinnaker import SPINNAKER_AVAILABLE, SpinnakerCamera

        if not SPINNAKER_AVAILABLE:
            pytest.skip("Spinnaker not available")

        camera = SpinnakerCamera()
        assert not camera.is_connected

        try:
            camera.connect()
            assert camera.is_connected
        except RuntimeError as e:
            if "No cameras" in str(e):
                pytest.skip("No cameras connected")
            raise
        finally:
            camera.disconnect()
            assert not camera.is_connected

    def test_spinnaker_camera_settings(self) -> None:
        """Test setting camera parameters."""
        from camera.spinnaker import SPINNAKER_AVAILABLE, SpinnakerCamera

        if not SPINNAKER_AVAILABLE:
            pytest.skip("Spinnaker not available")

        camera = SpinnakerCamera()

        try:
            camera.connect()
        except RuntimeError as e:
            if "No cameras" in str(e):
                pytest.skip("No cameras connected")
            raise

        try:
            camera.set_exposure(10000)
            camera.set_gain(0.0)
            camera.set_fps(30)
        finally:
            camera.disconnect()

    def test_spinnaker_camera_single_frame(self) -> None:
        """Test acquiring a single frame with SpinnakerCamera."""
        from camera.spinnaker import SPINNAKER_AVAILABLE, SpinnakerCamera

        if not SPINNAKER_AVAILABLE:
            pytest.skip("Spinnaker not available")

        camera = SpinnakerCamera()

        try:
            camera.connect()
        except RuntimeError as e:
            if "No cameras" in str(e):
                pytest.skip("No cameras connected")
            raise

        try:
            camera.start_acquisition()
            assert camera.is_acquiring

            frame = camera.get_frame()
            assert frame is not None
            assert isinstance(frame, np.ndarray)
            assert len(frame.shape) == 3
            print(f"Frame shape: {frame.shape}")

            camera.stop_acquisition()
            assert not camera.is_acquiring
        finally:
            camera.disconnect()

    def test_spinnaker_camera_multiple_frames(self) -> None:
        """Test acquiring multiple frames with SpinnakerCamera."""
        from camera.spinnaker import SPINNAKER_AVAILABLE, SpinnakerCamera

        if not SPINNAKER_AVAILABLE:
            pytest.skip("Spinnaker not available")

        camera = SpinnakerCamera()

        try:
            camera.connect()
        except RuntimeError as e:
            if "No cameras" in str(e):
                pytest.skip("No cameras connected")
            raise

        try:
            camera.start_acquisition()

            frames = []
            for _ in range(20):
                frame = camera.get_frame()
                if frame is not None:
                    frames.append(frame)

            camera.stop_acquisition()

            print(f"Acquired {len(frames)} frames")
            assert len(frames) >= 10  # Should get at least 10 frames

            for frame in frames:
                assert frame.shape[0] > 0
                assert frame.shape[1] > 0

        finally:
            camera.disconnect()
