#!/usr/bin/env bash
set -eo pipefail
cd "$(dirname "$0")/.."
source /opt/ros/noetic/setup.bash
source devel/setup.bash
python3 src/child_safety_monitoring/scripts/train_risk_model.py --use-seed
