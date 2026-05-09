# Create a Python 3.10 virtual environment for the host webcam streamer on Windows.
# Run from PowerShell inside the repo folder.

$ErrorActionPreference = "Stop"

Write-Host "Checking Python 3.10..."
py -3.10 --version

py -3.10 -m venv .venv310
.\.venv310\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv310\Scripts\python.exe -m pip install -r requirements_host.txt

Write-Host ""
Write-Host "Host webcam venv is ready."
Write-Host "Run the webcam streamer with:"
Write-Host "  .\.venv310\Scripts\python.exe scripts\host_webcam_streamer.py --camera 0 --port 8090"
