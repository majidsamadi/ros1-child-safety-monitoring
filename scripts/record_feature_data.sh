#!/usr/bin/env bash
set -eo pipefail

LABEL="${1:-}"
DURATION="${2:-30}"
OUT_DIR="${3:-data/feature_logs}"

if [ -z "$LABEL" ]; then
  echo "Usage: $0 LABEL [DURATION_SECONDS] [OUTPUT_DIR]"
  echo "Examples:"
  echo "  $0 normal_far 30"
  echo "  $0 normal_close 30"
  echo "  $0 normal_hug 30"
  echo "  $0 near_suspicious 30"
  echo "  $0 high_suspicious 30"
  exit 1
fi

cd "$(dirname "$0")/.."
source /opt/ros/noetic/setup.bash
source devel/setup.bash
mkdir -p "$OUT_DIR"

if ! rostopic list 2>/dev/null | grep -q '^/interaction/features$'; then
  echo "ERROR: /interaction/features is not available."
  echo "Start the robot pipeline first, for example:"
  echo "  ./scripts/run_ai_robot_stream_with_viewer.sh /dev/video2"
  exit 1
fi

echo "Recording feature data"
echo "  label:    $LABEL"
echo "  seconds:  $DURATION"
echo "  output:   $OUT_DIR"
echo "Perform the action now. Stop early with CTRL+C if needed."

set +e
timeout "$DURATION" roslaunch child_safety_monitoring feature_logger.launch label:="$LABEL" output_dir:="$OUT_DIR"
RC=$?
set -e

if [ "$RC" -ne 0 ] && [ "$RC" -ne 124 ]; then
  echo "Feature logger exited with code $RC"
  exit "$RC"
fi

echo "Done recording. Latest logs:"
ls -lt "$OUT_DIR" | head -10
