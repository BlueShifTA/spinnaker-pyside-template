set dotenv-load

_default:
  @just --list

# ─────────────────────────────────────────────────────────────
# Installation
# ─────────────────────────────────────────────────────────────

[group('install')]
install:
  uv python install 3.10
  uv sync --all-packages
  uv run pre-commit install --config devops/.pre-commit-config.yaml

[group('install')]
[doc("Install Spinnaker Python from SDK (macOS ARM64)")]
install-spinnaker:
  #!/usr/bin/env bash
  set -euo pipefail
  SPIN_DIR="/Applications/Spinnaker/PySpin"
  WHEEL_TAR="$SPIN_DIR/spinnaker_python-4.3.0.189-cp310-cp310-macosx_13_0_arm64.tar.gz"
  
  if [ ! -f "$WHEEL_TAR" ]; then
    echo "❌ Spinnaker SDK not found at $SPIN_DIR"
    echo ""
    echo "Please install Spinnaker SDK 4.3 from:"
    echo "  https://www.teledynevisionsolutions.com/support/support-center/software-firmware-downloads/iis/spinnaker-sdk-download/spinnaker-sdk--download-files/"
    echo ""
    echo "Download: Spinnaker SDK 4.3 for MacOS (Apple Silicon)"
    exit 1
  fi
  
  echo "📦 Extracting Spinnaker Python wheel..."
  TMPDIR=$(mktemp -d)
  tar -xzf "$WHEEL_TAR" -C "$TMPDIR"
  
  echo "📥 Installing spinnaker_python..."
  uv pip install "$TMPDIR"/spinnaker_python-*.whl
  
  echo "✅ Verifying installation..."
  uv run python -c "import PySpin; v = PySpin.System.GetInstance().GetLibraryVersion(); print(f'PySpin {v.major}.{v.minor}.{v.type}.{v.build} installed successfully')"
  
  rm -rf "$TMPDIR"
  echo "🎉 Done!"

[group('install')]
[doc("Full setup: install deps + Spinnaker")]
install-all: install install-spinnaker

[group('install')]
[doc("Reinstall after uv sync (which removes spinnaker)")]
sync: 
  uv sync --all-packages
  @just install-spinnaker

# ─────────────────────────────────────────────────────────────
# Run Application
# ─────────────────────────────────────────────────────────────

[group('run')]
run:
  uv run python -m app.main

[group('run')]
[doc("Run with mock camera (no hardware required)")]
run-mock:
  MOCK_CAMERA=1 uv run python -m app.main

[group('run')]
[doc("Run camera discovery utility")]
discover:
  uv run python -m camera.discover

# ─────────────────────────────────────────────────────────────
# Testing
# ─────────────────────────────────────────────────────────────

[group('test')]
test:
  uv run pytest

[group('test')]
[doc("Run tests with real camera hardware")]
test-hardware:
  uv run pytest --run-hardware -v

[group('test')]
[doc("Run tests with coverage")]
test-cov threshold="80":
  uv run pytest tests \
    --cov=src \
    --cov-report term-missing \
    --cov-report xml:coverage.xml \
    --cov-fail-under={{threshold}}

[group('test')]
[doc("Run tests without hardware (mock only)")]
test-mock:
  MOCK_CAMERA=1 uv run pytest

# ─────────────────────────────────────────────────────────────
# Linting & Formatting
# ─────────────────────────────────────────────────────────────

[group('lint')]
lint:
  uv run pre-commit run --config devops/.pre-commit-config.yaml --all-files

[group('lint')]
format:
  uv run ruff format src tests

[group('lint')]
typecheck:
  uv run mypy src

# ─────────────────────────────────────────────────────────────
# Build & Package
# ─────────────────────────────────────────────────────────────

[group('build')]
[doc("Build standalone executable with PyInstaller")]
build-exe:
  uv run pyinstaller --onefile --windowed --name camera-qc src/app/main.py

[group('build')]
[doc("Build Docker image for x86_64")]
build-docker:
  docker build -t camera-qc -f devops/Dockerfile .

[group('build')]
[doc("Build Docker image for Jetson")]
build-docker-jetson:
  docker build -t camera-qc-jetson -f devops/Dockerfile.jetson .

[group('build')]
clean:
  rm -rf .venv .mypy_cache .ruff_cache .pytest_cache __pycache__ .coverage coverage.xml
  rm -rf build dist *.spec
  find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# ─────────────────────────────────────────────────────────────
# Deployment
# ─────────────────────────────────────────────────────────────

[group('deploy')]
[doc("Run from Docker container")]
run-docker:
  #!/usr/bin/env bash
  xhost +local:docker 2>/dev/null || true
  docker run --rm -it \
    -e DISPLAY="$DISPLAY" \
    -e QT_X11_NO_MITSHM=1 \
    -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
    -v /opt/spinnaker:/opt/spinnaker:ro \
    -v "$HOME/camera-qc-exports:/app/exports" \
    --device=/dev/bus/usb \
    --network=host \
    camera-qc

[group('deploy')]
[doc("Install to system (requires sudo)")]
deploy-install:
  @echo "Run: sudo ./devops/install.sh"
  @echo "  or: sudo ./devops/install.sh --source (for dev mode)"

[group('deploy')]
[doc("Uninstall from system (requires sudo)")]
deploy-uninstall:
  @echo "Run: sudo ./devops/uninstall.sh"
