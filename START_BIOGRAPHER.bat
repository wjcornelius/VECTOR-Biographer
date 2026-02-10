@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
python biographer\main_gui.py
