# ROS 1 Child Safety Monitoring Prototype

This project is a ROS 1 Noetic prototype for detecting suspicious child-lifting or forced-carrying movement patterns from a live camera feed.

The main objective is visible from the start:

```text
Camera input
  -> YOLO pose estimation
  -> person tracking
  -> interaction feature extraction
  -> feature-based AI risk model
  -> AI decision node
  -> alert/alarm output
```

The project supports two real working modes:

- **Laptop mode** for weekday development on macOS, Windows, and Linux using Docker and each teammate's laptop camera.
- **Jupiter robot mode** for Saturday testing and stakeholder demos using the Jupiter robot's ROS 1 Noetic environment.

It also includes a **safe simulator mode** for demonstrating `NORMAL -> WARNING -> HIGH ALERT` without risky acting.

Important wording: this is a suspicious movement-pattern detection prototype. It does not identify people, estimate real age, prove kidnapping, or infer intent. It produces warning signals for human review.

## Current status

Implemented:

- ROS 1 Noetic catkin workspace.
- Custom ROS messages for poses, interaction features, suspicion events, and AI risk predictions.
- Laptop webcam streaming for Docker mode.
- Jupiter robot camera topic support.
- YOLO Pose for human body keypoints.
- Person tracking with smaller/larger candidate role assignment.
- Interaction feature extraction.
- Feature-based AI risk model using a lightweight classifier.
- AI decision node with persistence and cooldown.
- Console alert output and alarm state output.
- Browser pose overlay using `web_video_server`.
- Feature logger and training script for improving the AI model.

Validated so far:

- The ROS 1 workspace builds with `catkin_make`.
- The simulator demo runs on the Jupiter robot.
- The simulator produces normal, warning, and high-alert states.

Still needs live tuning:

- Real robot camera high-risk behavior validation.
- More labeled feature logs from safe staged tests.
- Retraining the AI model with the team's own collected data.

## System architecture

### Laptop development mode

```text
Laptop webcam
  -> host_webcam_streamer.py
  -> HTTP stream: http://host.docker.internal:8090/video
  -> ROS 1 Docker container
  -> cctv_stream_node.py
  -> /camera/image_raw
  -> pose_estimator_node.py
  -> /poses/raw
  -> tracker_node.py
  -> /poses/tracked
  -> interaction_analyzer_node.py
  -> /interaction/features
  -> risk_model_node.py
  -> /risk_model/prediction
  -> ai_decision_node.py
  -> /suspicion_event
  -> alert_console_node.py + alarm_node.py
```

### Jupiter robot mode

```text
Jupiter robot camera topic
  -> pose_estimator_node.py
  -> /poses/raw
  -> tracker_node.py
  -> /poses/tracked
  -> interaction_analyzer_node.py
  -> /interaction/features
  -> risk_model_node.py
  -> /risk_model/prediction
  -> ai_decision_node.py
  -> /suspicion_event
  -> alert_console_node.py + alarm_node.py
```

### Simulator mode

```text
scenario_simulator_node.py
  -> /interaction/features
  -> risk_model_node.py
  -> /risk_model/prediction
  -> ai_decision_node.py
  -> /suspicion_event
  -> alert_console_node.py + alarm_node.py
```

The simulator is the safest way to demonstrate warning and high-alert behavior.

## Algorithm flow

### 1. Pose estimation

`pose_estimator_node.py` uses YOLO Pose to detect people and body keypoints.

It publishes:

- `/poses/raw`
- `/camera/pose_overlay`

Keypoints include shoulders, elbows, wrists, hips, knees, and ankles.

### 2. Tracking and role assignment

`tracker_node.py` assigns stable IDs such as `track_1` and `track_2`.

It assigns roles:

- `smaller_candidate`
- `larger_candidate`
- `bystander`

The system does not estimate true age. It only uses relative body size for the prototype.

### 3. Interaction features

`interaction_analyzer_node.py` calculates interpretable features:

```text
torso_distance_norm
wrap_score
lift_score
feet_off_ground_score
limb_speed_score
limb_accel_score
co_motion_score
suspicion_score
state
```

These features describe closeness, possible holding posture, upward movement, feet-off-ground evidence, rapid limb motion, and movement together.

### 4. Feature-based AI risk model

`risk_model_node.py` receives `/interaction/features` and publishes `/risk_model/prediction`.

The AI model is Version 1: a lightweight feature-based classifier. This is intentional because it is fast, explainable, and more realistic for the Jupiter robot CPU than a large video model.

The model outputs:

```text
label: normal / warning / high
probability_normal
probability_warning
probability_high
confidence
```

The current seed model is for engineering demonstration. It should later be retrained using real safe staged feature logs.

### 5. AI decision and alarm

`ai_decision_node.py` converts AI probabilities into `/suspicion_event`.

It uses:

- warning threshold,
- high threshold,
- persistence time,
- event cooldown.

`alert_console_node.py` prints readable status messages.

`alarm_node.py` publishes `/alarm/state`:

```text
ALARM_OFF
WARNING
HIGH_ALARM_ON
```

## Repository structure

```text
ros1-child-safety-monitoring/
├── README.md
├── README_ROS1_PORT.md
├── check_ros1_pipeline.sh
├── requirements_host.txt
├── data/
├── docs/
│   ├── ai_risk_model.md
│   └── environment_setup.md
├── scripts/
│   ├── check_existing_dependencies.sh
│   ├── setup_host_venv.sh
│   ├── setup_host_venv_windows.ps1
│   ├── setup_host_venv_windows.bat
│   ├── setup_ros1_python_deps.sh
│   ├── run_ros1_docker_dev.sh
│   ├── docker_setup_ros1_workspace.sh
│   ├── run_laptop_stream_demo.sh
│   ├── run_robot_demo.sh
│   ├── run_ai_robot_demo.sh
│   ├── run_ai_scenario_demo.sh
│   ├── run_overlay_viewer.sh
│   ├── log_features.sh
│   └── train_seed_risk_model.sh
└── src/
    ├── child_safety_msgs/
    │   └── msg/
    │       ├── PersonPose2D.msg
    │       ├── PersonPose2DArray.msg
    │       ├── InteractionFeatures.msg
    │       ├── RiskPrediction.msg
    │       └── SuspicionEvent.msg
    └── child_safety_monitoring/
        ├── config/
        ├── launch/
        ├── scripts/
        └── src/child_safety_monitoring/core/
```

## Important files

### Core ROS nodes

- `cctv_stream_node.py`: reads OpenCV video sources or HTTP/RTSP streams and publishes `/camera/image_raw`.
- `pose_estimator_node.py`: runs YOLO Pose and publishes `/poses/raw` and `/camera/pose_overlay`.
- `tracker_node.py`: assigns tracking IDs and smaller/larger roles.
- `interaction_analyzer_node.py`: calculates interaction features.
- `risk_model_node.py`: runs the feature-based AI classifier.
- `ai_decision_node.py`: converts AI predictions into warnings and high alerts.
- `alert_console_node.py`: prints readable output.
- `alarm_node.py`: publishes alarm state.
- `scenario_simulator_node.py`: safe simulator for normal, warning, and high-alert scenarios.
- `feature_logger_node.py`: logs feature vectors for AI training.
- `train_risk_model.py`: trains the feature-based risk model.

### Launch files

- `ai_scenario_demo.launch`: safe AI demo without camera.
- `ai_jupiter_robot_camera_demo.launch`: AI pipeline from robot camera topic.
- `ai_stream_demo.launch`: AI pipeline from stream URL.
- `jupiter_robot_camera_demo.launch`: older rule-based robot camera pipeline.
- `stream_demo.launch`: older rule-based stream pipeline.
- `view_overlay.launch`: browser overlay server.
- `feature_logger.launch`: feature logging for model training.

For final work, prefer the `ai_*` launch files.

## ROS topics

```text
/camera/image_raw
/camera/pose_overlay
/poses/raw
/poses/tracked
/interaction/features
/risk_model/prediction
/suspicion_event
/alarm/state
```

## Setup on the Jupiter robot

First check dependencies without changing the robot:

```bash
./scripts/check_existing_dependencies.sh
```

If the required packages are already present, avoid unnecessary system changes.

To install missing Python dependencies only for the current user:

```bash
python3 -m pip install --user -r src/child_safety_monitoring/requirements_ros1.txt
```

If torch is missing, install the optional CPU torch requirements:

```bash
python3 -m pip install --user -r src/child_safety_monitoring/requirements_torch_cpu_optional.txt
```

Build:

```bash
source /opt/ros/noetic/setup.bash
catkin_make
source devel/setup.bash
```

Train the seed model:

```bash
./scripts/train_seed_risk_model.sh
```

Run simulator AI demo:

```bash
./scripts/run_ai_scenario_demo.sh
```

Run robot AI demo:

```bash
./scripts/run_ai_robot_demo.sh /YOUR/CAMERA/TOPIC
```

Example:

```bash
./scripts/run_ai_robot_demo.sh /usb_cam/image_raw
```

## Setup on laptops

### Host webcam virtual environment

Use Python 3.10 for the host webcam streamer. Do not use Python 3.14.

macOS/Linux:

```bash
./scripts/setup_host_venv.sh
source .venv310/bin/activate
python scripts/host_webcam_streamer.py --camera 0 --port 8090
```

Windows PowerShell:

```powershell
.\scripts\setup_host_venv_windows.ps1
.\.venv310\Scripts\python.exe scripts\host_webcam_streamer.py --camera 0 --port 8090
```

Windows CMD:

```bat
scripts\setup_host_venv_windows.bat
.venv310\Scripts\python.exe scripts\host_webcam_streamer.py --camera 0 --port 8090
```

Check:

```text
http://127.0.0.1:8090/video
```

### Docker ROS 1 mode

From the repo root:

```bash
./scripts/run_ros1_docker_dev.sh
```

Inside Docker:

```bash
bash scripts/docker_setup_ros1_workspace.sh
bash scripts/run_laptop_stream_demo.sh
```

For AI stream mode:

```bash
roslaunch child_safety_monitoring ai_stream_demo.launch stream_url:=http://host.docker.internal:8090/video
```

Overlay viewer:

```bash
./scripts/run_overlay_viewer.sh
```

Browser:

```text
http://localhost:8080/stream?topic=/camera/pose_overlay
```

## Collecting AI training data

Run the live pipeline first. Then label safe staged states:

```bash
./scripts/log_features.sh normal
./scripts/log_features.sh warning
./scripts/log_features.sh high
```

Only use safe staged movements. Do not lift anyone or create risky situations.

Retrain:

```bash
python3 src/child_safety_monitoring/scripts/train_risk_model.py --data-dir data/feature_logs
```

If there is not enough real data, train a seed demo model:

```bash
./scripts/train_seed_risk_model.sh
```

## Expected demo flow

For stakeholder demo, use two parts.

### Part 1: real robot live vision

Show:

- robot camera feed,
- YOLO pose overlay,
- tracked people,
- interaction features,
- no false alert during normal standing.

### Part 2: safe AI alert demo

Run:

```bash
./scripts/run_ai_scenario_demo.sh
```

Show:

```text
NORMAL -> WARNING -> HIGH ALERT
```

This proves the AI decision and alarm path without unsafe acting.

## Best-practice notes

- Keep the AI model lightweight for robot CPU performance.
- Keep feature extraction explainable.
- Use persistence and cooldown to reduce false alarms.
- Keep model metadata and feature order with the saved model.
- Do not claim the model proves kidnapping or intent.
- Do not claim the model detects real age.
- Treat the output as a warning signal for human review.

## Current limitations

- The seed AI model is only for engineering demo.
- Real performance depends on camera angle and pose quality.
- More safe staged feature logs are needed for a stronger model.
- Feet-off-ground is a 2D proxy, not real 3D height.
- The robot demo should use safe normal movement plus simulator alerts.

## Useful checks

```bash
rosnode list
rostopic list
rostopic hz /poses/raw
rostopic hz /poses/tracked
rostopic hz /interaction/features
rostopic echo /risk_model/prediction -n 1
rostopic echo /suspicion_event
rostopic echo /alarm/state
```

## Safety and ethics

This project is for robotics class demonstration and learning.

Do not test with dangerous actions. Do not perform forceful acting. Do not record people without consent. Do not present the output as proof of a crime.

Correct description:

```text
A ROS-based suspicious movement-pattern detection prototype using pose estimation and feature-based AI risk classification.
```
