#!/usr/bin/env bash
# Create a Python 3.10 virtual environment for the host webcam streamer.
# Use this on macOS/Linux host machines, not inside ROS.

set -eo pipefail
cd "$(dirname "$0")/.."

PYTHON_BIN=""
if command -v python3.10 >/dev/null 2>&1; then
  PYTHON_BIN="python3.10"
elif command -v python3 >/dev/null 2>&1; then
  PY_VER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  if [ "$PY_VER" = "3.10" ]; then
    PYTHON_BIN="python3"
  fi
fi

if [ -z "$PYTHON_BIN" ]; then
  echo "ERROR: Python 3.10 is required for the host webcam streamer venv."
  echo "macOS Homebrew example: brew install python@3.10"
  echo "Ubuntu example: sudo apt install python3.10 python3.10-venv"
  exit 1
fi

echo "Using $($PYTHON_BIN --version)"
$PYTHON_BIN -m venv .venv310
source .venv310/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements_host.txt

echo ""
echo "Host webcam venv is ready."
echo "Run the webcam streamer with:"
echo "  source .venv310/bin/activate"
echo "  python scripts/host_webcam_streamer.py --camera 0 --port 8090"
