@echo off
REM Create a Python 3.10 virtual environment for the host webcam streamer on Windows.
REM Run from Command Prompt inside the repo folder.

py -3.10 --version || exit /b 1
py -3.10 -m venv .venv310 || exit /b 1
.venv310\Scripts\python.exe -m pip install --upgrade pip setuptools wheel || exit /b 1
.venv310\Scripts\python.exe -m pip install -r requirements_host.txt || exit /b 1

echo.
echo Host webcam venv is ready.
echo Run the webcam streamer with:
echo   .venv310\Scripts\python.exe scripts\host_webcam_streamer.py --camera 0 --port 8090
