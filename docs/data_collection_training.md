# Data Collection and AI Training Workflow

The AI model will not reliably detect real robot-camera actions until it is trained with real feature data from the Jupiter robot camera.

The project already has the live pipeline:

```text
robot camera
-> YOLO Pose
-> tracker
-> interaction_analyzer_node
-> /interaction/features
-> risk_model_node
-> /risk_model/prediction
-> ai_decision_node
-> alerts
```

The data collection workflow records `/interaction/features` with labels, then trains `risk_model.joblib` from those logs.

## Labels to collect

Use adult volunteers and safe staged actions only.

Collect at least 20-30 seconds for each label:

```text
normal_far
normal_close
normal_hug
near_suspicious
high_suspicious
```

### normal_far

Two people stand far apart and move normally.

### normal_close

Two people stand close without sudden movement.

### normal_hug

A calm, normal hug. This is important because the model must learn that a normal hug is not suspicious.

### near_suspicious

A larger person approaches quickly and raises arms near the smaller person, without grabbing or lifting.

### high_suspicious

Safe adult-only staged action: close approach, arms around upper-body area, rapid arm/leg movement, and both people move together for one or two steps. Do not lift anyone.

## Method A: pipeline already running

Terminal 1:

```bash
./scripts/run_ai_robot_stream_with_viewer.sh /dev/video2
```

Terminal 2:

```bash
./scripts/record_feature_data.sh normal_far 30
./scripts/record_feature_data.sh normal_close 30
./scripts/record_feature_data.sh normal_hug 30
./scripts/record_feature_data.sh near_suspicious 30
./scripts/record_feature_data.sh high_suspicious 30
```

## Method B: start camera and record in one command

```bash
./scripts/record_feature_data_with_camera.sh normal_far 30 /dev/video2
./scripts/record_feature_data_with_camera.sh normal_close 30 /dev/video2
./scripts/record_feature_data_with_camera.sh normal_hug 30 /dev/video2
./scripts/record_feature_data_with_camera.sh near_suspicious 30 /dev/video2
./scripts/record_feature_data_with_camera.sh high_suspicious 30 /dev/video2
```

## Train the AI model

```bash
./scripts/train_robot_ai_model.sh
```

This writes:

```text
src/child_safety_monitoring/models/risk_model.joblib
src/child_safety_monitoring/models/risk_model.json
```

## Test the model

```bash
./scripts/run_ai_robot_stream_with_viewer.sh /dev/video2
```

In another terminal:

```bash
./scripts/run_ai_debug_console.sh
```

Watch how these values change:

```text
dist
wrap
lift
feet
limb
co
pN
pW
pH
```

## Safety rule

Do not test by lifting a real child. Use adult volunteers or a dummy/mannequin for staged high-risk movement.
