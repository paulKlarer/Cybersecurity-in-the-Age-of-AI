@echo off
setlocal

cd /d "%~dp0\.."

if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"

python evaluator.py --phase screening --condition-id screening-real-clear_allowed-neutral-neutral_assistant-none --runs-per-condition 1
if errorlevel 1 exit /b 1

endlocal
