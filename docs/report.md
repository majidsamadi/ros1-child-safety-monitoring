# WQF7010 / WID3005 — Robotics Project Report

**Project Title:** ROS 1 Child Safety Monitoring — Suspicious Lifting Pattern Detection  
**Repository:** https://github.com/majidsamadi/ros1-child-safety-monitoring  
**Branch:** `violence-detection`

---

## Question 1 — Application, Objectives, Scope and AI Techniques (10 marks)

### 1.1 Application Overview

This project implements a **child safety monitoring prototype** using ROS 1 Noetic that watches a camera feed and detects suspicious interaction patterns between two people — specifically a pattern consistent with a larger person forcibly lifting or carrying a smaller person.

The system is designed for deployment on the **Jupiter robot** in public or monitored spaces. It operates entirely on CPU, requires no cloud connectivity, and produces human-reviewable warning signals rather than automatic enforcement actions.

> **Important:** This prototype does not identify individuals, estimate real age, or make legal determinations. It is a movement-pattern detector that produces a warning signal for human review.

---

### 1.2 Objectives

| # | Objective |
|---|---|
| 1 | Detect two people simultaneously in a camera frame |
| 2 | Estimate and track 17-keypoint body pose for each person |
| 3 | Assign smaller/larger candidate roles based on relative bounding-box height |
| 4 | Compute interpretable interaction features (proximity, wrap, lift, feet-off-ground, limb speed) |
| 5 | Fuse rule-based features with a ViT deep-learning violence score |
| 6 | Issue console alerts and audio alarms when suspicion score exceeds a threshold for a sustained period |
| 7 | Visualise the pose overlay in real time via `rqt_image_view` |

---

### 1.3 Scope

**In scope:**
- Two-person interaction monitoring from a single RGB camera
- Rule-based and deep-learning hybrid suspicion scoring
- Three alert levels: NORMAL → WARNING → HIGH ALERT
- Support for live webcam, robot camera topic, and local video file input
- Audio alarm playback on detection events

**Out of scope:**
- Multi-camera setups
- Age estimation or identity recognition
- Depth sensing (depth field is reserved for future work)
- Automatic physical intervention or robot movement

---

### 1.4 AI Techniques and Models

#### A. Pose Estimation — YOLO11n-Pose (Ultralytics)

**Model:** `yolo11n-pose.pt`  
**Task:** Object detection + 17-keypoint skeleton estimation  
**Framework:** Ultralytics (PyTorch backend)

YOLO (You Only Look Once) is a single-stage convolutional neural network that simultaneously predicts bounding boxes and keypoint locations in one forward pass. The `n` (nano) variant is used for CPU-speed performance. It detects 17 COCO keypoints per person:

```
Nose, Left/Right Eye, Left/Right Ear,
Left/Right Shoulder, Left/Right Elbow, Left/Right Wrist,
Left/Right Hip, Left/Right Knee, Left/Right Ankle
```

Each keypoint is assigned a confidence score. Keypoints with confidence below 0.25 are marked as not visible.

#### B. Violence Detection — ViT (Vision Transformer) Classifier

**Model:** `jaranohaal/vit-base-violence-detection` (HuggingFace)  
**Task:** Binary image classification — violence / non-violence  
**Framework:** HuggingFace Transformers (PyTorch backend)

A Vision Transformer (ViT) divides an input image into fixed-size patches and applies multi-head self-attention across all patches. Unlike CNNs, ViT captures global context in a single pass. The model outputs a probability score (0.0–1.0) for the violence class, which is fused with the rule-based score in the decision node.

#### C. Rule-Based Feature Engineering

In parallel with the deep learning models, an explicit feature extractor computes six interpretable signals from the tracked poses:

| Feature | Description | Weight |
|---|---|---|
| Contact distance | Normalised torso-to-torso distance (lower = closer) | 0.20 |
| Wrap score | Adult wrists near child torso centre | 0.15 |
| Lift score | Upward displacement of smaller candidate across frames | 0.25 |
| Feet-off-ground | Smaller candidate ankles elevated above expected floor level | 0.15 |
| Limb speed | Rapid limb velocity (struggling signal) | 0.15 |
| Co-motion | Both people moving in same direction simultaneously | 0.10 |

The composite suspicion score is:

```
suspicion_score = 0.20 × contact + 0.15 × wrap + 0.25 × lift
                + 0.15 × feet + 0.15 × limb_speed + 0.10 × co_motion
```

#### D. Score Fusion and Decision Logic

The final blended score combines rule-based and ViT outputs:

```
final_score = (1 − vit_weight) × suspicion_score + vit_weight × vit_score
```

Default `vit_weight = 0.5`. Alerts fire when the score exceeds a threshold **for a sustained period**:

| Level | Threshold | Persistence |
|---|---|---|
| WARNING | ≥ 0.30 | 0.3 seconds |
| HIGH ALERT | ≥ 0.45 | 0.5 seconds |

#### E. Centroid Tracker

A lightweight centroid-based tracker assigns stable `track_N` IDs across frames using Euclidean distance matching. It maintains a motion history buffer (8 frames) per track, which is used to compute lift and limb-speed scores over time.

---

### 1.5 Experimental Setup

```
┌─────────────────────────────────────────────────────────────────┐
│                        INPUT SOURCES                            │
│  ┌─────────────┐  ┌─────────────────┐  ┌────────────────────┐  │
│  │ Laptop      │  │ Jupiter Robot   │  │ Video File         │  │
│  │ Webcam      │  │ /usb_cam/image  │  │ test_1.mp4         │  │
│  │ (HTTP MJPEG)│  │ _raw            │  │ (loop mode)        │  │
│  └──────┬──────┘  └────────┬────────┘  └─────────┬──────────┘  │
│         └─────────────────┬┘────────────────────┘             │
│                           ▼                                     │
│              /camera/image_raw  (sensor_msgs/Image)             │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
         ┌──────────────────────────────────┐
         │       pose_estimator_node        │
         │   YOLO11n-Pose (Ultralytics)     │
         │   17 keypoints per person        │
         └────────────┬─────────────────────┘
                      │ /poses/raw
                      ▼
         ┌──────────────────────────────────┐
         │          tracker_node            │
         │   Centroid Tracker               │
         │   Assigns track IDs + roles      │
         │   smaller_candidate / larger     │
         └────────────┬─────────────────────┘
                      │ /poses/tracked
          ┌───────────┴──────────┐
          ▼                      ▼
┌─────────────────────┐  ┌────────────────────────┐
│ interaction_        │  │ violence_detector_node  │
│ analyzer_node       │  │ ViT Image Classifier    │
│ Rule-based features │  │ HuggingFace             │
│ suspicion_score     │  │ /violence/vit_score     │
└────────────┬────────┘  └───────────┬─────────────┘
             │ /interaction/features  │ /violence/vit_score
             └──────────┬────────────┘
                        ▼
         ┌──────────────────────────────────┐
         │          decision_node           │
         │   Score fusion + persistence     │
         │   WARNING / HIGH ALERT           │
         └────────────┬─────────────────────┘
                      │ /suspicion_event
          ┌───────────┼───────────┐
          ▼           ▼           ▼
┌──────────────┐ ┌──────────┐ ┌──────────────┐
│alert_console │ │alarm_node│ │/alarm/state  │
│   node       │ │WAV audio │ │(String topic)│
│Console print │ │aplay     │ └──────────────┘
└──────────────┘ └──────────┘
```

---

### 1.6 Testing Scenarios

| # | Scenario | Expected Output |
|---|---|---|
| S1 | Single person walking normally | `state: observing`, `score ≈ 0.0`, no alert |
| S2 | Two people standing apart | `state: observing`, `score < 0.15`, no alert |
| S3 | Two people walking close together | `state: watch`, `score ≈ 0.15–0.29`, no alert |
| S4 | One person places hands on shoulders of shorter person | `wrap_score` increases, `state: watch`, possible WARNING |
| S5 | One person lifts smaller person (test video) | `lift_score → 1.0`, `limb_speed → 1.0`, WARNING or HIGH ALERT, audio alarm fires |
| S6 | Simulator scripted scenario (no camera) | Automated NORMAL → WARNING → HIGH ALERT sequence |

---

## Question 2 — ROS Workspace and APIs (20 marks)

### 2.1 Workspace Setup

The ROS workspace follows standard catkin conventions:

```
ros1/ws/                         ← catkin workspace root
├── src/
│   ├── child_safety_msgs/       ← custom message package
│   └── child_safety_monitoring/ ← main application package
├── build/                       ← generated by catkin_make
└── devel/                       ← generated by catkin_make
```

**Setup steps (inside Docker / Ubuntu 20.04 with ROS Noetic):**

```bash
# a) Boot into Ubuntu / enter Docker container
docker exec -it ros1_desktop bash

# b) The workspace folder already exists at /ros1_ws
cd /ros1_ws

# c) Build the catkin workspace
source /opt/ros/noetic/setup.bash
catkin_make

# d) Source the workspace in every new terminal
source /ros1_ws/devel/setup.bash

# (To make permanent on a native Ubuntu install, add to ~/.bashrc:)
# echo "source /ros1_ws/devel/setup.bash" >> ~/.bashrc
```

---

### 2.2 ROS Packages

#### Package 1: `child_safety_msgs`

Custom message definitions used across all nodes.

| Message | Fields | Purpose |
|---|---|---|
| `PersonPose2D` | `track_id`, `size_role`, `bbox_*`, `keypoints_xy[]`, `visible[]`, `keypoint_confidence[]` | One tracked person with pose |
| `PersonPose2DArray` | `header`, `poses[]` | Array of tracked people per frame |
| `InteractionFeatures` | `smaller_track_id`, `larger_track_id`, six score fields, `suspicion_score`, `state` | Output of interaction analyzer |
| `SuspicionEvent` | `level`, `suspicion_score`, `explanation`, ROI fields | Final alert event |

#### Package 2: `child_safety_monitoring`

Main application package containing all ROS nodes.

---

### 2.3 ROS APIs — Nodes, Topics, Publishers and Subscribers

#### Node 1: `cctv_stream_node`

**Purpose:** Reads a video source (webcam index, HTTP/RTSP stream, or local video file) and publishes raw frames as ROS Image messages.

**Parameters:**
- `~stream_url` — camera index (`0`), URL, or file path
- `~publish_rate_hz` — frame rate (default: 15.0)
- `~loop` — replay video file from start when it ends (default: `false`)

**Publisher:**

| Topic | Type | Example output |
|---|---|---|
| `/camera/image_raw` | `sensor_msgs/Image` | BGR8 encoded frame, 640×480, 15 fps |

```python
# Example: publishing one frame
msg = bridge.cv2_to_imgmsg(frame, encoding='bgr8')
msg.header.stamp = rospy.Time.now()
pub.publish(msg)
```

---

#### Node 2: `pose_estimator_node`

**Purpose:** Runs YOLO11n-Pose on each incoming frame to detect people and their 17 body keypoints.

**Subscriber:**

| Topic | Type | Description |
|---|---|---|
| `/camera/image_raw` | `sensor_msgs/Image` | Input camera frame |

**Publishers:**

| Topic | Type | Example output |
|---|---|---|
| `/poses/raw` | `PersonPose2DArray` | Array of detected persons with bounding boxes and keypoints |
| `/camera/pose_overlay` | `sensor_msgs/Image` | Frame with YOLO skeleton drawn over it |

```
# Example /poses/raw output for one person:
track_id: ''            # not yet assigned (tracker does this)
bbox_x: 320  bbox_y: 100  bbox_width: 120  bbox_height: 380
keypoints_xy: [(334, 115), (340, 110), ...]   # 17 points
keypoint_confidence: [0.91, 0.88, 0.05, ...]
visible: [True, True, False, ...]
```

---

#### Node 3: `tracker_node`

**Purpose:** Assigns stable track IDs across frames using centroid matching. Assigns `smaller_candidate` / `larger_candidate` roles by comparing bounding-box heights.

**Subscriber:**

| Topic | Type | Description |
|---|---|---|
| `/poses/raw` | `PersonPose2DArray` | Raw YOLO detections |

**Publisher:**

| Topic | Type | Example output |
|---|---|---|
| `/poses/tracked` | `PersonPose2DArray` | Same detections with `track_id` and `size_role` filled |

```
# Example /poses/tracked output:
poses[0].track_id: "track_3"
poses[0].size_role: "smaller_candidate"
poses[0].size_confidence: 0.8

poses[1].track_id: "track_1"
poses[1].size_role: "larger_candidate"
poses[1].size_confidence: 0.8
```

---

#### Node 4: `interaction_analyzer_node`

**Purpose:** Computes six interaction features from tracked poses and combines them into a weighted suspicion score. Maintains an 8-frame motion history per track pair for temporal signals (lift, limb speed).

**Subscriber:**

| Topic | Type | Description |
|---|---|---|
| `/poses/tracked` | `PersonPose2DArray` | Tracked poses with roles |

**Publisher:**

| Topic | Type | Example output |
|---|---|---|
| `/interaction/features` | `InteractionFeatures` | Six feature scores + composite suspicion score |

```
# Example /interaction/features output (suspicious scene):
smaller_track_id: "track_3"
larger_track_id: "track_1"
torso_distance_norm: 1.39      # close contact
wrap_score: 0.90               # adult wrists near child torso
lift_score: 1.00               # child moving upward
feet_off_ground_score: 0.14
limb_speed_score: 1.00         # rapid movement
co_motion_score: 0.00
suspicion_score: 0.617
state: "warning"
```

---

#### Node 5: `violence_detector_node`

**Purpose:** Runs a ViT image classifier on incoming frames (every N frames) to produce a deep-learning violence probability score.

**Subscriber:**

| Topic | Type | Description |
|---|---|---|
| `/camera/image_raw` | `sensor_msgs/Image` | Input frames (processed every `frame_skip+1` frames) |

**Publisher:**

| Topic | Type | Example output |
|---|---|---|
| `/violence/vit_score` | `std_msgs/Float32` | Violence probability 0.0–1.0 |

```
# Example: /violence/vit_score
data: 0.73    # high violence probability from ViT model
```

---

#### Node 6: `decision_node`

**Purpose:** Fuses the rule-based suspicion score with the ViT score. Fires a `SuspicionEvent` when the blended score exceeds a threshold for a sustained duration.

**Subscribers:**

| Topic | Type | Description |
|---|---|---|
| `/interaction/features` | `InteractionFeatures` | Rule-based score |
| `/violence/vit_score` | `std_msgs/Float32` | ViT score (optional) |

**Publisher:**

| Topic | Type | Example output |
|---|---|---|
| `/suspicion_event` | `SuspicionEvent` | Alert event with level, score, explanation |

```
# Example /suspicion_event output:
level: "high"
suspicion_score: 0.81
explanation: "HIGH score=0.81; contact_dist_norm=1.39; wrap=0.90; lift=1.00; ..."
```

---

#### Node 7: `alert_console_node`

**Purpose:** Subscribes to both `/interaction/features` and `/suspicion_event` and prints clean, colour-coded log messages to the terminal.

**Subscribers:** `/interaction/features`, `/suspicion_event`

```
[INFO]  [NORMAL]     score=0.05 | No suspicious interaction pattern detected
[WARN]  [WARNING]    score=0.34 | Suspicious interaction pattern detected
[ERROR] [HIGH ALERT] score=0.81 | Suspicious child-lifting pattern detected
```

---

#### Node 8: `alarm_node`

**Purpose:** Publishes the alarm state as a latched String topic. On WARNING or HIGH ALERT, generates and plays a sine-wave WAV alarm sound via `aplay` in a background thread.

**Subscribers:** `/interaction/features`, `/suspicion_event`

**Publisher:**

| Topic | Type | Values |
|---|---|---|
| `/alarm/state` | `std_msgs/String` (latched) | `ALARM_OFF`, `WARNING`, `HIGH_ALARM_ON` |

```
# Audio alarm specifications:
WARNING alarm:    660 Hz, 2 beeps, 0.6s each
HIGH ALERT alarm: 1100 Hz, 4 beeps, 0.8s each
```

---

#### Node 9: `scenario_simulator_node`

**Purpose:** Publishes scripted fake `InteractionFeatures` messages to demonstrate the NORMAL → WARNING → HIGH ALERT pipeline without a camera.

**Publisher:** `/interaction/features`

---

### 2.4 Unit Testing — Running Individual APIs

```bash
# Source workspace
source /opt/ros/noetic/setup.bash && source /ros1_ws/devel/setup.bash

# Test 1: verify frames are published
rostopic hz /camera/image_raw
# Expected: average rate: ~15.0

# Test 2: verify YOLO detection
rostopic echo /poses/raw -n 1
# Expected: PersonPose2DArray with at least one pose

# Test 3: verify tracker assigns IDs and roles
rostopic echo /poses/tracked --noarr | grep -E "track_id|size_role"
# Expected: track_id: "track_N", size_role: "smaller_candidate" / "larger_candidate"

# Test 4: verify interaction features
rostopic echo /interaction/features | grep -E "suspicion_score|state"
# Expected: numeric score, state in [observing, watch, warning, high_alert]

# Test 5: verify ViT score
rostopic echo /violence/vit_score
# Expected: Float32 between 0.0 and 1.0

# Test 6: verify alarm state
rostopic echo /alarm/state
# Expected: ALARM_OFF, WARNING, or HIGH_ALARM_ON

# Test 7: run simulator (no camera needed)
roslaunch child_safety_monitoring scenario_demo.launch
# Expected: NORMAL → WARNING → HIGH ALERT sequence in console
```

---

## Question 3 — ROS Graph Visualisation (5 marks)

### 3.1 Generating the rqt Graph

With the pipeline running, open a second terminal and run:

```bash
docker exec -it ros1_desktop bash
source /opt/ros/noetic/setup.bash && source /ros1_ws/devel/setup.bash
export DISPLAY=:0
rqt_graph
```

### 3.2 Node–Topic Relationships

The full ROS graph for the video file demo is as follows:

```
[cctv_stream_node] ──────────────────────────────────────────────────────┐
                                                                          │ /camera/image_raw
                                    ┌─────────────────────────────────────┤
                                    │                                      │
                                    ▼                                      ▼
                        [pose_estimator_node]              [violence_detector_node]
                                    │                                      │
                    ┌───────────────┤                                      │
                    │ /poses/raw    │ /camera/pose_overlay                 │ /violence/vit_score
                    ▼              (→ rqt_image_view)                      │
                [tracker_node]                                             │
                    │                                                      │
                    │ /poses/tracked                                       │
                    ▼                                                      │
        [interaction_analyzer_node]                                        │
                    │                                                      │
                    │ /interaction/features                                │
                    ├──────────────────────────────────────────────────────┤
                    │               [decision_node] ◄──────────────────────┘
                    │                    │
                    │                    │ /suspicion_event
                    │            ┌───────┴──────────┐
                    │            ▼                  ▼
                    │  [alert_console_node]    [alarm_node]
                    │                              │
                    ▼                              │ /alarm/state
              [alarm_node]                   (latched topic)
```

### 3.3 Relationship Summary

| Publisher | Topic | Subscriber(s) |
|---|---|---|
| `cctv_stream_node` | `/camera/image_raw` | `pose_estimator_node`, `violence_detector_node` |
| `pose_estimator_node` | `/poses/raw` | `tracker_node` |
| `pose_estimator_node` | `/camera/pose_overlay` | `web_video_server` / `rqt_image_view` |
| `tracker_node` | `/poses/tracked` | `interaction_analyzer_node` |
| `interaction_analyzer_node` | `/interaction/features` | `decision_node`, `alert_console_node`, `alarm_node` |
| `violence_detector_node` | `/violence/vit_score` | `decision_node` |
| `decision_node` | `/suspicion_event` | `alert_console_node`, `alarm_node` |
| `alarm_node` | `/alarm/state` | (latched — any subscriber) |

The graph shows a **linear pipeline** with one branch point at `/camera/image_raw` (serving both pose estimation and violence detection), converging at `decision_node` for final score fusion.

---

## Question 4 — Demo Video Plan (max 5 minutes)

### 4.1 Recommended Video Structure

| Time | Content | Text Label |
|---|---|---|
| 0:00–0:20 | Project title card, team members, brief objective | *"Child Safety Monitoring — ROS 1 Noetic"* |
| 0:20–0:40 | Show the rqt_graph with all nodes and topics highlighted | *"ROS Node Graph — 8 nodes connected via 7 topics"* |
| 0:40–1:10 | Show `rqt_image_view` with YOLO pose overlay — two people walking normally | *"NORMAL: score ≈ 0.05 — No suspicious pattern"* |
| 1:10–2:00 | Show test video with two people interacting — score climbing | *"WATCH: score = 0.34 — Persons in close proximity"* |
| 2:00–3:00 | Show suspicious lifting moment — WARNING fires, audio alarm plays | *"WARNING: score = 0.42 — Suspicious interaction detected"* |
| 3:00–3:40 | Show HIGH ALERT with all scores at maximum | *"HIGH ALERT: score = 0.81 — Suspicious lifting pattern"* |
| 3:40–4:10 | Show `rostopic echo /suspicion_event` output alongside video | *"ROS topic /suspicion_event — live event data"* |
| 4:10–4:40 | Show simulator demo (scripted NORMAL → HIGH ALERT) | *"Simulator mode — repeatable demo without camera"* |
| 4:40–5:00 | Summary of AI techniques used and conclusion | *"YOLO Pose + ViT Classifier + Rule-based Fusion"* |

### 4.2 Commands to Capture During Recording

```bash
# Terminal 1 — run pipeline
roslaunch child_safety_monitoring video_file_demo.launch \
  video_file:=/ros1_ws/src/ros1-child-safety-monitoring/data/videos/test_1.mp4 \
  loop:=true

# Terminal 2 — show live topic output
rostopic echo /interaction/features | grep -E "suspicion_score|state|smaller|larger"

# Terminal 3 — show events
rostopic echo /suspicion_event

# Terminal 4 — YOLO overlay
export DISPLAY=:0 && rqt_image_view /camera/pose_overlay

# Terminal 5 — rqt graph
export DISPLAY=:0 && rqt_graph
```

---

## Appendix — Launch Files

| Launch File | Purpose | Command |
|---|---|---|
| `video_file_demo.launch` | Full pipeline from video file | `roslaunch child_safety_monitoring video_file_demo.launch video_file:=<path> loop:=true` |
| `stream_demo.launch` | Full pipeline from webcam/HTTP stream | `roslaunch child_safety_monitoring stream_demo.launch stream_url:=0` |
| `jupiter_robot_camera_demo.launch` | Full pipeline from robot ROS camera topic | `roslaunch child_safety_monitoring jupiter_robot_camera_demo.launch camera_topic:=/usb_cam/image_raw` |
| `scenario_demo.launch` | Simulated NORMAL→HIGH ALERT, no camera | `roslaunch child_safety_monitoring scenario_demo.launch` |
| `view_overlay.launch` | Web video server for browser overlay | `roslaunch child_safety_monitoring view_overlay.launch` |

---

## Appendix — Configuration Parameters (`detection_params.yaml`)

```yaml
warning_threshold: 0.30          # suspicion score to trigger WARNING
high_threshold: 0.45             # suspicion score to trigger HIGH ALERT
warning_persistence_seconds: 0.3 # must hold above threshold for this long
high_persistence_seconds: 0.5
vit_weight: 0.5                  # blend weight for ViT score (0.0 = rule-based only)
vit_enabled: false               # set true to enable ViT score fusion
```
