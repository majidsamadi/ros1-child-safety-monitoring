#!/usr/bin/env bash
set -eo pipefail

LABEL="${1:-}"
SECONDS_TO_RECORD="${2:-30}"

if [ -z "$LABEL" ]; then
  echo "Usage: ./scripts/record_feature_data.sh <label> [seconds]"
  echo "Example: ./scripts/record_feature_data.sh normal_far 30"
  exit 1
fi

cd "$(dirname "$0")/.."

source /opt/ros/noetic/setup.bash
source devel/setup.bash

OUTPUT_DIR="$(pwd)/data/feature_logs"
mkdir -p "$OUTPUT_DIR"

echo "Recording feature data"
echo "  label:    $LABEL"
echo "  seconds:  $SECONDS_TO_RECORD"
echo "  output:   $OUTPUT_DIR"
echo "Perform the action now. Stop early with CTRL+C if needed."

timeout "$SECONDS_TO_RECORD" roslaunch child_safety_monitoring feature_logger.launch \
  label:="$LABEL" \
  output_dir:="$OUTPUT_DIR" || true

echo "Done recording. Latest logs:"
ls -lh "$OUTPUT_DIR" | tail -10
