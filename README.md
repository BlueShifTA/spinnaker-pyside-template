# Spinnaker + PySide6 Camera Application

A desktop application for FLIR Spinnaker camera livestreaming with PySide6 GUI, designed for camera QC and beam profiling.

## ✨ Features

- **Live Camera View** with overlay options (grid, crosshair)
- **X/Y Projection Analysis** with multiple modes:
  - Sum (true projection)
  - Min/Max (extreme value)
  - Average (mean)
- **Beam Profiling**:
  - FWHM (Full Width at Half Maximum) calculation
  - Mean, standard deviation, peak position
  - Normalization option
- **Export Capabilities**:
  - Image export (TIFF, PNG)
  - Projection data export (CSV, PNG)
- **Keyboard Shortcuts**:
  - `H` - Hide/show control panel
  - `F` - Toggle fullscreen
  - `Escape` - Exit fullscreen

## 🏗️ Project Structure

```
├── src/
│   ├── app/              # Application entry point
│   │   └── main.py
│   ├── camera/           # Camera interfaces
│   │   ├── protocol.py   # Abstract camera interface
│   │   ├── spinnaker.py  # FLIR Spinnaker implementation
│   │   ├── mock.py       # Mock camera for development
│   │   └── discover.py   # Camera discovery utility
│   ├── ui/               # PySide6 widgets
│   │   ├── main_window.py
│   │   ├── viewport.py   # Video display widget
│   │   ├── controls.py   # Camera control panel
│   │   └── projections.py # X/Y projection panels
│   └── core/             # Core utilities
│       ├── config.py     # Configuration
│       └── projection.py # Projection analysis
├── tests/                # pytest + pytest-qt tests
├── devops/
│   └── .pre-commit-config.yaml
├── pyproject.toml        # Python project (uv)
└── justfile              # Task runner
```

## 🚀 Quick Start

### Prerequisites
- Python 3.10 (required for Spinnaker SDK)
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- [just](https://github.com/casey/just) (command runner)
- FLIR Spinnaker SDK 4.3+ (for real cameras)
- **macOS**: `brew install ffmpeg@2.8` (required by Spinnaker)

### Installation

```bash
# Install Python deps (auto-installs Python 3.10)
just install

# Install Spinnaker Python bindings (requires SDK installed first)
just install-spinnaker

# Or do both at once
just install-all
```

### Running the Application

```bash
# Run with mock camera (no hardware required)
just run-mock

# Run with real Spinnaker camera
just run

# Discover connected cameras
just discover
```

## 📋 Available Commands

```bash
just              # List all commands
just install      # Install dependencies
just run          # Run application
just run-mock     # Run with mock camera
just discover     # List connected cameras
just test         # Run tests
just test-cov 80  # Run tests with coverage
just lint         # Run linters
just typecheck    # Run mypy
just build-exe    # Build standalone executable
```

## ⚠️ Important: Dependency Management

Spinnaker Python is **not on PyPI** - it's installed from a local wheel file. Running `uv sync` directly will remove it!

```bash
# ✅ Use this to sync dependencies (preserves Spinnaker):
just sync

# ❌ Don't use this directly:
uv sync  # This removes spinnaker-python!
```

## 🎥 Camera Support

### Mock Camera
Development mode that generates test patterns. No hardware required.

```bash
MOCK_CAMERA=1 just run
# or
just run-mock
```

### Spinnaker Cameras (SDK 4.2.x or 4.3.x with workaround)
Supports FLIR/Point Grey cameras via Spinnaker SDK.

**⚠️ Known Issue with SDK 4.3.0.189 on macOS ARM64:**
PySpin 4.3.0.189 has a memory corruption bug where `GetNDArray()` returns numpy arrays 
with incorrect `OWNDATA` flag. When garbage collected, numpy tries to free PySpin's 
internal memory, causing "pointer being freed was not allocated" crash.

**Workaround (implemented in this project):** Clear the `OWNDATA` flag before copying:
```python
import ctypes

class _PyArrayObject(ctypes.Structure):
    _fields_ = [("ob_refcnt", ctypes.c_ssize_t), ("ob_type", ctypes.c_void_p),
                ("data", ctypes.c_void_p), ("nd", ctypes.c_int),
                ("dimensions", ctypes.c_void_p), ("strides", ctypes.c_void_p),
                ("base", ctypes.c_void_p), ("descr", ctypes.c_void_p),
                ("flags", ctypes.c_int)]

def clear_owndata(arr):
    _PyArrayObject.from_address(id(arr)).flags &= ~0x0004

raw = img.GetNDArray()
clear_owndata(raw)  # Prevent numpy from freeing PySpin memory
frame = np.array(raw, copy=True)  # Now safe to copy
```

**Download SDK**: [Teledyne Spinnaker SDK Downloads](https://www.teledynevisionsolutions.com/support/support-center/software-firmware-downloads/iis/spinnaker-sdk-download/spinnaker-sdk--download-files/?pn=Spinnaker+SDK&vn=Spinnaker+SDK)

**macOS (Apple Silicon):**
1. Download & install Spinnaker SDK 4.3 for macOS (Apple Silicon)
2. Install ffmpeg dependency: `brew install ffmpeg`
3. Run: `just install-spinnaker`
4. Verify: `just discover`

**Linux/Windows:**
1. Download Spinnaker SDK from Teledyne
2. Extract the Python wheel and install:
   ```bash
   uv pip install spinnaker_python-4.x.x.x-cp310-*.whl
   ```

## 🔧 Configuration

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Environment variables:
- `CAMERA_SERIAL` - Target specific camera by serial number
- `CAMERA_FPS` - Target frame rate (default: 30)
- `CAMERA_EXPOSURE_US` - Exposure time in microseconds
- `CAMERA_GAIN_DB` - Gain in dB
- `DISPLAY_WIDTH/HEIGHT` - Display resolution
- `MOCK_CAMERA` - Set to 1 for mock mode

## 🧪 Testing

```bash
# Run all tests
just test

# Run with coverage
just test-cov 80

# Run with real camera hardware
just test-hardware

# Run without hardware (mock only)
just test-mock
```

Uses `pytest-qt` for GUI testing. Coverage target: 80%.

## 🎨 Adding New Camera Types

1. Implement `CameraProtocol` in `src/camera/`
2. Add camera factory logic in `main_window.py`
3. Add tests in `tests/`

## 📄 License

MIT
