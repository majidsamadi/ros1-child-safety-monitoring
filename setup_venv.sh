#!/usr/bin/env bash
# setup_venv.sh
# Creates a Python 3.10 virtual environment for host-side tools (webcam streamer).
# Run this ONCE from the repo root:
#
#   cd path/to/ros1-child-safety-monitoring
#   bash setup_venv.sh
#
# After setup, activate with:
#   source .venv310/bin/activate

set -euo pipefail

VENV_DIR=".venv310"
REQUIRED="3.10"

print_color() { printf "\033[%sm%s\033[0m\n" "$1" "$2"; }
info()    { print_color "36" "[INFO] $*"; }
success() { print_color "32" "[OK]   $*"; }
warn()    { print_color "33" "[WARN] $*"; }
error()   { print_color "31" "[ERR]  $*"; }

echo ""
echo "============================================"
info "  Child Safety Monitoring - Host Venv Setup"
echo "============================================"
echo ""

# ── 1. Find Python 3.10 ──────────────────────────────────────────────────────
info "[1/4] Looking for Python $REQUIRED ..."

PYTHON_EXE=""
for candidate in python3.10 python3 python; do
    if command -v "$candidate" &>/dev/null; then
        ver=$("$candidate" --version 2>&1 || true)
        if echo "$ver" | grep -q "Python 3\.10"; then
            PYTHON_EXE="$candidate"
            success "Found: $ver  ($candidate)"
            break
        fi
    fi
done

if [ -z "$PYTHON_EXE" ]; then
    error "Python 3.10 not found."
    echo ""
    echo "Install it:"
    echo "  macOS:  brew install python@3.10"
    echo "  Ubuntu: sudo apt install python3.10 python3.10-venv"
    echo "  Or download: https://www.python.org/downloads/release/python-31011/"
    echo ""
    exit 1
fi

# ── 2. Create virtual environment ────────────────────────────────────────────
info "[2/4] Creating virtual environment in '$VENV_DIR' ..."

if [ -d "$VENV_DIR" ]; then
    warn "'$VENV_DIR' already exists, skipping creation."
else
    "$PYTHON_EXE" -m venv "$VENV_DIR"
    success "Created."
fi

PIP="$VENV_DIR/bin/pip"
PYTHON_VENV="$VENV_DIR/bin/python"

# ── 3. Upgrade pip ───────────────────────────────────────────────────────────
info "[3/4] Upgrading pip ..."
"$PYTHON_VENV" -m pip install --upgrade pip --quiet
success "Done."

# ── 4. Install host requirements ─────────────────────────────────────────────
info "[4/4] Installing host requirements from requirements_host.txt ..."

if [ ! -f "requirements_host.txt" ]; then
    error "requirements_host.txt not found."
    echo "      Make sure you are running this from the repo root."
    exit 1
fi

"$PIP" install -r requirements_host.txt

echo ""
echo "============================================"
success "Setup complete!"
echo "============================================"
echo ""
echo "Activate the environment:"
echo "  source .venv310/bin/activate"
echo ""
echo "Then run the webcam streamer:"
echo "  python src/child_safety_monitoring/scripts/host_webcam_streamer.py --camera 0 --port 8090"
echo ""

# Quick sanity check
info "Verifying installation ..."
"$PYTHON_VENV" -c "
import cv2, numpy
print('  numpy :', numpy.__version__)
print('  cv2   :', cv2.__version__)
print('  All OK')
"
echo ""
