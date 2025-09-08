#!/bin/bash
# Start script for Gemini Voice Assistant - Real-time ARI

echo "🚀 Starting Gemini Voice Assistant - Real-time ARI..."

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "Please copy .env.example to .env and configure your settings"
    exit 1
fi

# Start the server
echo "Starting FastAPI server..."
python src/run_realtime_server.py