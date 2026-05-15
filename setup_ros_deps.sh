#!/usr/bin/env bash
# setup_ros_deps.sh
#
# Installs all ROS-side dependencies and builds the catkin workspace.
# Run this ONCE after cloning, and again after any git pull that adds new packages.
#
# Works on:
#   - Jupiter robot  (Ubuntu 20.04 + ROS Noetic, native)
#   - ROS Docker container
#   - Any Ubuntu 20.04 machine with ROS Noetic installed
#
# Usage (from repo root):
#   bash setup_ros_deps.sh
#
# Inside Docker, repo is typically mounted at /ros1_ws or /root/catkin_ws.
# On the robot it is typically at ~/ros1-child-safety-monitoring.

set -euo pipefail

print_color() { printf "\033[%sm%s\033[0m\n" "$1" "$2"; }
info()    { print_color "36" "[INFO] $*"; }
success() { print_color "32" "[OK]   $*"; }
warn()    { print_color "33" "[WARN] $*"; }
error()   { print_color "31" "[ERR]  $*"; }

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REQUIREMENTS="$REPO_ROOT/src/child_safety_monitoring/requirements_ros1.txt"

echo ""
echo "============================================"
info "  Child Safety Monitoring - ROS Deps Setup"
echo "============================================"
echo ""

# ── 1. Source ROS ────────────────────────────────────────────────────────────
info "[1/4] Sourcing ROS Noetic ..."
if [ -f /opt/ros/noetic/setup.bash ]; then
    # shellcheck disable=SC1091
    source /opt/ros/noetic/setup.bash
    success "ROS Noetic sourced."
else
    error "/opt/ros/noetic/setup.bash not found."
    echo "      Make sure ROS Noetic is installed on this machine."
    exit 1
fi

# ── 2. Install apt packages ───────────────────────────────────────────────────
info "[2/4] Installing apt packages ..."

APT_PACKAGES=(
    python3-pip
    python3-opencv
    ros-noetic-cv-bridge
    ros-noetic-image-transport
    ros-noetic-web-video-server
)

# Use sudo only if not already root (Docker runs as root, robot may not)
if [ "$(id -u)" -eq 0 ]; then
    apt-get update -qq
    apt-get install -y --no-install-recommends "${APT_PACKAGES[@]}"
else
    sudo apt-get update -qq
    sudo apt-get install -y --no-install-recommends "${APT_PACKAGES[@]}"
fi
success "apt packages installed."

# ── 3. Install Python packages ────────────────────────────────────────────────
info "[3/4] Installing Python packages from requirements_ros1.txt ..."

if [ ! -f "$REQUIREMENTS" ]; then
    error "requirements_ros1.txt not found at $REQUIREMENTS"
    exit 1
fi

# Use --user when not root (robot), plain install when root (Docker)
if [ "$(id -u)" -eq 0 ]; then
    pip3 install -r "$REQUIREMENTS"
else
    pip3 install --user -r "$REQUIREMENTS"
fi
success "Python packages installed."

# ── 4. Build catkin workspace ─────────────────────────────────────────────────
info "[4/4] Building catkin workspace ..."
cd "$REPO_ROOT"
catkin_make
source devel/setup.bash
success "Build complete."

echo ""
echo "============================================"
success "Setup complete!"
echo "============================================"
echo ""
echo "Activate the workspace before launching:"
echo "  source $REPO_ROOT/devel/setup.bash"
echo ""
echo "Then launch (Docker / stream):"
echo "  roslaunch child_safety_monitoring stream_demo.launch stream_url:=http://host.docker.internal:8090/video"
echo ""
echo "Or launch (robot):"
echo "  roslaunch child_safety_monitoring jupiter_robot_camera_demo.launch camera_topic:=/usb_cam/image_raw"
echo ""
