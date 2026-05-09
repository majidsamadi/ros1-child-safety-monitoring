# ROS 1 Port Notes

This repository is a ROS 1 Noetic port of the original ROS 2 child safety monitoring prototype.

Main differences:

```text
ROS 2 rclpy       → ROS 1 rospy
colcon/ament      → catkin_make/catkin
ros2 launch       → roslaunch
ros2 topic        → rostopic
```

The logic is intentionally kept simple and explainable for a robotics class demo.
