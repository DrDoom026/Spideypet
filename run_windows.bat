@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo SpiderPet has not been set up yet. Run setup_windows.bat first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" main.py
if errorlevel 1 (
  echo.
  echo SpiderPet stopped with an error. Read the message above.
  pause
)
