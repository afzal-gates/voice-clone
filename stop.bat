@echo off
REM VoiceClone AI - Stop Server Script
REM ===================================

echo.
echo =============================================
echo   VoiceClone AI - Stopping Server
echo =============================================
echo.

REM Find and kill Python processes running on port 8000
echo [INFO] Searching for processes using port 8000...

for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    set PID=%%a
    goto :found
)

:found
if defined PID (
    echo [INFO] Found process PID: %PID%
    echo [INFO] Terminating process...
    taskkill //F //PID %PID%
    if errorlevel 1 (
        echo [ERROR] Failed to terminate process
    ) else (
        echo [SUCCESS] Server stopped successfully
    )
) else (
    echo [INFO] No server process found on port 8000
)

echo.
pause
