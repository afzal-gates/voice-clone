@echo off
REM VoiceClone AI - Start with Browser
REM ====================================

echo.
echo =============================================
echo   VoiceClone AI - Starting with Browser
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
    pause
    exit /b 1
)

echo [INFO] Starting server in background...
echo [INFO] Server will be available at: http://localhost:8000
echo.

REM Start server in background using START command
start /B python run.py

REM Wait for server to start (5 seconds)
echo [INFO] Waiting for server to start...
timeout /t 5 /nobreak >nul

REM Check if server is running
netstat -ano | findstr :8000 | findstr LISTENING >nul
if errorlevel 1 (
    echo [WARNING] Server may not have started properly
    echo [INFO] Check the server window for errors
) else (
    echo [SUCCESS] Server started successfully
    echo [INFO] Opening browser...
    start http://localhost:8000
)

echo.
echo =============================================
echo   VoiceClone AI is running
echo =============================================
echo.
echo Press any key to stop the server and exit...
pause >nul

REM Stop the server when user presses a key
echo.
echo [INFO] Stopping server...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill //F //PID %%a >nul 2>&1
)

echo [SUCCESS] Server stopped
timeout /t 2 /nobreak >nul
