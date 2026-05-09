#!/usr/bin/env bash
# Start a ROS Noetic Docker development container for laptop mode.
# Run this from the repo root on macOS, Windows WSL/Git Bash, or Linux with Docker installed.

set -eo pipefail
cd "$(dirname "$0")/.."

docker rm -f ros1-child-safety-dev >/dev/null 2>&1 || true

docker run -it --rm \
  --name ros1-child-safety-dev \
  -p 8080:8080 \
  -v "$PWD:/root/catkin_ws" \
  osrf/ros:noetic-desktop \
  bash
