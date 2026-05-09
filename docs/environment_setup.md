# Environment Setup Notes

## Python versions

Use these versions:

- Host laptop webcam streamer: Python 3.10.x
- Jupiter robot / ROS Noetic: system Python 3.8 from Ubuntu 20.04

Do not use Python 3.14 for this project. PyTorch, OpenCV, Ultralytics, and ROS Noetic Python bindings are not reliable on Python 3.14 for our setup.

## Host laptop venv

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

## ROS 1 dependencies

On Jupiter robot or inside ROS Noetic Docker:

```bash
./scripts/setup_ros1_python_deps.sh
./scripts/build_ros1_workspace.sh
```

## Laptop Docker mode

```bash
./scripts/run_ros1_docker_dev.sh
```

Inside Docker:

```bash
bash scripts/docker_setup_ros1_workspace.sh
bash scripts/run_laptop_stream_demo.sh
```

## Robot mode

On Jupiter robot:

```bash
./scripts/setup_ros1_python_deps.sh
./scripts/build_ros1_workspace.sh
source devel/setup.bash
rostopic list | grep -i image
./scripts/run_robot_demo.sh /YOUR/CAMERA/TOPIC
```
