#!/usr/bin/env bash
set -eo pipefail
cd "$(dirname "$0")/.."
source /opt/ros/noetic/setup.bash
source devel/setup.bash
roslaunch child_safety_monitoring ai_scenario_demo.launch
