@echo off
setlocal
cd /d "%~dp0"

echo === SpiderPet Windows setup ===
where py >nul 2>nul
if errorlevel 1 (
  echo Python Launcher 'py' was not found.
  echo Install 64-bit Python 3.10 or newer from https://www.python.org/downloads/windows/
  echo During setup, enable the Python Launcher and optionally add Python to PATH.
  pause
  exit /b 1
)

py -3 -m venv .venv
if errorlevel 1 goto :failed
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :failed
".venv\Scripts\python.exe" -m pip install -r requirements-windows.txt
if errorlevel 1 goto :failed

echo.
echo Setup complete. Double-click run_windows.bat to start SpiderPet.
pause
exit /b 0

:failed
echo.
echo Setup failed. Read the error above and check your Python installation/network.
pause
exit /b 1
