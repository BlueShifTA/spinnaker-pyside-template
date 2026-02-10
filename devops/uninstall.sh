#!/bin/bash
# Camera Analysis QC - Uninstaller
#
# Usage:
#   sudo ./uninstall.sh

set -e

APP_NAME="camera-qc"
INSTALL_DIR="/opt/camera-qc"
BIN_DIR="/usr/local/bin"
DESKTOP_DIR="/usr/share/applications"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

echo "=============================================="
echo "  Camera Analysis QC Uninstaller"
echo "=============================================="
echo ""

# Check root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root (sudo)${NC}"
    exit 1
fi

# Remove files
echo "Removing installation..."

# Remove wrapper script
if [ -f "$BIN_DIR/$APP_NAME" ]; then
    rm -f "$BIN_DIR/$APP_NAME"
    echo "  Removed $BIN_DIR/$APP_NAME"
fi

# Remove desktop entry
if [ -f "$DESKTOP_DIR/$APP_NAME.desktop" ]; then
    rm -f "$DESKTOP_DIR/$APP_NAME.desktop"
    echo "  Removed $DESKTOP_DIR/$APP_NAME.desktop"
fi

# Remove install directory
if [ -d "$INSTALL_DIR" ]; then
    rm -rf "$INSTALL_DIR"
    echo "  Removed $INSTALL_DIR"
fi

# Update desktop database
update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true

# Ask about Docker image
if command -v docker &> /dev/null; then
    if docker images | grep -q "$APP_NAME"; then
        echo ""
        read -p "Remove Docker image $APP_NAME? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker rmi $APP_NAME 2>/dev/null || true
            docker rmi $APP_NAME-jetson 2>/dev/null || true
            echo "  Removed Docker images"
        fi
    fi
fi

echo ""
echo -e "${GREEN}Uninstallation complete!${NC}"
echo ""
