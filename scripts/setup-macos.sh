#!/usr/bin/env bash
# ============================================================
# VoiceClone AI - macOS Setup
# ============================================================
# Installs system dependencies via Homebrew, creates a Python
# virtual environment, and installs the correct PyTorch variant
# (MPS for Apple Silicon, CPU for Intel).
#
# Usage:  bash scripts/setup-macos.sh
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"

echo "========================================"
echo " VoiceClone AI - macOS Setup"
echo "========================================"

# ----------------------------------------------------------
# 1. Check Homebrew
# ----------------------------------------------------------
if ! command -v brew &>/dev/null; then
    echo "[!] Homebrew not found."
    echo "    Install it from https://brew.sh then re-run this script."
    exit 1
fi
echo "[OK] Homebrew found"

# ----------------------------------------------------------
# 2. Install FFmpeg
# ----------------------------------------------------------
if command -v ffmpeg &>/dev/null; then
    echo "[OK] FFmpeg already installed: $(ffmpeg -version 2>&1 | head -1)"
else
    echo "[*] Installing FFmpeg via Homebrew..."
    brew install ffmpeg
fi

# ----------------------------------------------------------
# 3. Check Python version
# ----------------------------------------------------------
PYTHON=""
for cmd in python3.11 python3.10 python3.12 python3.13 python3; do
    if command -v "$cmd" &>/dev/null; then
        PYTHON="$cmd"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "[*] Installing Python via Homebrew..."
    brew install python@3.11
    PYTHON="python3.11"
fi

PY_VERSION=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "[OK] Using $PYTHON ($PY_VERSION)"

# ----------------------------------------------------------
# 4. Create virtual environment
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
# 5. Detect architecture and install PyTorch
# ----------------------------------------------------------
ARCH="$(uname -m)"
if [ "$ARCH" = "arm64" ]; then
    echo "[OK] Apple Silicon ($ARCH) detected — installing PyTorch with MPS support..."
    pip install torch torchaudio
else
    echo "[*] Intel Mac ($ARCH) — installing CPU-only PyTorch..."
    pip install -r "$PROJECT_DIR/requirements-cpu.txt"
fi

# ----------------------------------------------------------
# 6. Install remaining dependencies
# ----------------------------------------------------------
echo "[*] Installing project dependencies..."
pip install -r "$PROJECT_DIR/requirements.txt"

# ----------------------------------------------------------
# 7. Done
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
