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
[doc("Install Spinnaker Python from SDK (auto-detect OS)")]
install-spinnaker:
  #!/usr/bin/env bash
  set -euo pipefail
  
  OS="$(uname -s)"
  ARCH="$(uname -m)"
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  SDK_DIR="$SCRIPT_DIR/devops/sdk"
  
  echo "🔍 Detecting platform: $OS / $ARCH"
  
  case "$OS" in
    Darwin)
      # macOS - check for wheel in SDK dir first, then system
      if [ "$ARCH" = "arm64" ]; then
        WHEEL=$(find "$SDK_DIR" -name "spinnaker_python*macosx*arm64*.whl" 2>/dev/null | head -1)
        if [ -z "$WHEEL" ]; then
          # Try to extract from system Spinnaker
          SPIN_DIR="/Applications/Spinnaker/PySpin"
          WHEEL_TAR=$(find "$SPIN_DIR" -name "spinnaker_python*arm64*.tar.gz" 2>/dev/null | head -1)
          if [ -n "$WHEEL_TAR" ]; then
            echo "📦 Extracting from $WHEEL_TAR..."
            TMPDIR=$(mktemp -d)
            tar -xzf "$WHEEL_TAR" -C "$TMPDIR"
            WHEEL=$(find "$TMPDIR" -name "*.whl" | head -1)
          fi
        fi
      else
        WHEEL=$(find "$SDK_DIR" -name "spinnaker_python*macosx*x86_64*.whl" 2>/dev/null | head -1)
      fi
      ;;
      
    Linux)
      # Linux - check SDK dir for wheel
      if [ "$ARCH" = "x86_64" ]; then
        WHEEL=$(find "$SDK_DIR" -name "spinnaker_python*linux_x86_64*.whl" 2>/dev/null | head -1)
      elif [ "$ARCH" = "aarch64" ]; then
        WHEEL=$(find "$SDK_DIR" -name "spinnaker_python*linux_aarch64*.whl" -o -name "spinnaker_python*linux_arm64*.whl" 2>/dev/null | head -1)
      fi
      ;;
      
    *)
      echo "❌ Unsupported OS: $OS"
      exit 1
      ;;
  esac
  
  if [ -z "$WHEEL" ] || [ ! -f "$WHEEL" ]; then
    echo "❌ Spinnaker Python wheel not found"
    echo ""
    echo "Please download the wheel from:"
    echo "  https://www.teledynevisionsolutions.com/support/support-center/software-firmware-downloads/iis/spinnaker-sdk-download/spinnaker-sdk--download-files/"
    echo ""
    echo "Place the .whl file in: $SDK_DIR/"
    echo "Expected: spinnaker_python-*-cp310-*.whl"
    exit 1
  fi
  
  echo "📥 Installing: $(basename "$WHEEL")"
  uv pip install "$WHEEL"
  
  echo "✅ Verifying installation..."
  uv run python -c "import PySpin; v = PySpin.System.GetInstance().GetLibraryVersion(); print(f'PySpin {v.major}.{v.minor}.{v.type}.{v.build} installed successfully')"
  
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

# Helper to find Spinnaker Python path on Linux
_spinnaker-path := if os() == "linux" {
  "/opt/spinnaker/lib/python3.10/site-packages"
} else {
  ""
}

[group('run')]
run:
  #!/usr/bin/env bash
  # Auto-detect Spinnaker Python path on Linux
  if [ "$(uname -s)" = "Linux" ]; then
    for dir in /opt/spinnaker/lib/python3.10/site-packages /opt/spinnaker/lib/python3/site-packages /opt/spinnaker/python; do
      if [ -f "$dir/PySpin.py" ] || [ -f "$dir/_PySpin.so" ]; then
        export PYTHONPATH="$dir:$PYTHONPATH"
        echo "Using Spinnaker from: $dir"
        break
      fi
    done
  fi
  exec uv run python -m app.main

[group('run')]
[doc("Run with mock camera (no hardware required)")]
run-mock:
  MOCK_CAMERA=1 uv run python -m app.main

[group('run')]
[doc("Run camera discovery utility")]
discover:
  #!/usr/bin/env bash
  if [ "$(uname -s)" = "Linux" ]; then
    for dir in /opt/spinnaker/lib/python3.10/site-packages /opt/spinnaker/lib/python3/site-packages /opt/spinnaker/python; do
      if [ -f "$dir/PySpin.py" ] || [ -f "$dir/_PySpin.so" ]; then
        export PYTHONPATH="$dir:$PYTHONPATH"
        break
      fi
    done
  fi
  exec uv run python -m camera.discover

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
