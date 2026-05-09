#!/usr/bin/env bash
# Run Jupiter robot camera demo on the robot.
# Usage: ./scripts/run_robot_demo.sh /camera/topic

set -eo pipefail
cd "$(dirname "$0")/.."
set +u
source /opt/ros/noetic/setup.bash
source devel/setup.bash
set -u 2>/dev/null || true

CAMERA_TOPIC="${1:-/usb_cam/image_raw}"
roslaunch child_safety_monitoring jupiter_robot_camera_demo.launch camera_topic:="$CAMERA_TOPIC"
