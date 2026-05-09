# ROS 1 Child Safety Monitoring Prototype

This is the **ROS 1 Noetic** version of the child-safety monitoring prototype.
It is intended for the Jupiter robot, which is running:

```text
Ubuntu 20.04
ROS 1 Noetic
catkin
rospy
```

The project detects suspicious child-lifting patterns from a camera stream by using pose estimation, tracking, interaction-feature extraction, and a rule-based alert pipeline.

This is a **prototype**. It does not prove kidnapping or intent. It only detects suspicious movement patterns and should always be used with human review.

---

## Pipeline

```text
Robot camera topic
        ↓
pose_estimator_node
        ↓
/poses/raw
        ↓
tracker_node
        ↓
/poses/tracked
        ↓
interaction_analyzer_node
        ↓
/interaction/features
        ↓
decision_node
        ↓
/suspicion_event
        ↓
alert_console_node + alarm_node
```

---

## Packages

```text
src/child_safety_msgs
src/child_safety_monitoring
```

`child_safety_msgs` contains custom ROS 1 messages.

`child_safety_monitoring` contains the Python nodes.

---

## Install dependencies on Jupiter robot

Run on the Jupiter robot:

```bash
sudo apt update
sudo apt install -y \
  python3-pip \
  python3-opencv \
  ros-noetic-cv-bridge \
  ros-noetic-image-transport \
  ros-noetic-web-video-server
```

Then install Python dependencies:

```bash
cd ~/ros1-child-safety-monitoring
python3 -m pip install --user -r src/child_safety_monitoring/requirements_ros1.txt
```

If PyTorch installation is slow or fails, install it manually for the robot hardware and then rerun the command.

---

## Build

```bash
cd ~/ros1-child-safety-monitoring
source /opt/ros/noetic/setup.bash
catkin_make
source devel/setup.bash
```

---

## Find the robot camera topic

Make sure `roscore` and the robot camera are running.

```bash
rostopic list | grep -i image
rostopic list | grep -i camera
```

Common examples:

```text
/usb_cam/image_raw
/camera/rgb/image_raw
/jupiter/camera/image_raw
```

Use the real topic in the launch command below.

---

## Run live Jupiter camera demo

Replace `/YOUR/CAMERA/TOPIC` with the real camera topic:

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

---

## View YOLO pose overlay in browser

Open a second terminal on the robot:

```bash
cd ~/ros1-child-safety-monitoring
source /opt/ros/noetic/setup.bash
source devel/setup.bash
roslaunch child_safety_monitoring view_overlay.launch
```

Then open in a browser:

```text
http://ROBOT_IP:8080/stream?topic=/camera/pose_overlay
```

If you are using the robot itself with a browser, use:

```text
http://localhost:8080/stream?topic=/camera/pose_overlay
```

---

## Check live pipeline

In another terminal:

```bash
cd ~/ros1-child-safety-monitoring
source /opt/ros/noetic/setup.bash
source devel/setup.bash
./check_ros1_pipeline.sh
```

Useful manual checks:

```bash
rostopic hz /poses/raw
rostopic hz /poses/tracked
rostopic hz /interaction/features
rostopic echo /interaction/features -n 1
rostopic echo /suspicion_event
```

For normal standing, expected behavior is:

```text
suspicion_score: 0.0
state: observing
no /suspicion_event output
```

---

## Simulator backup demo

This does not require a camera. It is useful for presentations because it shows:

```text
NORMAL → WARNING → HIGH ALERT
```

Run:

```bash
cd ~/ros1-child-safety-monitoring
source /opt/ros/noetic/setup.bash
source devel/setup.bash
roslaunch child_safety_monitoring scenario_demo.launch
```

---

## Optional: use a laptop/web stream

The ROS 1 port also includes a stream input node. If you have an HTTP/MJPEG stream or RTSP stream:

```bash
roslaunch child_safety_monitoring stream_demo.launch stream_url:=http://HOST:8090/video
```

or:

```bash
roslaunch child_safety_monitoring stream_demo.launch stream_url:=rtsp://CAMERA_STREAM
```

Do not commit real usernames/passwords to GitHub.

---

## Current limitations

- The prototype depends heavily on camera angle and keypoint visibility.
- It needs two clearly visible people for interaction features.
- It does not identify people or infer intent.
- It is not a real safety product without proper testing, privacy approval, and human verification.
- The high-alert behavior should be demonstrated with the simulator or safe staged movement only.

---

## Safety note

Do not perform risky lifting or forceful acting for demos. Use safe staged movement, a mannequin, or the simulator demo for high-alert behavior.
