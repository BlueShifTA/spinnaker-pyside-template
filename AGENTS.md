# Repository Guidelines

## Project Structure

- `src/`: Source code
  - `app/`: Application entry point (`main.py`)
  - `camera/`: Camera interfaces and implementations
    - `protocol.py`: Abstract camera interface
    - `spinnaker.py`: FLIR Spinnaker implementation
    - `mock.py`: Mock camera for development
    - `discover.py`: Camera discovery utility
  - `ui/`: PySide6 widgets
    - `main_window.py`: Main application window
    - `viewport.py`: Video display widget
    - `controls.py`: Camera control panel
  - `core/`: Configuration and utilities
- `tests/`: pytest tests (uses pytest-qt for GUI tests)
- `devops/`: Pre-commit config

## Build, Test, Dev

- Task runner: `just`
- Install deps: `just install`
- Run app: `just run`
- Run with mock camera: `just run-mock`
- Discover cameras: `just discover`
- Run tests: `just test`
- Run tests with coverage: `just test-cov 80`
- Lint: `just lint`
- Type check: `just typecheck`
- Build executable: `just build-exe`

## Python Dependencies

- Managed by `uv` (`pyproject.toml` + `uv.lock`)
- **Python 3.10 required** (Spinnaker SDK compatibility)
- **numpy < 2.0 required** (Spinnaker compiled against numpy 1.x)
- **ffmpeg@2.8 required on macOS** (`brew install ffmpeg@2.8`)
- Spinnaker: run `just install-spinnaker` after installing SDK
- **Always use `just sync` instead of `uv sync`** to preserve spinnaker-python

## Coding Style

- Python: `ruff` for formatting/linting, `mypy` strict mode
- 4 spaces, `snake_case` for functions/modules, `PascalCase` for classes
- Camera implementations must follow `CameraProtocol`
- UI widgets in separate files under `src/ui/`

## Camera Architecture

- `CameraProtocol`: Abstract interface for all cameras
- `SpinnakerCamera`: Real camera implementation
- `MockCamera`: Development/testing without hardware
- Factory pattern in `main_window.py` selects implementation

## UI Architecture

- PySide6 with Fusion style + dark theme
- `CameraViewport`: Displays frames (QLabel with QPixmap)
- `ControlPanel`: Camera settings and controls
- `AcquisitionThread`: Background thread for frame capture
- Qt Signals for thread-safe communication

## Testing

- pytest + pytest-qt for GUI tests
- Mock camera used for automated tests
- Set `MOCK_CAMERA=1` for tests without hardware

## Adding New Features

1. For new camera types: implement `CameraProtocol`
2. For new UI controls: add to `ControlPanel` or create new widget
3. For new settings: add to `core/config.py`
4. Always add tests in `tests/`
