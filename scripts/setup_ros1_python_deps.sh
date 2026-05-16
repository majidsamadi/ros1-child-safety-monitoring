#!/usr/bin/env bash
# Install ROS 1 Noetic system + Python AI dependencies.
# Usage:
#   ./scripts/setup_ros1_python_deps.sh
#   ./scripts/setup_ros1_python_deps.sh --no-apt
# Environment:
#   INSTALL_TORCH=0    do not install torch even if missing
#   INSTALL_TORCH=1    force install CPU torch optional requirements
#   INSTALL_TORCH=auto install CPU torch only if torch is missing

set -eo pipefail
cd "$(dirname "$0")/.."

RUN_APT=1
for arg in "$@"; do
  if [ "$arg" = "--no-apt" ]; then
    RUN_APT=0
  fi
done

if [ -f /opt/ros/noetic/setup.bash ]; then
  set +u
  source /opt/ros/noetic/setup.bash
  set -u 2>/dev/null || true
else
  echo "WARNING: /opt/ros/noetic/setup.bash not found. Continuing anyway."
fi

if [ "$RUN_APT" = "1" ]; then
  APT="apt"
  SUDO=""
  if [ "$(id -u)" != "0" ]; then
    if command -v sudo >/dev/null 2>&1; then
      SUDO="sudo"
    else
      echo "ERROR: Need root or sudo to install apt packages." >&2
      exit 1
    fi
  fi

  echo "Installing ROS/system packages. Use --no-apt on shared robots if you only want Python user deps."
  $SUDO $APT update
  $SUDO $APT install -y \
    python3-pip \
    python3-opencv \
    ros-noetic-cv-bridge \
    ros-noetic-image-transport \
    ros-noetic-web-video-server
else
  echo "Skipping apt installation because --no-apt was provided."
fi

PIP_USER=""
if [ "$(id -u)" != "0" ]; then
  PIP_USER="--user"
fi

python3 -m pip install $PIP_USER --upgrade pip setuptools wheel
python3 -m pip install $PIP_USER -r src/child_safety_monitoring/requirements_ros1.txt

INSTALL_TORCH_MODE="${INSTALL_TORCH:-auto}"
if python3 - <<'PY' >/dev/null 2>&1
import torch
PY
then
  if [ "$INSTALL_TORCH_MODE" = "1" ]; then
    echo "Torch exists but INSTALL_TORCH=1, installing optional CPU torch anyway."
    python3 -m pip install $PIP_USER -r src/child_safety_monitoring/requirements_torch_cpu_optional.txt
  else
    echo "Torch already installed. Keeping existing torch build."
  fi
else
  if [ "$INSTALL_TORCH_MODE" = "0" ]; then
    echo "Torch is missing, but INSTALL_TORCH=0. Skipping torch install."
  else
    echo "Torch missing. Installing optional CPU torch build."
    python3 -m pip install $PIP_USER -r src/child_safety_monitoring/requirements_torch_cpu_optional.txt
  fi
fi

echo ""
echo "ROS 1 Python dependencies are ready."
