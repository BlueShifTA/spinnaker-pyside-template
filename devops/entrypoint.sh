#!/bin/bash
# Camera Analysis QC - Container entrypoint

set -e

# Check if PySpin is available (installed in container)
PYSPIN_OK=$(python3 -c "import PySpin; print('yes')" 2>/dev/null || echo "no")

if [ "$PYSPIN_OK" != "yes" ]; then
    echo "⚠️  WARNING: Spinnaker Python SDK not installed in container"
    echo "   The application will run in mock camera mode."
    echo ""
    echo "   To build with Spinnaker SDK:"
    echo "   1. Copy wheel to devops/sdk/: cp spinnaker_python-*.whl devops/sdk/"
    echo "   2. Rebuild: docker build -t camera-qc -f devops/Dockerfile ."
    echo ""
    export MOCK_CAMERA=1
fi

# Check for Spinnaker C++ libraries (needed for USB access)
if [ ! -d "/opt/spinnaker" ] && [ "$PYSPIN_OK" = "yes" ]; then
    echo "⚠️  WARNING: Spinnaker C++ libraries not found at /opt/spinnaker"
    echo "   Camera USB communication may not work."
    echo ""
    echo "   Mount the SDK: docker run -v /opt/spinnaker:/opt/spinnaker:ro ..."
    echo ""
fi

# Check for display
if [ -z "$DISPLAY" ]; then
    echo "ERROR: DISPLAY environment variable not set"
    echo "   Run with: -e DISPLAY=\$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix"
    exit 1
fi

# Disable OpenCV's Qt plugins to avoid conflicts with PySide6
export QT_QPA_PLATFORM_PLUGIN_PATH=""

# Remove cv2 qt plugins path if it exists (they conflict with PySide6)
if [ -d "/usr/local/lib/python3.10/dist-packages/cv2/qt/plugins" ]; then
    rm -rf /usr/local/lib/python3.10/dist-packages/cv2/qt/plugins 2>/dev/null || true
fi

# Run the application
exec python3 -m app.main "$@"
