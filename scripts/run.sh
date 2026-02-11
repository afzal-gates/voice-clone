#!/usr/bin/env bash
# ============================================================
# VoiceClone AI - Start Server (macOS / Linux)
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."

# Activate virtual environment if present
if [ -f ".venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi

# Ensure UTF-8 output (required for IndicF5 Unicode text logging)
export PYTHONIOENCODING=utf-8

# Use local models if models/ directory exists
if [ -d "models/huggingface" ] && [ -z "$MODELS_DIR" ]; then
    export MODELS_DIR=models
fi

echo "Starting VoiceClone AI server..."
python run.py
