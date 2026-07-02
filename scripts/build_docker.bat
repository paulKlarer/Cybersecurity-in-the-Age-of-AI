@echo off
setlocal

cd /d "%~dp0\.."

echo Building Docker image ai-agent-eval...
docker build -t ai-agent-eval .
if errorlevel 1 exit /b 1

echo Docker image built.
endlocal
