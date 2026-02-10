@echo off
setlocal enabledelayedexpansion
echo.
echo ============================================================
echo    VECTOR Biographer - One-Click Installer
echo ============================================================
echo.
echo This will set up everything you need to run VECTOR Biographer.
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed.
    echo.
    echo Please install Python 3.10 or later from:
    echo https://www.python.org/downloads/
    echo.
    echo IMPORTANT: During installation, check "Add Python to PATH"
    echo.
    echo After installing Python, run this installer again.
    echo.
    pause
    exit /b 1
)

echo Python found! Continuing with installation...
echo.

REM Check if .env already exists
if exist ".env" (
    echo Found existing .env file - keeping your current API key.
    echo.
    goto :install
)

REM Prompt for API key
echo ============================================================
echo    STEP 1: Enter Your API Key
echo ============================================================
echo.
echo You need an Anthropic API key to use VECTOR Biographer.
echo.
echo If you don't have one yet:
echo   1. Go to https://console.anthropic.com/
echo   2. Create a free account
echo   3. Click "API Keys" and create a new key
echo   4. Copy the key (it starts with sk-ant-...)
echo.
echo ============================================================
echo.
set /p APIKEY="Paste your API key here and press Enter: "

if "!APIKEY!"=="" (
    echo.
    echo No API key entered. You can add it later by editing the .env file.
    echo.
    echo # VECTOR Biographer Configuration> .env
    echo ANTHROPIC_API_KEY=your_api_key_here>> .env
) else (
    echo.
    echo # VECTOR Biographer Configuration> .env
    echo ANTHROPIC_API_KEY=!APIKEY!>> .env
    echo API key saved!
)
echo.

:install
echo ============================================================
echo    STEP 2: Installing (this takes 5-10 minutes)
echo ============================================================
echo.
echo Please wait while we download and install everything...
echo.

echo [1/5] Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo ERROR: Could not create virtual environment.
    pause
    exit /b 1
)

echo [2/5] Activating virtual environment...
call venv\Scripts\activate.bat

echo [3/5] Installing Python packages...
echo       (Downloading AI models - this is the slow part)
pip install --upgrade pip >nul 2>&1
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
    echo You can run START_BIOGRAPHER.bat manually instead.
)

echo.
echo ============================================================
echo    INSTALLATION COMPLETE!
echo ============================================================
echo.
echo Look for "VECTOR Biographer" on your desktop.
echo.
echo If you don't see the shortcut, you can double-click
echo START_BIOGRAPHER.bat in this folder instead.
echo.
echo ============================================================
echo.
pause
