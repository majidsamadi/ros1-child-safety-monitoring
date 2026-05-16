#!/usr/bin/env bash
set -eo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"
source /opt/ros/noetic/setup.bash
source devel/setup.bash

STREAM_URL="${1:-/dev/video2}"
VIEWER_PORT="${2:-8080}"

if [ -f "src/child_safety_monitoring/launch/ai_stream_demo_with_viewer.launch" ]; then
  roslaunch child_safety_monitoring ai_stream_demo_with_viewer.launch \
    stream_url:="$STREAM_URL" \
    viewer_port:="$VIEWER_PORT"
else
  echo "AI launch file not found. Falling back to non-AI stream demo with viewer."
  roslaunch child_safety_monitoring stream_demo_with_viewer.launch \
    stream_url:="$STREAM_URL" \
    viewer_port:="$VIEWER_PORT"
fi
