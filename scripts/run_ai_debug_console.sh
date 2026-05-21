#!/usr/bin/env bash
# Run a compact live debug console for features and AI probabilities.
set -eo pipefail
cd "$(dirname "$0")/.."
source /opt/ros/noetic/setup.bash
source devel/setup.bash
rosrun child_safety_monitoring risk_debug_console_node.py _print_rate_hz:=1.0
