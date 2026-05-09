#!/usr/bin/env bash
# Run laptop-camera demo inside ROS 1 Docker container.

set -eo pipefail
cd /root/catkin_ws
set +u
source /opt/ros/noetic/setup.bash
source devel/setup.bash
set -u 2>/dev/null || true

STREAM_URL="${1:-http://host.docker.internal:8090/video}"
roslaunch child_safety_monitoring stream_demo.launch stream_url:="$STREAM_URL"
