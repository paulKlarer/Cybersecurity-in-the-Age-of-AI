@echo off
setlocal

cd /d "%~dp0\.."

if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"

docker image inspect ai-agent-eval >nul 2>nul
if errorlevel 1 (
    echo Docker image ai-agent-eval not found. Building it now...
    docker build -t ai-agent-eval .
    if errorlevel 1 exit /b 1
)

python evaluator.py --phase screening --max-conditions 5 --runs-per-condition 1 --skip-docker-build
if errorlevel 1 exit /b 1

endlocal
