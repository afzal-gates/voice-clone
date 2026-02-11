@echo off
REM ============================================================
REM VoiceClone AI - Windows Setup
REM ============================================================
REM Creates a Python virtual environment and installs the
REM correct PyTorch variant (CUDA or CPU).
REM
REM Usage:  scripts\setup-windows.bat
REM ============================================================

echo ========================================
echo  VoiceClone AI - Windows Setup
echo ========================================

set "PROJECT_DIR=%~dp0.."
set "VENV_DIR=%PROJECT_DIR%\.venv"

REM ----------------------------------------------------------
REM 1. Check Python
REM ----------------------------------------------------------
where python >nul 2>&1
if errorlevel 1 (
    echo [!] Python not found on PATH. Please install Python 3.10+ first.
    exit /b 1
)
for /f "delims=" %%v in ('python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do set PY_VERSION=%%v
echo [OK] Python %PY_VERSION% found

REM ----------------------------------------------------------
REM 2. Create virtual environment
REM ----------------------------------------------------------
if exist "%VENV_DIR%\Scripts\activate.bat" (
    echo [OK] Virtual environment already exists
) else (
    echo [*] Creating virtual environment...
    python -m venv "%VENV_DIR%"
    echo [OK] Virtual environment created
)

call "%VENV_DIR%\Scripts\activate.bat"
pip install --upgrade pip --quiet

REM ----------------------------------------------------------
REM 3. Detect GPU and install PyTorch
REM ----------------------------------------------------------
where nvidia-smi >nul 2>&1
if errorlevel 1 (
    echo [*] No NVIDIA GPU detected - installing CPU-only PyTorch...
    pip install -r "%PROJECT_DIR%\requirements-cpu.txt"
) else (
    echo [OK] NVIDIA GPU detected
    echo [*] Installing PyTorch with CUDA support...
    pip install -r "%PROJECT_DIR%\requirements-cuda.txt"
)

REM ----------------------------------------------------------
REM 4. Install remaining dependencies
REM ----------------------------------------------------------
echo [*] Installing project dependencies...
pip install -r "%PROJECT_DIR%\requirements.txt"

REM ----------------------------------------------------------
REM 5. Done
REM ----------------------------------------------------------
echo.
echo ========================================
echo  Setup complete!
echo ========================================
echo.
echo  To start the server:
echo    scripts\run.bat
echo.
echo  Or manually:
echo    .venv\Scripts\activate.bat
echo    set PYTHONIOENCODING=utf-8
echo    python run.py
echo.
