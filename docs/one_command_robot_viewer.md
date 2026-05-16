# One-command robot camera viewer

This update adds `browser_stream_viewer_node.py`, a ROS 1 node that subscribes to the robot image topic and serves it as MJPEG video in a browser.

It avoids the old workflow where one terminal ran a pasted Python HTTP server and another terminal was only used to find the robot IP.

## Run normal stream pipeline with viewer

```bash
source /opt/ros/noetic/setup.bash
source devel/setup.bash
./scripts/run_robot_stream_with_viewer.sh /dev/video2
```

## Run AI stream pipeline with viewer

```bash
source /opt/ros/noetic/setup.bash
source devel/setup.bash
./scripts/run_ai_robot_stream_with_viewer.sh /dev/video2
```

The node prints browser links such as:

```text
Open browser: http://ROBOT_IP:8080/video
```

Open that URL from a laptop connected to the same network.

If `/dev/video2` is wrong, try:

```bash
./scripts/run_ai_robot_stream_with_viewer.sh /dev/video0
```
