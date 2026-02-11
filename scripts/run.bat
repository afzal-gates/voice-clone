@echo off
REM ============================================================
REM VoiceClone AI - Start Server (Windows)
REM ============================================================

cd /d "%~dp0\.."

REM Activate virtual environment if present
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

REM Required for IndicF5 Unicode text logging on Windows console
set PYTHONIOENCODING=utf-8

REM Use local models if models/ directory exists
if exist "models\huggingface" (
    if not defined MODELS_DIR set MODELS_DIR=models
)

echo Starting VoiceClone AI server...
python run.py
