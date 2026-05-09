#!/usr/bin/env bash
# Quick ROS 1 pipeline check. Run while a demo launch is running.

set -eo pipefail
set +u
source /opt/ros/noetic/setup.bash
if [ -f devel/setup.bash ]; then
  source devel/setup.bash
fi
set -u 2>/dev/null || true

echo "Nodes:"
rosnode list || true

echo ""
echo "Topics:"
rostopic list | grep -E "camera|pose|tracked|interaction|suspicion|alarm" || true

echo ""
echo "Checking /poses/raw for 5 seconds..."
timeout 5 rostopic hz /poses/raw || true

echo ""
echo "Checking /poses/tracked for 5 seconds..."
timeout 5 rostopic hz /poses/tracked || true

echo ""
echo "Checking /interaction/features for 5 seconds..."
timeout 5 rostopic hz /interaction/features || true

echo ""
echo "One interaction feature sample:"
timeout 5 rostopic echo -n 1 /interaction/features || true

echo ""
echo "Checking for false alerts for 5 seconds:"
timeout 5 rostopic echo /suspicion_event || true
