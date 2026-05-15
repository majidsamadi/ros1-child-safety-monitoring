#!/usr/bin/env bash
set -eo pipefail
CAMERA_TOPIC="${1:-/usb_cam/image_raw}"
cd "$(dirname "$0")/.."
source /opt/ros/noetic/setup.bash
source devel/setup.bash
roslaunch child_safety_monitoring ai_jupiter_robot_camera_demo.launch camera_topic:="$CAMERA_TOPIC"
