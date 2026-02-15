@echo off
REM VoiceClone AI - Windows Startup Script
REM ========================================

echo.
echo =============================================
echo   VoiceClone AI - Starting Application
echo =============================================
echo.

REM Change to script directory
cd /d "%~dp0"

REM Check if virtual environment exists
if exist ".venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo [WARNING] Virtual environment not found at .venv
    echo [INFO] Using system Python...
)

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo [ERROR] Please install Python 3.9+ and try again
    pause
    exit /b 1
)

REM Display Python version
echo [INFO] Python version:
python --version

REM Check if required packages are installed
python -c "import uvicorn" >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] Required packages not installed
    echo [INFO] Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
)

echo.
echo [INFO] Starting VoiceClone AI server...
echo [INFO] Server will be available at: http://localhost:8000
echo [INFO] Press Ctrl+C to stop the server
echo.
echo =============================================
echo.

REM Start the application
python run.py

REM If the server exits, show the error level
if errorlevel 1 (
    echo.
    echo [ERROR] Server exited with error code %errorlevel%
    echo.
)

pause
