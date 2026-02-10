@echo off
echo.
echo ============================================================
echo    VECTOR Biographer - Setup Checker
echo ============================================================
echo.
echo Checking if everything is set up correctly...
echo.

set ERRORS=0

REM Check Python
echo [1] Checking for Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo     X  Python is NOT installed.
    echo        Go to https://python.org and install it.
    echo        IMPORTANT: Check "Add to PATH" during install!
    echo.
    set ERRORS=1
) else (
    echo     OK Python is installed.
)

REM Check venv
echo [2] Checking for virtual environment...
if exist "venv\Scripts\python.exe" (
    echo     OK Virtual environment exists.
) else (
    echo     X  Virtual environment not found.
    echo        Run INSTALL.bat first.
    echo.
    set ERRORS=1
)

REM Check .env file
echo [3] Checking for API key...
if exist ".env" (
    findstr /C:"sk-ant-" .env >nul 2>&1
    if errorlevel 1 (
        echo     X  .env file exists but API key looks wrong.
        echo        Open .env in Notepad and check your key.
        echo        It should start with sk-ant-
        echo.
        set ERRORS=1
    ) else (
        echo     OK API key found.
    )
) else (
    echo     X  No .env file found.
    echo        Run INSTALL.bat and enter your API key when asked.
    echo.
    set ERRORS=1
)

REM Check database
echo [4] Checking for database...
if exist "data\biographer.db" (
    echo     OK Database exists.
) else (
    echo     ?  No database yet - one will be created on first run.
)

REM Check key packages
echo [5] Checking key packages...
call venv\Scripts\activate.bat 2>nul
python -c "import anthropic" 2>nul
if errorlevel 1 (
    echo     X  Anthropic package not installed.
    echo        Run INSTALL.bat again.
    echo.
    set ERRORS=1
) else (
    echo     OK Anthropic package installed.
)

python -c "import whisper" 2>nul
if errorlevel 1 (
    echo     X  Whisper package not installed.
    echo        Run INSTALL.bat again.
    echo.
    set ERRORS=1
) else (
    echo     OK Whisper package installed.
)

echo.
echo ============================================================
if %ERRORS%==0 (
    echo    Everything looks good! You should be able to run it.
    echo    Double-click START_BIOGRAPHER.bat or the desktop shortcut.
) else (
    echo    Some problems found. See above for what to fix.
)
echo ============================================================
echo.
pause
