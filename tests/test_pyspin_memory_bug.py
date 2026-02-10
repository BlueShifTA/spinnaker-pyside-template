#!/usr/bin/env python3
"""
Test and workaround for PySpin 4.3.0.189 memory corruption bug on macOS ARM64.

The bug: GetNDArray() returns a numpy array with OWNDATA=True, but the memory
is actually owned by PySpin. When Python's garbage collector runs, numpy tries
to free memory it doesn't own, causing "malloc: pointer being freed was not
allocated" crash.

SOLUTION: Clear the OWNDATA flag on the returned array before copying.

NOTE: These tests are NOT meant to be run via pytest - they must be run standalone
because PySpin doesn't handle multiple system instances well in the same process.

Run individual tests:
    uv run python tests/test_pyspin_memory_bug.py 1  # No data access (works)
    uv run python tests/test_pyspin_memory_bug.py 2  # BUG: Multiple frames crash
    uv run python tests/test_pyspin_memory_bug.py 3  # WORKAROUND: Clear OWNDATA
"""

# Skip if imported by pytest
import sys

if "pytest" in sys.modules:
    import pytest

    pytest.skip(
        "These tests must be run standalone, not via pytest", allow_module_level=True
    )

import ctypes
import sys

import numpy as np

try:
    import PySpin
except ImportError:
    print("PySpin not installed")
    sys.exit(1)


# ============================================================================
# WORKAROUND: Clear OWNDATA flag to prevent numpy from freeing PySpin memory
# ============================================================================


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


_NPY_ARRAY_OWNDATA = 0x0004


def clear_owndata_flag(arr: np.ndarray) -> None:  # type: ignore[type-arg]
    """Clear OWNDATA flag to prevent numpy from freeing PySpin memory."""
    arr_struct = _PyArrayObject.from_address(id(arr))
    arr_struct.flags &= ~_NPY_ARRAY_OWNDATA


# ============================================================================
# Test functions
# ============================================================================


def test_no_data_access() -> None:
    """Test: Acquire frames without accessing pixel data - should work."""
    print("\n[TEST 1] Multiple frames, no GetNDArray call - SHOULD WORK")

    system = PySpin.System.GetInstance()
    v = system.GetLibraryVersion()
    print(f"PySpin version: {v.major}.{v.minor}.{v.type}.{v.build}")

    cam_list = system.GetCameras()
    if cam_list.GetSize() == 0:
        print("  SKIP: No cameras connected")
        cam_list.Clear()
        system.ReleaseInstance()
        return

    cam = cam_list.GetByIndex(0)
    cam.Init()

    nodemap = cam.GetNodeMap()
    node_acq = PySpin.CEnumerationPtr(nodemap.GetNode("AcquisitionMode"))
    if PySpin.IsWritable(node_acq):
        entry = node_acq.GetEntryByName("Continuous")
        node_acq.SetIntValue(entry.GetValue())

    cam.BeginAcquisition()

    for i in range(5):
        img = cam.GetNextImage(2000)
        width, height = img.GetWidth(), img.GetHeight()
        print(f"  Frame {i}: {width}x{height}")
        img.Release()

    cam.EndAcquisition()
    cam.DeInit()
    del cam
    cam_list.Clear()
    system.ReleaseInstance()

    print("  PASS: No crash")


def test_bug_multiple_frames() -> None:
    """Test: Multiple frames with GetNDArray - CRASHES on 2nd frame due to bug."""
    print("\n[TEST 2] Multiple frames with GetNDArray - BUG DEMONSTRATION")
    print("  This test will crash with 'pointer being freed was not allocated'")

    system = PySpin.System.GetInstance()
    v = system.GetLibraryVersion()
    print(f"  PySpin version: {v.major}.{v.minor}.{v.type}.{v.build}")

    cam_list = system.GetCameras()
    if cam_list.GetSize() == 0:
        print("  SKIP: No cameras connected")
        cam_list.Clear()
        system.ReleaseInstance()
        return

    cam = cam_list.GetByIndex(0)
    cam.Init()

    nodemap = cam.GetNodeMap()
    node_acq = PySpin.CEnumerationPtr(nodemap.GetNode("AcquisitionMode"))
    if PySpin.IsWritable(node_acq):
        entry = node_acq.GetEntryByName("Continuous")
        node_acq.SetIntValue(entry.GetValue())

    cam.BeginAcquisition()

    for i in range(5):
        img = cam.GetNextImage(2000)
        if img.IsIncomplete():
            img.Release()
            continue

        # BUG: GetNDArray returns array with incorrect OWNDATA flag
        raw = img.GetNDArray()
        frame = np.array(raw, copy=True)
        print(f"  Frame {i}: mean={frame.mean():.1f}")

        img.Release()
        # Crash happens here when GC runs and tries to free 'raw'

    cam.EndAcquisition()
    cam.DeInit()
    del cam
    cam_list.Clear()
    system.ReleaseInstance()

    print("  PASS: No crash (unexpected)")


def test_workaround_clear_owndata() -> None:
    """Test: WORKAROUND - Clear OWNDATA flag before copy."""
    print("\n[TEST 3] WORKAROUND: Clear OWNDATA flag - SHOULD WORK")

    system = PySpin.System.GetInstance()
    v = system.GetLibraryVersion()
    print(f"  PySpin version: {v.major}.{v.minor}.{v.type}.{v.build}")

    cam_list = system.GetCameras()
    if cam_list.GetSize() == 0:
        print("  SKIP: No cameras connected")
        cam_list.Clear()
        system.ReleaseInstance()
        return

    cam = cam_list.GetByIndex(0)
    cam.Init()

    nodemap = cam.GetNodeMap()
    node_acq = PySpin.CEnumerationPtr(nodemap.GetNode("AcquisitionMode"))
    if PySpin.IsWritable(node_acq):
        entry = node_acq.GetEntryByName("Continuous")
        node_acq.SetIntValue(entry.GetValue())

    cam.BeginAcquisition()

    frames = []
    for i in range(10):
        img = cam.GetNextImage(2000)
        if img.IsIncomplete():
            img.Release()
            continue

        raw = img.GetNDArray()

        # WORKAROUND: Clear OWNDATA flag BEFORE any copy operation
        clear_owndata_flag(raw)

        # Now we can safely copy
        frame = np.array(raw, copy=True)
        frames.append(frame)
        print(f"  Frame {i}: {frame.shape}, mean={frame.mean():.1f}")

        img.Release()

    cam.EndAcquisition()
    cam.DeInit()
    del cam
    cam_list.Clear()
    system.ReleaseInstance()

    print(f"  PASS: Captured {len(frames)} frames without crash")


if __name__ == "__main__":
    print("=" * 70)
    print("PySpin 4.3.0.189 Memory Bug Test and Workaround")
    print("=" * 70)
    print(f"Python: {sys.version}")
    print(f"NumPy: {np.__version__}")

    if len(sys.argv) > 1:
        test_num = int(sys.argv[1])
        tests = [
            test_no_data_access,
            test_bug_multiple_frames,
            test_workaround_clear_owndata,
        ]
        if 1 <= test_num <= len(tests):
            tests[test_num - 1]()
        else:
            print(f"Invalid test number. Use 1-{len(tests)}")
    else:
        print("\nUsage: python test_pyspin_memory_bug.py <test_number>")
        print("  1 - No data access (works fine)")
        print("  2 - BUG: Multiple frames with GetNDArray (will crash)")
        print("  3 - WORKAROUND: Clear OWNDATA flag (works)")
