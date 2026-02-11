#!/usr/bin/env bash
# ============================================================
# VoiceClone AI - Linux Setup
# ============================================================
# Installs system dependencies, creates a Python virtual environment,
# and installs the correct PyTorch variant (CUDA or CPU).
#
# Usage:  bash scripts/setup-linux.sh
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"

echo "========================================"
echo " VoiceClone AI - Linux Setup"
echo "========================================"

# ----------------------------------------------------------
# 1. Install FFmpeg via system package manager
# ----------------------------------------------------------
install_ffmpeg() {
    if command -v ffmpeg &>/dev/null; then
        echo "[OK] FFmpeg already installed: $(ffmpeg -version 2>&1 | head -1)"
        return
    fi

    echo "[*] Installing FFmpeg..."
    if command -v apt-get &>/dev/null; then
        sudo apt-get update -qq
        sudo apt-get install -y -qq ffmpeg
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y ffmpeg
    elif command -v yum &>/dev/null; then
        sudo yum install -y ffmpeg
    elif command -v pacman &>/dev/null; then
        sudo pacman -S --noconfirm ffmpeg
    else
        echo "[!] Could not detect package manager. Please install FFmpeg manually."
        echo "    The app will fall back to the imageio-ffmpeg Python package."
    fi
}

install_ffmpeg

# ----------------------------------------------------------
# 2. Check Python version
# ----------------------------------------------------------
PYTHON=""
for cmd in python3.11 python3.10 python3.12 python3.13 python3; do
    if command -v "$cmd" &>/dev/null; then
        PYTHON="$cmd"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "[!] Python 3.10+ not found. Please install Python first."
    exit 1
fi

PY_VERSION=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "[OK] Using $PYTHON ($PY_VERSION)"

# ----------------------------------------------------------
# 3. Create virtual environment
# ----------------------------------------------------------
if [ -d "$VENV_DIR" ]; then
    echo "[OK] Virtual environment already exists at $VENV_DIR"
else
    echo "[*] Creating virtual environment..."
    "$PYTHON" -m venv "$VENV_DIR"
    echo "[OK] Virtual environment created"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
pip install --upgrade pip --quiet

# ----------------------------------------------------------
# 4. Detect GPU and install PyTorch
# ----------------------------------------------------------
TORCH_REQ=""
if command -v nvidia-smi &>/dev/null; then
    echo "[OK] NVIDIA GPU detected"
    nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null || true
    TORCH_REQ="$PROJECT_DIR/requirements-cuda.txt"
    echo "[*] Installing PyTorch with CUDA support..."
else
    echo "[*] No NVIDIA GPU detected — installing CPU-only PyTorch..."
    TORCH_REQ="$PROJECT_DIR/requirements-cpu.txt"
fi

pip install -r "$TORCH_REQ"

# ----------------------------------------------------------
# 5. Install remaining dependencies
# ----------------------------------------------------------
echo "[*] Installing project dependencies..."
pip install -r "$PROJECT_DIR/requirements.txt"

# ----------------------------------------------------------
# 6. Done
# ----------------------------------------------------------
echo ""
echo "========================================"
echo " Setup complete!"
echo "========================================"
echo ""
echo " To start the server:"
echo "   bash scripts/run.sh"
echo ""
echo " Or manually:"
echo "   source .venv/bin/activate"
echo "   python run.py"
echo ""
