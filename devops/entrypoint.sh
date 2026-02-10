#!/bin/bash
# Camera Analysis QC - Container entrypoint

set -e

# Check for Spinnaker SDK
if [ ! -d "/opt/spinnaker" ]; then
    echo "⚠️  WARNING: Spinnaker SDK not found at /opt/spinnaker"
    echo "   The application will run in mock camera mode."
    echo ""
    echo "   To use real cameras, mount the Spinnaker SDK:"
    echo "   docker run -v /opt/spinnaker:/opt/spinnaker:ro ..."
    echo ""
    export MOCK_CAMERA=1
fi

# Check for display
if [ -z "$DISPLAY" ]; then
    echo "ERROR: DISPLAY environment variable not set"
    echo "   Run with: -e DISPLAY=\$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix"
    exit 1
fi

# Run the application
exec python3 -m app.main "$@"
