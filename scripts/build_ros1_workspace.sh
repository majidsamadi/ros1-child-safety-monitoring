#!/usr/bin/env bash
# Build the ROS 1 catkin workspace.

set -eo pipefail
cd "$(dirname "$0")/.."

set +u
source /opt/ros/noetic/setup.bash
set -u 2>/dev/null || true

catkin_make

echo ""
echo "Build finished. Before running nodes, use:"
echo "  source devel/setup.bash"
