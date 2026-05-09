#!/usr/bin/env bash
# Install ROS 1 Noetic system + Python AI dependencies.
# Use this on the Jupiter robot or inside a ROS Noetic Docker container.

set -eo pipefail
cd "$(dirname "$0")/.."

if [ -f /opt/ros/noetic/setup.bash ]; then
  set +u
  source /opt/ros/noetic/setup.bash
  set -u 2>/dev/null || true
else
  echo "WARNING: /opt/ros/noetic/setup.bash not found. Continuing anyway."
fi

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

$SUDO $APT update
$SUDO $APT install -y \
  python3-pip \
  python3-opencv \
  ros-noetic-cv-bridge \
  ros-noetic-image-transport \
  ros-noetic-web-video-server

PIP_USER=""
if [ "$(id -u)" != "0" ]; then
  PIP_USER="--user"
fi

python3 -m pip install $PIP_USER --upgrade pip setuptools wheel
python3 -m pip install $PIP_USER -r src/child_safety_monitoring/requirements_ros1.txt

echo ""
echo "ROS 1 Python dependencies are installed."
