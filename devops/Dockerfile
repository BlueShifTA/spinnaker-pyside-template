# Camera Analysis QC - Docker Image
# Multi-stage build for x86_64 Linux
#
# IMPORTANT: Place Spinnaker Python wheel in devops/sdk/ before building:
#   cp spinnaker_python-*.whl devops/sdk/
#
# Usage:
#   docker build -t camera-qc -f devops/Dockerfile .
#   docker run --rm -it \
#     -e DISPLAY=$DISPLAY \
#     -v /tmp/.X11-unix:/tmp/.X11-unix \
#     --device=/dev/bus/usb \
#     camera-qc

# =============================================================================
# Stage 1: Build
# =============================================================================
FROM python:3.10-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Copy project files
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/

# Build wheel
RUN uv build --wheel

# =============================================================================
# Stage 2: Runtime
# =============================================================================
FROM ubuntu:22.04 AS runtime

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3-pip \
    libgl1 \
    libglib2.0-0 \
    libxcb-xinerama0 \
    libxcb-cursor0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxkbcommon0 \
    libxkbcommon-x11-0 \
    libegl1 \
    libfontconfig1 \
    libdbus-1-3 \
    libusb-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy application wheel from builder
COPY --from=builder /app/dist/*.whl ./

# Copy Spinnaker SDK wheel (must exist in devops/sdk/)
COPY devops/sdk/*.whl ./sdk/

# Install the application and Spinnaker SDK
RUN pip3 install --no-cache-dir ./*.whl ./sdk/*.whl && \
    rm -rf ./sdk ./*.whl

# Copy startup script
COPY devops/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Environment for Qt
ENV QT_QPA_PLATFORM=xcb
ENV QT_X11_NO_MITSHM=1
ENV QT_QPA_PLATFORM_PLUGIN_PATH=""

# Spinnaker library paths (for GenTL)
ENV SPINNAKER_GENTL64_CTI=/opt/spinnaker/lib/flir-gentl/FLIR_GenTL.cti
ENV LD_LIBRARY_PATH=/opt/spinnaker/lib:$LD_LIBRARY_PATH

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python3", "-m", "app.main"]
