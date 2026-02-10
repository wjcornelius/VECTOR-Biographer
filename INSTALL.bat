@echo off
setlocal enabledelayedexpansion
echo.
echo ============================================================
echo    VECTOR Biographer - Installer
echo ============================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed on this computer.
    echo.
    echo I'll open the download page for you.
    echo.
    echo When installing Python:
    echo   - Click the big yellow Download button
    echo   - Run the installer
    echo   - CHECK THE BOX that says "Add Python to PATH"
    echo   - Click Install
    echo.
    echo After Python is installed, run this installer again.
    echo.
    start https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2" %%I in ('python --version 2^>^&1') do set PYVER=%%I
echo Found Python %PYVER% - good!
echo.

REM Check if .env already exists
if exist ".env" (
    echo Found your existing settings - keeping them.
    echo.
    goto :install
)

REM Prompt for API key
echo ============================================================
echo    Your API Key
echo ============================================================
echo.
echo To use this, you need an Anthropic API key.
echo.
echo If you don't have one yet:
echo   1. Go to console.anthropic.com
echo   2. Create an account
echo   3. Add a payment method (Settings then Billing)
echo   4. Click "API Keys" and create a new key
echo   5. Copy the key (starts with sk-ant-)
echo.
echo Want me to open that page for you? (Y/N)
set /p OPENPAGE="Type Y or N and press Enter: "
if /i "!OPENPAGE!"=="Y" (
    start https://console.anthropic.com/
    echo.
    echo I opened the page. Get your API key and come back here.
    echo.
)

echo.
set /p APIKEY="Paste your API key here and press Enter: "

if "!APIKEY!"=="" (
    echo.
    echo No key entered - you can add it later.
    echo Just edit the .env file in Notepad.
    echo.
    echo ANTHROPIC_API_KEY=your_api_key_here> .env
) else (
    echo ANTHROPIC_API_KEY=!APIKEY!> .env
    echo.
    echo Saved!
)
echo.

:install
echo ============================================================
echo    Installing - This Takes About 10 Minutes
echo ============================================================
echo.
echo Go grab a coffee. I'm downloading about 2GB of AI stuff.
echo.

echo [1/5] Setting up Python environment...
python -m venv venv
if errorlevel 1 (
    echo.
    echo Something went wrong creating the Python environment.
    echo Try restarting your computer and running this again.
    pause
    exit /b 1
)

echo [2/5] Activating environment...
call venv\Scripts\activate.bat

echo [3/5] Downloading packages (this is the slow part)...
pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo Something went wrong installing packages.
    echo Try running this installer again.
    echo If it keeps failing, you might need to restart your computer.
    pause
    exit /b 1
)

echo [4/5] Creating database...
python biographer\setup_database.py 2>nul
if errorlevel 1 (
    echo      (Database will be created on first run)
)

echo [5/5] Creating desktop shortcut...
python create_shortcut.py 2>nul
if errorlevel 1 (
    echo      (Shortcut creation skipped - use START_BIOGRAPHER.bat instead)
)

echo.
echo ============================================================
echo    DONE!
echo ============================================================
echo.
echo Look for "VECTOR Biographer" on your desktop.
echo.
echo If you don't see it, just double-click START_BIOGRAPHER.bat
echo in this folder.
echo.
echo ============================================================
echo.
pause
