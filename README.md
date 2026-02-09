# Spinnaker + PySide6 Camera Application

A desktop application for FLIR Spinnaker camera livestreaming with PySide6 GUI.

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
│   │   └── controls.py   # Camera control panel
│   └── core/             # Configuration
│       └── config.py
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

### Spinnaker Cameras (SDK 4.3+)
Supports FLIR/Point Grey cameras via Spinnaker SDK.

**Download SDK**: [Teledyne Spinnaker SDK Downloads](https://www.teledynevisionsolutions.com/support/support-center/software-firmware-downloads/iis/spinnaker-sdk-download/spinnaker-sdk--download-files/?pn=Spinnaker+SDK&vn=Spinnaker+SDK)

**macOS (Apple Silicon):**
1. Download & install Spinnaker SDK 4.3 for macOS (Apple Silicon)
2. Install ffmpeg dependency: `brew install ffmpeg@2.8`
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

# Run without hardware (mock only)
just test-mock
```

Uses `pytest-qt` for GUI testing.

## 📦 Building Executable

```bash
# Build standalone .exe/.app
just build-exe
```

Uses PyInstaller to create a single-file executable.

## 🎨 Adding New Camera Types

1. Implement `CameraProtocol` in `src/camera/`
2. Add camera factory logic in `main_window.py`
3. Add tests in `tests/`

## 📄 License

MIT
