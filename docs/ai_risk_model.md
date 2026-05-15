# Feature-Based AI Risk Model

This project now has two AI stages:

1. **YOLO Pose** detects people and body keypoints.
2. **Feature-based AI risk model** classifies interaction risk using features over time.

The AI risk model is Version 1 because it is fast, explainable, and practical on the Jupiter robot.

## Input features

The model receives these values from `/interaction/features`:

```text
torso_distance_norm
wrap_score
lift_score
feet_off_ground_score
limb_speed_score
limb_accel_score
co_motion_score
```

## Output

The model publishes `/risk_model/prediction`:

```text
label: normal / warning / high
probability_normal
probability_warning
probability_high
confidence
```

Then `ai_decision_node.py` converts AI predictions into `/suspicion_event`.

## Training

Train a seed demo model:

```bash
./scripts/train_seed_risk_model.sh
```

This creates:

```text
src/child_safety_monitoring/models/risk_model.joblib
src/child_safety_monitoring/models/risk_model.json
```

The seed model is for engineering/demo only. For final tuning, collect safe staged feature logs.

## Collecting safe data

Run the live pipeline, then in another terminal:

```bash
./scripts/log_features.sh normal
./scripts/log_features.sh warning
./scripts/log_features.sh high
```

Only use safe staged movements. Do not lift anyone or perform risky actions.

## AI demo launch files

Simulator AI demo:

```bash
roslaunch child_safety_monitoring ai_scenario_demo.launch
```

Robot camera AI demo:

```bash
roslaunch child_safety_monitoring ai_jupiter_robot_camera_demo.launch camera_topic:=/YOUR/CAMERA/TOPIC
```
