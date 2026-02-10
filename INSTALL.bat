@echo off
echo ============================================================
echo    VECTOR Biographer - One-Click Installer
echo ============================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo.
    echo Please install Python 3.10 or later from:
    echo https://www.python.org/downloads/
    echo.
    echo IMPORTANT: During installation, check "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

echo [1/5] Python found. Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo ERROR: Could not create virtual environment.
    pause
    exit /b 1
)

echo [2/5] Activating virtual environment...
call venv\Scripts\activate.bat

echo [3/5] Installing dependencies (this may take 5-10 minutes)...
echo       Downloading AI models and libraries...
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Could not install dependencies.
    echo Try running: pip install -r requirements.txt
    pause
    exit /b 1
)

echo [4/5] Creating database...
python biographer\setup_database.py
if errorlevel 1 (
    echo WARNING: Database setup had issues, but may still work.
)

echo [5/5] Creating desktop shortcut...
python create_shortcut.py
if errorlevel 1 (
    echo NOTE: Could not create desktop shortcut automatically.
    echo You can run START_BIOGRAPHER.bat manually.
)

echo.
echo ============================================================
echo    INSTALLATION COMPLETE!
echo ============================================================
echo.
echo NEXT STEPS:
echo.
echo 1. Copy .env.template to .env
echo 2. Edit .env and add your Anthropic API key
echo    (Get one at: https://console.anthropic.com/)
echo 3. Double-click "VECTOR Biographer" on your desktop
echo    (or run START_BIOGRAPHER.bat)
echo.
echo ============================================================
pause
