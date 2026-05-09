cmake_minimum_required(VERSION 3.0.2)
project(child_safety_monitoring)

find_package(catkin REQUIRED COMPONENTS
  rospy
  std_msgs
  sensor_msgs
  geometry_msgs
  cv_bridge
  child_safety_msgs
)

catkin_python_setup()

catkin_package(
  CATKIN_DEPENDS rospy std_msgs sensor_msgs geometry_msgs cv_bridge child_safety_msgs
)

catkin_install_python(PROGRAMS
  scripts/cctv_stream_node.py
  scripts/pose_estimator_node.py
  scripts/tracker_node.py
  scripts/interaction_analyzer_node.py
  scripts/decision_node.py
  scripts/alert_console_node.py
  scripts/alarm_node.py
  scripts/scenario_simulator_node.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(DIRECTORY launch config
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)
