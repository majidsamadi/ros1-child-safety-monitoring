# Feature-Based AI Risk Model

This project uses AI in two stages.

The first AI stage is YOLO Pose. It detects people and body keypoints from camera frames.

The second AI stage is a feature-based risk classifier. It receives interpretable interaction features and predicts `normal`, `warning`, or `high`.

## Why this model type?

The Jupiter robot needs a fast model. A full video action-recognition model would be harder to train and heavier to run. A feature-based classifier is more practical for the current project.

Benefits:

- fast on CPU,
- easier to train with small data,
- easier to explain,
- works with the features already produced by the ROS pipeline.

## Features

The classifier uses:

```text
torso_distance_norm
wrap_score
lift_score
feet_off_ground_score
limb_speed_score
limb_accel_score
co_motion_score
```

These features are published by `interaction_analyzer_node.py` on `/interaction/features`.

## Model output

`risk_model_node.py` publishes `/risk_model/prediction` with:

```text
label
confidence
probability_normal
probability_warning
probability_high
model_version
explanation
```

## Decision logic

`ai_decision_node.py` applies:

- probability thresholds,
- time persistence,
- event cooldown.

This prevents one bad frame from triggering an alert.

## Training workflow

Start with seed model:

```bash
./scripts/train_seed_risk_model.sh
```

Collect safe data:

```bash
./scripts/log_features.sh normal
./scripts/log_features.sh warning
./scripts/log_features.sh high
```

Retrain:

```bash
python3 src/child_safety_monitoring/scripts/train_risk_model.py --data-dir data/feature_logs
```

## Important limitation

The seed model is not a real validated safety model. It is for demonstration and engineering tests. Real performance requires more labeled feature logs from safe staged scenarios.
