#!/usr/bin/env bash
set -e

source /opt/ros/noetic/setup.bash
if [ -f devel/setup.bash ]; then
  source devel/setup.bash
fi

echo "Nodes:"
rosnode list || true

echo ""
echo "Relevant topics:"
rostopic list | grep -E "camera|poses|tracked|interaction|suspicion|alarm" || true

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
timeout 5 rostopic echo /interaction/features -n 1 || true

echo ""
echo "Checking false alerts for 5 seconds:"
timeout 5 rostopic echo /suspicion_event || true
