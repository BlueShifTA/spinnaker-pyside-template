#!/bin/bash
# Camera Analysis QC - Linux Installer
#
# This script installs the Camera Analysis QC application.
#
# Usage:
#   sudo ./install.sh              # Install from Docker image
#   sudo ./install.sh --source     # Install from source (dev mode)
#   sudo ./install.sh --help       # Show help
#
# Requirements:
#   - Docker (for container mode)
#   - Python 3.10+ and uv (for source mode)
#   - Spinnaker Python wheel in devops/sdk/ (optional, for real camera)

set -e

# Configuration
APP_NAME="camera-qc"
INSTALL_DIR="/opt/camera-qc"
BIN_DIR="/usr/local/bin"
DESKTOP_DIR="/usr/share/applications"
ICON_DIR="/usr/share/icons/hicolor/256x256/apps"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Detect architecture
ARCH=$(uname -m)
case $ARCH in
    x86_64)
        PLATFORM="x86_64"
        DOCKERFILE="Dockerfile"
        ;;
    aarch64)
        PLATFORM="arm64"
        DOCKERFILE="Dockerfile.jetson"
        ;;
    *)
        echo -e "${RED}Unsupported architecture: $ARCH${NC}"
        exit 1
        ;;
esac

echo "=============================================="
echo "  Camera Analysis QC Installer"
echo "  Platform: $PLATFORM"
echo "=============================================="
echo ""

# Parse arguments
INSTALL_MODE="docker"
while [[ $# -gt 0 ]]; do
    case $1 in
        --source)
            INSTALL_MODE="source"
            shift
            ;;
        --help)
            echo "Usage: sudo $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --source    Install from source (development mode)"
            echo "  --help      Show this help message"
            echo ""
            echo "Default: Install from Docker container"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Check root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root (sudo)${NC}"
    exit 1
fi

# Check prerequisites
check_docker() {
    if command -v docker &> /dev/null; then
        echo -e "${GREEN}✓ Docker found${NC}"
        return 0
    else
        echo -e "${RED}✗ Docker not found${NC}"
        echo "  Please install Docker: https://docs.docker.com/engine/install/"
        return 1
    fi
}

check_python() {
    if command -v python3.10 &> /dev/null || command -v python3 &> /dev/null; then
        echo -e "${GREEN}✓ Python found${NC}"
        return 0
    else
        echo -e "${RED}✗ Python 3.10+ not found${NC}"
        return 1
    fi
}

# Installation functions
install_docker() {
    echo ""
    echo "Installing from Docker..."
    echo ""
    
    check_docker || exit 1
    
    # Get script directory
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
    
    # Check if SDK wheel exists
    if ! ls "$SCRIPT_DIR/sdk/"*.whl 1>/dev/null 2>&1; then
        echo -e "${YELLOW}⚠ No Spinnaker wheel found in devops/sdk/${NC}"
        echo "  Copy the wheel before building:"
        echo "    cp spinnaker_python-*.whl devops/sdk/"
        echo ""
        echo "  Continuing without SDK (mock camera only)..."
        echo ""
    fi
    
    # Build Docker image (use --no-cache to ensure SDK wheel is picked up)
    echo "Building Docker image..."
    cd "$PROJECT_DIR"
    docker build --no-cache -t $APP_NAME -f devops/$DOCKERFILE .
    
    # Create install directory
    mkdir -p "$INSTALL_DIR"
    
    # Create wrapper script - simple, SDK is in container
    cat > "$BIN_DIR/$APP_NAME" << 'WRAPPER'
#!/bin/bash
# Camera Analysis QC - Docker wrapper

# Allow X11 connections
xhost +local:docker 2>/dev/null || true

# Run the container
# - SDK is installed inside container from wheel
# - USB device access for camera
# - X11 forwarding for GUI
docker run --rm -it \
    -e DISPLAY="$DISPLAY" \
    -e QT_X11_NO_MITSHM=1 \
    -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
    -v "$HOME/camera-qc-exports:/app/exports" \
    --device=/dev/bus/usb \
    --privileged \
    camera-qc "$@"
WRAPPER
    chmod +x "$BIN_DIR/$APP_NAME"
    
    echo -e "${GREEN}✓ Docker wrapper installed${NC}"
}

install_source() {
    echo ""
    echo "Installing from source..."
    echo ""
    
    check_python || exit 1
    
    # Get script directory
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
    
    # Check for SDK wheel
    SDK_WHEEL=""
    if ls "$SCRIPT_DIR/sdk/"*.whl 1>/dev/null 2>&1; then
        SDK_WHEEL=$(ls "$SCRIPT_DIR/sdk/"*.whl | head -1)
        echo -e "${GREEN}✓ Found SDK wheel: $(basename $SDK_WHEEL)${NC}"
    else
        echo -e "${YELLOW}⚠ No Spinnaker wheel in devops/sdk/ - will use mock camera${NC}"
    fi
    
    # Create install directory with source link
    mkdir -p "$INSTALL_DIR"
    ln -sf "$PROJECT_DIR" "$INSTALL_DIR/source"
    
    # Setup virtual environment and install SDK
    echo "Setting up virtual environment..."
    cd "$PROJECT_DIR"
    
    if [ ! -d ".venv" ]; then
        uv sync 2>/dev/null || (python3 -m venv .venv && .venv/bin/pip install -e .)
    fi
    
    # Install SDK wheel into venv if available
    if [ -n "$SDK_WHEEL" ]; then
        echo "Installing Spinnaker SDK..."
        .venv/bin/pip install --quiet "$SDK_WHEEL"
        echo -e "${GREEN}✓ Spinnaker SDK installed${NC}"
    fi
    
    # Create wrapper script
    cat > "$BIN_DIR/$APP_NAME" << WRAPPER
#!/bin/bash
# Camera Analysis QC - Source wrapper

cd "$PROJECT_DIR"

# Disable OpenCV Qt plugins to avoid conflicts with PySide6
export QT_QPA_PLATFORM_PLUGIN_PATH=""

# Run the application from venv (SDK is installed in venv)
exec .venv/bin/python -m app.main "\$@"
WRAPPER
    chmod +x "$BIN_DIR/$APP_NAME"
    
    echo -e "${GREEN}✓ Source wrapper installed${NC}"
}

# Create desktop entry
install_desktop() {
    mkdir -p "$DESKTOP_DIR"
    mkdir -p "/usr/share/icons/hicolor/scalable/apps"
    
    # Get script directory
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    # Copy SVG icon
    if [ -f "$SCRIPT_DIR/camera-qc.svg" ]; then
        cp "$SCRIPT_DIR/camera-qc.svg" "/usr/share/icons/hicolor/scalable/apps/camera-qc.svg"
        echo "  Installed icon to /usr/share/icons/"
    fi
    
    # Create desktop entry in system location
    cat > "$DESKTOP_DIR/$APP_NAME.desktop" << DESKTOP
[Desktop Entry]
Version=1.0
Type=Application
Name=Camera Analysis QC
Comment=Camera quality control with beam profiling
Exec=$BIN_DIR/$APP_NAME
Icon=camera-qc
Terminal=false
Categories=Utility;Graphics;Science;
Keywords=camera;qc;beam;profile;
DESKTOP
    
    chmod 644 "$DESKTOP_DIR/$APP_NAME.desktop"
    
    # Also copy to user's Desktop for easy access
    REAL_USER="${SUDO_USER:-$USER}"
    USER_DESKTOP="/home/$REAL_USER/Desktop"
    if [ -d "$USER_DESKTOP" ]; then
        DESKTOP_FILE="$USER_DESKTOP/$APP_NAME.desktop"
        cp "$DESKTOP_DIR/$APP_NAME.desktop" "$DESKTOP_FILE"
        chown "$REAL_USER:$REAL_USER" "$DESKTOP_FILE"
        chmod 755 "$DESKTOP_FILE"
        echo "  Copied to $USER_DESKTOP/"
        
        # Mark as trusted on GNOME using dbus-launch
        if command -v gio &> /dev/null && command -v dbus-launch &> /dev/null; then
            sudo -u "$REAL_USER" dbus-launch gio set "$DESKTOP_FILE" metadata::trusted true 2>/dev/null && \
                echo -e "  ${GREEN}✓ Desktop icon trusted${NC}" || \
                echo "  Note: Right-click the icon and select 'Allow Launching'"
        elif command -v gio &> /dev/null; then
            echo "  Run: dbus-launch gio set $DESKTOP_FILE metadata::trusted true"
        fi
    fi
    
    # Update desktop database and icon cache
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
    
    echo -e "${GREEN}✓ Desktop entry installed${NC}"
    echo "  System: $DESKTOP_DIR/$APP_NAME.desktop"
}

# Main installation
echo "Checking prerequisites..."
echo ""

if [ "$INSTALL_MODE" = "docker" ]; then
    install_docker
else
    install_source
fi

install_desktop

echo ""
echo "=============================================="
echo -e "${GREEN}  Installation complete!${NC}"
echo "=============================================="
echo ""
echo "You can now:"
echo "  1. Run from terminal: $APP_NAME"
echo "  2. Launch from application menu: Camera Analysis QC"
echo ""
echo "To uninstall: sudo $0/../uninstall.sh"
echo ""
