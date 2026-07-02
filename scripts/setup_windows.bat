@echo off
setlocal

cd /d "%~dp0\.."

echo Creating Python virtual environment...
python -m venv .venv
if errorlevel 1 exit /b 1

call ".venv\Scripts\activate.bat"
if errorlevel 1 exit /b 1

echo Installing Python dependencies...
python -m pip install --upgrade pip
if errorlevel 1 exit /b 1

python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

echo Running unit tests...
python -m unittest discover
if errorlevel 1 exit /b 1

echo Setup complete.
endlocal
