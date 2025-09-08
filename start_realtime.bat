@echo off
REM Start script for Gemini Voice Assistant - Real-time ARI

echo 🚀 Starting Gemini Voice Assistant - Real-time ARI...

REM Activate virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
)

REM Check if .env file exists
if not exist ".env" (
    echo ❌ .env file not found!
    echo Please copy .env.example to .env and configure your settings
    pause
    exit /b 1
)

REM Start the server
echo Starting FastAPI server...
python src\run_realtime_server.py
pause