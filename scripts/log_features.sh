#!/usr/bin/env bash
set -eo pipefail
LABEL="${1:-normal}"
cd "$(dirname "$0")/.."
source /opt/ros/noetic/setup.bash
source devel/setup.bash
roslaunch child_safety_monitoring feature_logger.launch label:="$LABEL"
