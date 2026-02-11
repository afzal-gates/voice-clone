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

echo Starting VoiceClone AI server...
python run.py
