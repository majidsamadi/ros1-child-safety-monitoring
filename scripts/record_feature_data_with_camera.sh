#!/usr/bin/env bash
set -eo pipefail

LABEL="${1:-}"
DURATION="${2:-30}"
CAMERA="${3:-/dev/video2}"
OUT_DIR="${4:-data/feature_logs}"

if [ -z "$LABEL" ]; then
  echo "Usage: $0 LABEL [DURATION_SECONDS] [CAMERA] [OUTPUT_DIR]"
  echo "Example: $0 normal_close 30 /dev/video2"
  exit 1
fi

cd "$(dirname "$0")/.."
source /opt/ros/noetic/setup.bash
source devel/setup.bash
mkdir -p "$OUT_DIR"

echo "Starting AI robot pipeline using camera: $CAMERA"
roslaunch child_safety_monitoring ai_stream_demo.launch stream_url:="$CAMERA" > /tmp/child_safety_record_pipeline.log 2>&1 &
PIPELINE_PID=$!

cleanup() {
  echo "Stopping pipeline..."
  kill "$PIPELINE_PID" 2>/dev/null || true
  sleep 1
  pkill -P "$PIPELINE_PID" 2>/dev/null || true
}
trap cleanup EXIT

for i in $(seq 1 40); do
  if rostopic list 2>/dev/null | grep -q '^/interaction/features$'; then
    break
  fi
  sleep 0.5
  if ! kill -0 "$PIPELINE_PID" 2>/dev/null; then
    echo "Pipeline exited early. Log:"
    cat /tmp/child_safety_record_pipeline.log
    exit 1
  fi
done

if ! rostopic list 2>/dev/null | grep -q '^/interaction/features$'; then
  echo "ERROR: /interaction/features did not appear. Pipeline log:"
  cat /tmp/child_safety_record_pipeline.log
  exit 1
fi

echo "Pipeline ready. Recording label=$LABEL for ${DURATION}s."
timeout "$DURATION" roslaunch child_safety_monitoring feature_logger.launch label:="$LABEL" output_dir:="$OUT_DIR" || true

echo "Done. Latest logs:"
ls -lt "$OUT_DIR" | head -10
