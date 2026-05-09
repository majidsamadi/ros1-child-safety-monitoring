#!/usr/bin/env bash
# Run web_video_server for browser overlay viewing.

set -eo pipefail
cd "$(dirname "$0")/.."
set +u
source /opt/ros/noetic/setup.bash
source devel/setup.bash
set -u 2>/dev/null || true

roslaunch child_safety_monitoring view_overlay.launch
