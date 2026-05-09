#!/usr/bin/env bash
# Run this INSIDE the ROS Noetic Docker container.
# It installs dependencies, builds the workspace, and sources it.

set -eo pipefail
cd /root/catkin_ws

bash scripts/setup_ros1_python_deps.sh
bash scripts/build_ros1_workspace.sh
set +u
source devel/setup.bash
set -u 2>/dev/null || true

echo ""
echo "Docker ROS 1 workspace is ready."
echo "Run laptop demo with:"
echo "  roslaunch child_safety_monitoring stream_demo.launch stream_url:=http://host.docker.internal:8090/video"
