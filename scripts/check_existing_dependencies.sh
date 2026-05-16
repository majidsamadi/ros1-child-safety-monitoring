#!/usr/bin/env bash
# Read-only dependency checker. Safe for university robot.
# It does not run apt update and does not install anything.

set -eo pipefail

printf '\n=== OS / ROS ===\n'
lsb_release -a || true
echo "ROS_DISTRO=${ROS_DISTRO:-not_set}"
python3 --version

printf '\n=== ROS commands ===\n'
for cmd in roscore roslaunch rostopic rospack catkin_make; do
  printf '%-15s' "$cmd"
  which "$cmd" || true
done

printf '\n=== ROS packages ===\n'
for pkg in cv_bridge image_transport web_video_server sensor_msgs std_msgs geometry_msgs; do
  printf '%-20s' "$pkg"
  rospack find "$pkg" || true
done

printf '\n=== Python packages ===\n'
python3 - <<'PY'
packages = [
    'rospy', 'cv2', 'numpy', 'cv_bridge', 'sensor_msgs', 'std_msgs',
    'ultralytics', 'torch', 'torchvision', 'sklearn', 'joblib'
]
for pkg in packages:
    try:
        mod = __import__(pkg)
        version = getattr(mod, '__version__', 'OK')
        print(f'{pkg}: {version}')
    except Exception as exc:
        print(f'{pkg}: MISSING or ERROR -> {exc}')
PY

printf '\n=== Camera devices ===\n'
ls -l /dev/video* 2>/dev/null || true
