@echo off
setlocal

cd /d "%~dp0\.."

if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"

python deep_dive_report.py
if errorlevel 1 exit /b 1

endlocal
