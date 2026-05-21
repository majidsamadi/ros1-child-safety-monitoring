#!/usr/bin/env bash
set -eo pipefail

DATA_DIR="${1:-data/feature_logs}"
OUTPUT="${2:-src/child_safety_monitoring/models/risk_model.joblib}"

cd "$(dirname "$0")/.."
source /opt/ros/noetic/setup.bash
source devel/setup.bash
mkdir -p "$(dirname "$OUTPUT")"

echo "Training AI risk model"
echo "  data:   $DATA_DIR"
echo "  output: $OUTPUT"
python3 src/child_safety_monitoring/scripts/train_risk_model.py --data-dir "$DATA_DIR" --output "$OUTPUT"

echo "Model files:"
ls -lh "$(dirname "$OUTPUT")"
