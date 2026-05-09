# ROS 1 Child Safety Monitoring Prototype

A ROS 1 Noetic project for detecting **suspicious child-lifting / forced-carrying movement patterns** from a live camera feed.

This project is designed for a team workflow where the robot is only available sometimes:

- **Laptop development mode**: used during the week by team members on macOS, Windows, or Linux. The project runs in a ROS 1 Docker container and uses each laptop's webcam.
- **Jupiter robot mode**: used when the Jupiter robot is available. The project runs directly on the robot using ROS 1 Noetic and the robot camera topic.
- **Simulator mode**: used as a safe backup demo for showing `NORMAL → WARNING → HIGH ALERT` without needing a camera or risky acting.

The final stakeholder demo should be done on the **Jupiter robot**, but most development can happen on laptops.

> Important: this is a robotics class prototype. It does **not** identify people, estimate real age, prove kidnapping, or infer criminal intent. It only detects suspicious movement patterns and should always be treated as a human-reviewed safety signal.

---

## Table of contents

1. [Project goal](#project-goal)
2. [Current project status](#current-project-status)
3. [Main idea](#main-idea)
4. [System modes](#system-modes)
5. [High-level pipeline](#high-level-pipeline)
6. [Algorithm overview](#algorithm-overview)
7. [Repository structure](#repository-structure)
8. [ROS topics and messages](#ros-topics-and-messages)
9. [Laptop mode: macOS](#laptop-mode-macos)
10. [Laptop mode: Windows](#laptop-mode-windows)
11. [Laptop mode: Linux](#laptop-mode-linux)
12. [Jupiter robot mode](#jupiter-robot-mode)
13. [Simulator backup demo](#simulator-backup-demo)
14. [How to check the pipeline](#how-to-check-the-pipeline)
15. [Expected demo behavior](#expected-demo-behavior)
16. [Troubleshooting](#troubleshooting)
17. [Team workflow](#team-workflow)
18. [Safety and ethics](#safety-and-ethics)
19. [Current limitations](#current-limitations)

---

## Project goal

The goal is to build a ROS-based child-safety monitoring prototype that watches a camera feed and detects suspicious interaction patterns involving two people:

- a **smaller candidate** person,
- a **larger candidate** person,
- sudden close interaction,
- possible holding/wrapping posture,
- possible upward movement,
- possible feet-off-ground signal,
- rapid limb movement,
- and a final warning/high-alert score.

The system should eventually trigger an alarm-like output when the movement pattern becomes suspicious.

The goal is **not** to make a legal or final decision. The output is a warning signal for review.

---

## Current project status

The ROS 1 repository supports:

- ROS 1 Noetic workspace structure.
- Custom ROS messages.
- Laptop webcam input through a small host webcam streamer.
- Robot camera input through an existing ROS image topic.
- YOLO pose estimation.
- Person tracking.
- Smaller/larger candidate assignment.
- Interaction feature extraction.
- Rule-based warning/high-alert decision logic.
- Console alert output.
- Alarm topic output.
- Browser visualization of pose overlay.
- Safe simulator demo.

The project can be run in two main ways:

```text
Laptop mode  → for normal development on Mac/Windows/Linux
Robot mode   → for final testing and stakeholder demo on Jupiter robot
```

---

## Main idea

The project uses the same detection pipeline in both laptop mode and robot mode. The only difference is the camera input.

### Laptop mode input

```text
Laptop webcam
    ↓
host_webcam_streamer.py
    ↓
HTTP stream: http://host.docker.internal:8090/video
    ↓
ROS 1 Docker container
```

### Robot mode input

```text
Jupiter robot camera ROS topic
    ↓
Example: /usb_cam/image_raw or /camera/rgb/image_raw
```

After the image enters ROS, the rest of the pipeline is the same.

---

## System modes

### 1. Laptop development mode

Use this when the robot is not available.

This mode is for:

- macOS users,
- Windows users,
- Linux users,
- testing the camera pipeline,
- developing the detection logic,
- showing browser pose overlay,
- checking normal/warning/high behavior.

The laptop camera is streamed outside Docker because Docker does not always access laptop webcams easily on macOS and Windows.

### 2. Jupiter robot mode

Use this when the robot is available.

This mode is for:

- Saturday testing,
- real robot demonstration,
- stakeholder demo,
- using the robot's ROS 1 camera topic.

The Jupiter robot already runs:

```text
Ubuntu 20.04
ROS 1 Noetic
catkin
rospy
```

So the final project is built around ROS 1.

### 3. Simulator mode

Use this when you want a safe demo without a camera.

The simulator publishes fake interaction features:

```text
NORMAL → WARNING → HIGH ALERT
```

This is useful for showing the decision and alarm system without asking anyone to perform risky movements.

---

## High-level pipeline

### Laptop mode pipeline

```text
Laptop webcam
        ↓
host_webcam_streamer.py
        ↓
HTTP video stream
        ↓
cctv_stream_node.py
        ↓
/camera/image_raw
        ↓
pose_estimator_node.py
        ↓
/poses/raw
        ↓
tracker_node.py
        ↓
/poses/tracked
        ↓
interaction_analyzer_node.py
        ↓
/interaction/features
        ↓
decision_node.py
        ↓
/suspicion_event
        ↓
alert_console_node.py + alarm_node.py
```

### Jupiter robot mode pipeline

```text
Jupiter robot camera topic
        ↓
pose_estimator_node.py
        ↓
/poses/raw
        ↓
tracker_node.py
        ↓
/poses/tracked
        ↓
interaction_analyzer_node.py
        ↓
/interaction/features
        ↓
decision_node.py
        ↓
/suspicion_event
        ↓
alert_console_node.py + alarm_node.py
```

---

## Algorithm overview

The system is intentionally rule-based and explainable. The final alert is not produced by a black-box classifier. Instead, the system calculates several interpretable features and combines them into a suspicion score.

### 1. Pose estimation

`pose_estimator_node.py` runs YOLO pose estimation on camera frames.

It detects people and body keypoints such as:

- nose,
- shoulders,
- elbows,
- wrists,
- hips,
- knees,
- ankles.

It publishes raw pose detections on:

```text
/poses/raw
```

It also publishes a visual overlay image on:

```text
/camera/pose_overlay
```

This overlay is used in the browser to verify that the system can see the people and their skeletons.

### 2. Tracking

`tracker_node.py` takes raw pose detections and assigns stable track IDs:

```text
track_1
track_2
track_3
...
```

It also assigns roles:

```text
smaller_candidate
larger_candidate
bystander
```

This is based on relative bounding-box size/height, not true age.

Important: the project does **not** estimate age. It only says “smaller candidate” and “larger candidate” for the purpose of the prototype.

Tracked poses are published on:

```text
/poses/tracked
```

### 3. Interaction feature extraction

`interaction_analyzer_node.py` compares the smaller and larger candidates.

It calculates:

| Feature | Meaning |
|---|---|
| `torso_distance_norm` | Normalized distance between the two people |
| `wrap_score` | Whether the larger person's wrists are near the smaller person's torso |
| `lift_score` | Whether the smaller candidate moves upward over time |
| `feet_off_ground_score` | Whether ankles/feet appear above the bottom of the body box, capped unless lift is detected |
| `limb_speed_score` | Rapid movement of smaller candidate's limbs |
| `limb_accel_score` | Sudden acceleration of smaller candidate's limb movement |
| `co_motion_score` | Reserved for future adult-child joint movement scoring |
| `suspicion_score` | Weighted combination of all cues |
| `state` | `observing`, `watch`, `warning`, or `high_alert` |

Interaction features are published on:

```text
/interaction/features
```

### 4. Suspicion scoring

The current weighted score is:

```text
score =
    0.20 * close_contact
  + 0.15 * wrap_score
  + 0.25 * lift_score
  + 0.15 * feet_off_ground_score
  + 0.15 * struggle_score
  + 0.10 * co_motion_score
```

The state is selected using score thresholds:

```text
score < 0.25       → observing
score >= 0.25      → watch
score >= 0.55      → warning
score >= 0.75      → high_alert
```

The decision node also uses persistence, meaning it does not jump to high alert from a single frame. The suspicious score must remain high long enough.

### 5. Decision and alert

`decision_node.py` subscribes to:

```text
/interaction/features
```

It publishes alert events on:

```text
/suspicion_event
```

`alert_console_node.py` prints readable messages like:

```text
[NORMAL] score=0.00 | No suspicious interaction pattern detected
[WARNING] score=0.62 | Suspicious interaction pattern detected
[HIGH ALERT] score=0.92 | Suspicious child-lifting pattern detected
```

`alarm_node.py` publishes alarm state on:

```text
/alarm/state
```

---

## Repository structure

```text
ros1-child-safety-monitoring/
│
├── README.md
├── README_ROS1_PORT.md
├── check_ros1_pipeline.sh
├── .gitignore
│
├── data/
│   ├── debug_clips/
│   ├── rosbags/
│   └── videos/
│
└── src/
    ├── child_safety_msgs/
    │   ├── package.xml
    │   ├── CMakeLists.txt
    │   └── msg/
    │       ├── PersonPose2D.msg
    │       ├── PersonPose2DArray.msg
    │       ├── InteractionFeatures.msg
    │       └── SuspicionEvent.msg
    │
    └── child_safety_monitoring/
        ├── package.xml
        ├── CMakeLists.txt
        ├── setup.py
        ├── requirements_ros1.txt
        │
        ├── config/
        │   └── detection_params.yaml
        │
        ├── launch/
        │   ├── jupiter_robot_camera_demo.launch
        │   ├── stream_demo.launch
        │   ├── scenario_demo.launch
        │   └── view_overlay.launch
        │
        ├── scripts/
        │   ├── host_webcam_streamer.py
        │   ├── cctv_stream_node.py
        │   ├── pose_estimator_node.py
        │   ├── tracker_node.py
        │   ├── interaction_analyzer_node.py
        │   ├── decision_node.py
        │   ├── alert_console_node.py
        │   ├── alarm_node.py
        │   └── scenario_simulator_node.py
        │
        └── src/
            └── child_safety_monitoring/
                ├── __init__.py
                └── core/
                    ├── geometry.py
                    ├── keypoints.py
                    ├── scoring.py
                    └── centroid_tracker.py
```

---

## File-by-file explanation

### Root files

| File | Purpose |
|---|---|
| `README.md` | Main project documentation |
| `README_ROS1_PORT.md` | Notes about ROS 2 to ROS 1 porting |
| `check_ros1_pipeline.sh` | Quick health check for nodes/topics |
| `.gitignore` | Prevents build files, cache files, videos, and secrets from being committed |

### `child_safety_msgs`

| File | Purpose |
|---|---|
| `PersonPose2D.msg` | One detected/tracked person, bounding box, keypoints, confidence, role |
| `PersonPose2DArray.msg` | List of detected/tracked people |
| `InteractionFeatures.msg` | Output of the interaction analyzer |
| `SuspicionEvent.msg` | Warning/high-alert event output |

### `child_safety_monitoring/scripts`

| Script | Purpose |
|---|---|
| `host_webcam_streamer.py` | Runs outside Docker and streams laptop webcam as MJPEG |
| `cctv_stream_node.py` | Reads HTTP/RTSP stream and publishes `/camera/image_raw` |
| `pose_estimator_node.py` | Runs YOLO pose detection and publishes `/poses/raw` + `/camera/pose_overlay` |
| `tracker_node.py` | Assigns track IDs and smaller/larger candidate roles |
| `interaction_analyzer_node.py` | Computes suspicious interaction features |
| `decision_node.py` | Converts suspicion score into warning/high alert events |
| `alert_console_node.py` | Prints clean alert messages in terminal |
| `alarm_node.py` | Publishes alarm state |
| `scenario_simulator_node.py` | Publishes fake features for safe demo/testing |

### Launch files

| Launch file | Purpose |
|---|---|
| `jupiter_robot_camera_demo.launch` | Runs the full pipeline from a robot ROS image topic |
| `stream_demo.launch` | Runs the full pipeline from an HTTP/RTSP stream |
| `scenario_demo.launch` | Runs simulator + decision + alert + alarm without a camera |
| `view_overlay.launch` | Starts web video server so `/camera/pose_overlay` can be viewed in a browser |

---

## ROS topics and messages

| Topic | Type | Publisher | Subscriber | Purpose |
|---|---|---|---|---|
| `/camera/image_raw` | `sensor_msgs/Image` | camera/stream node | pose estimator | Raw camera frame |
| `/camera/pose_overlay` | `sensor_msgs/Image` | pose estimator | web video server | Camera image with YOLO pose overlay |
| `/poses/raw` | `child_safety_msgs/PersonPose2DArray` | pose estimator | tracker | Raw detected poses |
| `/poses/tracked` | `child_safety_msgs/PersonPose2DArray` | tracker | interaction analyzer | Tracked people with roles |
| `/interaction/features` | `child_safety_msgs/InteractionFeatures` | interaction analyzer | decision/alert/alarm | Suspicion features |
| `/suspicion_event` | `child_safety_msgs/SuspicionEvent` | decision node | alert/alarm | Warning/high-alert events |
| `/alarm/state` | `std_msgs/String` | alarm node | optional output | Alarm state |

---

# Laptop mode: macOS

Use this mode for MacBook development when the robot is not available.

## macOS requirements

Install:

- Git
- Python 3
- Docker Desktop
- VS Code or Terminal

If macOS blocks camera access in normal Terminal, run the webcam streamer from **VS Code Terminal** and allow camera access for VS Code in:

```text
System Settings → Privacy & Security → Camera
```

## Step 1: clone the repo

```bash
mkdir -p "$HOME/Master AI/Robotics/ros1"
cd "$HOME/Master AI/Robotics/ros1"

git clone https://github.com/majidsamadi/ros1-child-safety-monitoring.git
cd ros1-child-safety-monitoring
```

## Step 2: start laptop webcam streamer

Run this outside Docker:

```bash
python3 -m pip install --user "numpy==1.26.4" "opencv-python==4.10.0.84"
python3 src/child_safety_monitoring/scripts/host_webcam_streamer.py --camera 0 --port 8090
```

Keep this terminal open.

Open this browser link:

```text
http://127.0.0.1:8090/video
```

You should see your webcam.

If camera `0` does not work:

```bash
python3 src/child_safety_monitoring/scripts/host_webcam_streamer.py --camera 1 --port 8090
```

## Step 3: start ROS 1 Docker container

Open another terminal:

```bash
cd "$HOME/Master AI/Robotics/ros1/ros1-child-safety-monitoring"

docker rm -f ros1-child-safety-dev 2>/dev/null || true

docker run -it --rm \
  --name ros1-child-safety-dev \
  -p 8080:8080 \
  -v "$PWD:/root/catkin_ws" \
  osrf/ros:noetic-desktop-full \
  bash
```

## Step 4: install and build inside Docker

Inside Docker:

```bash
cd /root/catkin_ws
source /opt/ros/noetic/setup.bash

apt update
apt install -y \
  python3-pip \
  python3-opencv \
  ros-noetic-cv-bridge \
  ros-noetic-image-transport \
  ros-noetic-web-video-server

python3 -m pip install -r src/child_safety_monitoring/requirements_ros1.txt

catkin_make
source devel/setup.bash
```

## Step 5: run laptop camera demo

Inside Docker:

```bash
roslaunch child_safety_monitoring stream_demo.launch stream_url:=http://host.docker.internal:8090/video
```

Keep this running.

## Step 6: view YOLO pose overlay

Open another terminal:

```bash
docker exec -it ros1-child-safety-dev bash
```

Inside Docker:

```bash
cd /root/catkin_ws
source /opt/ros/noetic/setup.bash
source devel/setup.bash
roslaunch child_safety_monitoring view_overlay.launch
```

Open in browser:

```text
http://localhost:8080/stream?topic=/camera/pose_overlay
```

---

# Laptop mode: Windows

Use this mode for the Windows teammate.

## Windows requirements

Install:

- Git for Windows
- Python 3
- Docker Desktop
- WSL 2 backend enabled in Docker Desktop

## Step 1: clone the repo

Open **PowerShell**:

```powershell
mkdir "$HOME\Documents\Robotics" -Force
cd "$HOME\Documents\Robotics"

git clone https://github.com/majidsamadi/ros1-child-safety-monitoring.git
cd ros1-child-safety-monitoring
```

## Step 2: start laptop webcam streamer

Run outside Docker in PowerShell:

```powershell
py -3 -m pip install --user "numpy==1.26.4" "opencv-python==4.10.0.84"
py -3 src\child_safety_monitoring\scripts\host_webcam_streamer.py --camera 0 --port 8090
```

Keep this terminal open.

Open in browser:

```text
http://127.0.0.1:8090/video
```

If camera `0` does not work:

```powershell
py -3 src\child_safety_monitoring\scripts\host_webcam_streamer.py --camera 1 --port 8090
```

## Step 3: start Docker

Open another PowerShell terminal:

```powershell
cd "$HOME\Documents\Robotics\ros1-child-safety-monitoring"

docker rm -f ros1-child-safety-dev 2>$null

docker run -it --rm `
  --name ros1-child-safety-dev `
  -p 8080:8080 `
  -v "${PWD}:/root/catkin_ws" `
  osrf/ros:noetic-desktop-full `
  bash
```

## Step 4: install and build inside Docker

Inside Docker:

```bash
cd /root/catkin_ws
source /opt/ros/noetic/setup.bash

apt update
apt install -y \
  python3-pip \
  python3-opencv \
  ros-noetic-cv-bridge \
  ros-noetic-image-transport \
  ros-noetic-web-video-server

python3 -m pip install -r src/child_safety_monitoring/requirements_ros1.txt

catkin_make
source devel/setup.bash
```

## Step 5: run laptop camera demo

Inside Docker:

```bash
roslaunch child_safety_monitoring stream_demo.launch stream_url:=http://host.docker.internal:8090/video
```

## Step 6: view overlay

Open another PowerShell terminal:

```powershell
docker exec -it ros1-child-safety-dev bash
```

Inside Docker:

```bash
cd /root/catkin_ws
source /opt/ros/noetic/setup.bash
source devel/setup.bash
roslaunch child_safety_monitoring view_overlay.launch
```

Open in browser:

```text
http://localhost:8080/stream?topic=/camera/pose_overlay
```

---

# Laptop mode: Linux

Linux users can run either with Docker or native ROS 1 Noetic.

## Option A: Linux with Docker

Clone:

```bash
mkdir -p ~/Robotics
cd ~/Robotics

git clone https://github.com/majidsamadi/ros1-child-safety-monitoring.git
cd ros1-child-safety-monitoring
```

Start laptop webcam streamer outside Docker:

```bash
python3 -m pip install --user "numpy==1.26.4" "opencv-python==4.10.0.84"
python3 src/child_safety_monitoring/scripts/host_webcam_streamer.py --camera 0 --port 8090
```

Check browser:

```text
http://127.0.0.1:8090/video
```

Start Docker:

```bash
docker rm -f ros1-child-safety-dev 2>/dev/null || true

docker run -it --rm \
  --name ros1-child-safety-dev \
  --add-host=host.docker.internal:host-gateway \
  -p 8080:8080 \
  -v "$PWD:/root/catkin_ws" \
  osrf/ros:noetic-desktop-full \
  bash
```

Then inside Docker:

```bash
cd /root/catkin_ws
source /opt/ros/noetic/setup.bash

apt update
apt install -y \
  python3-pip \
  python3-opencv \
  ros-noetic-cv-bridge \
  ros-noetic-image-transport \
  ros-noetic-web-video-server

python3 -m pip install -r src/child_safety_monitoring/requirements_ros1.txt
catkin_make
source devel/setup.bash

roslaunch child_safety_monitoring stream_demo.launch stream_url:=http://host.docker.internal:8090/video
```

## Option B: Linux with native ROS Noetic

If the Linux teammate has Ubuntu 20.04 and ROS Noetic installed:

```bash
mkdir -p ~/Robotics
cd ~/Robotics

git clone https://github.com/majidsamadi/ros1-child-safety-monitoring.git
cd ros1-child-safety-monitoring

source /opt/ros/noetic/setup.bash

sudo apt update
sudo apt install -y \
  python3-pip \
  python3-opencv \
  ros-noetic-cv-bridge \
  ros-noetic-image-transport \
  ros-noetic-web-video-server

python3 -m pip install --user -r src/child_safety_monitoring/requirements_ros1.txt

catkin_make
source devel/setup.bash
```

Then use either a camera stream:

```bash
python3 src/child_safety_monitoring/scripts/host_webcam_streamer.py --camera 0 --port 8090
```

and:

```bash
roslaunch child_safety_monitoring stream_demo.launch stream_url:=http://127.0.0.1:8090/video
```

or use a native ROS camera topic if one exists.

---

# Jupiter robot mode

Use this mode for Saturday testing and stakeholder demo.

The Jupiter robot is already ROS 1 Noetic on Ubuntu 20.04.

## Step 1: clone the repo on the robot

On the robot:

```bash
cd ~
git clone https://github.com/majidsamadi/ros1-child-safety-monitoring.git
cd ros1-child-safety-monitoring
```

If the repo already exists:

```bash
cd ~/ros1-child-safety-monitoring
git pull
```

## Step 2: install dependencies on the robot

```bash
sudo apt update
sudo apt install -y \
  python3-pip \
  python3-opencv \
  ros-noetic-cv-bridge \
  ros-noetic-image-transport \
  ros-noetic-web-video-server

python3 -m pip install --user -r src/child_safety_monitoring/requirements_ros1.txt
```

## Step 3: build

```bash
cd ~/ros1-child-safety-monitoring
source /opt/ros/noetic/setup.bash
catkin_make
source devel/setup.bash
```

## Step 4: start robot camera

Start the Jupiter robot camera using the normal Jupiter robot bringup/camera launch.

Then check image topics:

```bash
rostopic list | grep -i image
rostopic list | grep -i camera
```

Common examples might be:

```text
/usb_cam/image_raw
/camera/rgb/image_raw
/jupiter/camera/image_raw
```

Use the real topic from the robot.

## Step 5: run robot demo

```bash
cd ~/ros1-child-safety-monitoring
source /opt/ros/noetic/setup.bash
source devel/setup.bash

roslaunch child_safety_monitoring jupiter_robot_camera_demo.launch camera_topic:=/YOUR/CAMERA/TOPIC
```

Example:

```bash
roslaunch child_safety_monitoring jupiter_robot_camera_demo.launch camera_topic:=/usb_cam/image_raw
```

## Step 6: view robot overlay

Open another robot terminal:

```bash
cd ~/ros1-child-safety-monitoring
source /opt/ros/noetic/setup.bash
source devel/setup.bash
roslaunch child_safety_monitoring view_overlay.launch
```

Find robot IP:

```bash
hostname -I
```

Open in browser from your laptop:

```text
http://ROBOT_IP:8080/stream?topic=/camera/pose_overlay
```

If you use a browser directly on the robot:

```text
http://localhost:8080/stream?topic=/camera/pose_overlay
```

---

# Simulator backup demo

Use this when:

- the robot is not available,
- the camera is not working,
- you need a safe high-alert demo,
- you want to show the decision/alarm pipeline.

Run:

```bash
cd ~/ros1-child-safety-monitoring
source /opt/ros/noetic/setup.bash
source devel/setup.bash
roslaunch child_safety_monitoring scenario_demo.launch
```

Expected output:

```text
[NORMAL] score=0.10
[WARNING] score=0.62
[HIGH ALERT] score=0.92
```

This demo does not use a camera.

---

## How to check the pipeline

Use these commands in a sourced terminal:

```bash
source /opt/ros/noetic/setup.bash
source devel/setup.bash
```

List nodes:

```bash
rosnode list
```

Expected live nodes:

```text
/cctv_stream_node or robot camera driver
/pose_estimator_node
/tracker_node
/interaction_analyzer_node
/decision_node
/alert_console_node
/alarm_node
```

List topics:

```bash
rostopic list
```

Expected topics:

```text
/camera/image_raw
/camera/pose_overlay
/poses/raw
/poses/tracked
/interaction/features
/suspicion_event
/alarm/state
```

Check pose detection:

```bash
rostopic hz /poses/raw
```

Check tracking:

```bash
rostopic hz /poses/tracked
```

Check interaction features:

```bash
rostopic hz /interaction/features
rostopic echo /interaction/features -n 1
```

Check alerts:

```bash
rostopic echo /suspicion_event
```

For normal standing, expected:

```text
suspicion_score: 0.0
state: observing
```

and no `/suspicion_event` output.

---

## Expected demo behavior

### Normal behavior

Two people standing normally:

```text
suspicion_score: near 0
state: observing
no alert
```

### People standing closer

Two people move closer:

```text
torso_distance_norm should decrease
state may become watch
no high alert unless other suspicious signals exist
```

### Safe simulated alert

For high-alert demonstration, use:

```bash
roslaunch child_safety_monitoring scenario_demo.launch
```

This avoids unsafe acting.

---

## Troubleshooting

### `rospack` cannot find package

Run:

```bash
cd ~/ros1-child-safety-monitoring
source /opt/ros/noetic/setup.bash
catkin_make
source devel/setup.bash
```

Then try again.

### Webcam does not open on macOS

Use VS Code Terminal instead of normal Terminal, and allow camera access:

```text
System Settings → Privacy & Security → Camera → Visual Studio Code
```

### Browser overlay is blank

Check if the overlay topic exists:

```bash
rostopic list | grep pose_overlay
```

Check if images are publishing:

```bash
rostopic hz /camera/pose_overlay
```

Start web video server:

```bash
roslaunch child_safety_monitoring view_overlay.launch
```

Open:

```text
http://localhost:8080/stream?topic=/camera/pose_overlay
```

### `/interaction/features` does not publish

Possible reasons:

- only one person is visible,
- one skeleton is only partially visible,
- the tracker has not assigned smaller/larger candidates yet,
- `interaction_analyzer_node` is not running.

Check:

```bash
rosnode list | grep interaction
rostopic hz /poses/tracked
rostopic echo /poses/tracked -n 1
```

### Docker cannot read laptop stream

Make sure the host webcam stream is open in browser:

```text
http://127.0.0.1:8090/video
```

Then test inside Docker:

```bash
python3 - <<'PY'
import cv2
cap = cv2.VideoCapture('http://host.docker.internal:8090/video')
print('opened:', cap.isOpened())
PY
```

On Linux Docker, start the container with:

```bash
--add-host=host.docker.internal:host-gateway
```

### PyTorch or YOLO is slow

This is expected on CPU. For a class demo, use:

```text
yolo11n-pose.pt
```

It is the smaller/faster pose model.

### NumPy / cv_bridge problems

Use pinned versions:

```bash
python3 -m pip install --user "numpy==1.26.4" "opencv-python==4.10.0.84"
```

---

## Team workflow

Use this repository as the main project:

```text
https://github.com/majidsamadi/ros1-child-safety-monitoring
```

The old ROS 2 repository is only a prototype/reference.

Recommended workflow:

```bash
git pull
# work on one small change
git status
git add .
git commit -m "Clear commit message"
git push
```

Before merging or presenting:

```bash
catkin_make
roslaunch child_safety_monitoring scenario_demo.launch
```

For live testing:

```bash
rostopic hz /poses/raw
rostopic hz /poses/tracked
rostopic hz /interaction/features
```

---

## Safety and ethics

This project involves child-safety monitoring, so the demo must be handled carefully.

Rules for demos:

- Do not use real dangerous situations.
- Do not perform forceful acting.
- Do not lift anyone in an unsafe way.
- Use the simulator for high-alert behavior.
- Use normal standing/approaching for live camera tests.
- Do not record or store videos unless everyone agrees.
- Do not claim the system proves kidnapping.

Correct wording:

```text
This is a suspicious movement-pattern detection prototype.
It provides a warning signal for human review.
```

Incorrect wording:

```text
This system proves kidnapping.
This system knows intent.
This system identifies a child by age.
```

---

## Current limitations

- Performance depends on camera angle and lighting.
- YOLO must see enough of both people.
- The system needs two clearly visible people.
- The smaller/larger role is based on relative size, not true age.
- Feet-off-ground detection is only a 2D proxy.
- Real deployment would require privacy approval, better testing, and human review.
- The high-alert behavior is safest to demonstrate with simulator mode.

---

## Final stakeholder demo suggestion

Use two parts:

### Part 1: real robot live vision demo

Show:

```text
robot camera feed
YOLO pose overlay
tracked people
normal standing gives no false alert
```

### Part 2: safe alert logic demo

Run simulator:

```bash
roslaunch child_safety_monitoring scenario_demo.launch
```

Show:

```text
NORMAL → WARNING → HIGH ALERT
```

This demonstrates the full concept without unsafe acting.

---

## Final summary

This repository contains the ROS 1 Noetic version of the project. It supports both laptop development and Jupiter robot demonstration.

The system is designed around this idea:

```text
camera image
→ pose estimation
→ tracking
→ interaction features
→ decision logic
→ alert/alarm output
```

During the week, teammates can develop on their own laptops using Docker. On Saturdays, the same project can run directly on the Jupiter robot using its ROS camera topic.
