#!/bin/bash
set -e

# NPCL Voice Assistant Docker Entrypoint Script
# Handles initialization, health checks, and graceful shutdown

echo "🚀 Starting NPCL Voice Assistant..."

# Function to handle graceful shutdown
cleanup() {
    echo "🛑 Received shutdown signal, cleaning up..."
    
    # Kill background processes
    if [ ! -z "$HEALTH_CHECK_PID" ]; then
        kill $HEALTH_CHECK_PID 2>/dev/null || true
    fi
    
    # Wait for main process to finish
    if [ ! -z "$MAIN_PID" ]; then
        kill -TERM $MAIN_PID 2>/dev/null || true
        wait $MAIN_PID
    fi
    
    echo "✅ Cleanup completed"
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Environment validation
validate_environment() {
    echo "🔍 Validating environment..."
    
    # Check required environment variables
    if [ -z "$GOOGLE_API_KEY" ] || [ "$GOOGLE_API_KEY" = "your-google-api-key-here" ]; then
        echo "❌ GOOGLE_API_KEY is not set or is placeholder value"
        echo "💡 Please set a valid Google API key in the environment"
        exit 1
    fi
    
    # Check if .env file exists and has required settings
    if [ ! -f ".env" ]; then
        echo "⚠️  .env file not found, using environment variables only"
    fi
    
    # Validate Python environment
    python -c "import src.voice_assistant.core.constants" || {
        echo "❌ Failed to import core modules"
        exit 1
    }
    
    echo "✅ Environment validation passed"
}

# Initialize application
initialize_app() {
    echo "🔧 Initializing application..."
    
    # Create necessary directories
    mkdir -p sounds/temp recordings logs
    
    # Set proper permissions
    chmod 755 sounds recordings logs
    chmod 777 sounds/temp  # Temp directory needs write access
    
    # Initialize logging
    export LOG_LEVEL=${LOG_LEVEL:-INFO}
    export LOG_FORMAT=${LOG_FORMAT:-"%(asctime)s - %(name)s - %(levelname)s - %(message)s"}
    
    # Set application defaults
    export ASSISTANT_NAME=${ASSISTANT_NAME:-"NPCL Assistant"}
    export AUDIO_SAMPLE_RATE=${AUDIO_SAMPLE_RATE:-16000}
    export MAX_CALL_DURATION=${MAX_CALL_DURATION:-3600}
    
    echo "✅ Application initialized"
}

# Health check function
start_health_monitor() {
    echo "🏥 Starting health monitor..."
    
    (
        sleep 30  # Wait for app to start
        while true; do
            if ! curl -f -s http://localhost:8000/health > /dev/null 2>&1; then
                echo "⚠️  Health check failed at $(date)"
            fi
            sleep 30
        done
    ) &
    
    HEALTH_CHECK_PID=$!
    echo "✅ Health monitor started (PID: $HEALTH_CHECK_PID)"
}

# Performance monitoring
start_performance_monitor() {
    if [ "$ENABLE_PERFORMANCE_MONITORING" = "true" ]; then
        echo "📊 Starting performance monitor..."
        
        (
            while true; do
                # Log memory usage
                ps -o pid,ppid,cmd,%mem,%cpu --sort=-%mem -p $MAIN_PID 2>/dev/null | tail -n +2 >> logs/performance.log
                sleep 60
            done
        ) &
        
        echo "✅ Performance monitor started"
    fi
}

# Database migration (if needed)
run_migrations() {
    if [ "$RUN_MIGRATIONS" = "true" ]; then
        echo "🗄️  Running database migrations..."
        python -m src.database.migrate || {
            echo "❌ Database migration failed"
            exit 1
        }
        echo "✅ Database migrations completed"
    fi
}

# Pre-flight checks
preflight_checks() {
    echo "✈️  Running pre-flight checks..."
    
    # Check disk space
    DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ "$DISK_USAGE" -gt 90 ]; then
        echo "⚠️  Warning: Disk usage is ${DISK_USAGE}%"
    fi
    
    # Check memory
    MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
    if [ "$MEMORY_USAGE" -gt 90 ]; then
        echo "⚠️  Warning: Memory usage is ${MEMORY_USAGE}%"
    fi
    
    # Test AI service connectivity
    python -c "
import os
import google.generativeai as genai
try:
    genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content('test')
    print('✅ AI service connectivity test passed')
except Exception as e:
    print(f'⚠️  AI service test failed: {e}')
    print('💡 The application will start but AI features may not work')
" || true
    
    echo "✅ Pre-flight checks completed"
}

# Main execution
main() {
    echo "🎯 NPCL Voice Assistant v${VERSION:-unknown}"
    echo "🏗️  Build: ${BUILD_DATE:-unknown}"
    echo "📦 Environment: ${ENVIRONMENT:-production}"
    
    # Run initialization steps
    validate_environment
    initialize_app
    run_migrations
    preflight_checks
    
    # Start monitoring
    start_health_monitor
    start_performance_monitor
    
    echo "🚀 Starting main application..."
    
    # Execute the main command
    exec "$@" &
    MAIN_PID=$!
    
    echo "✅ Application started (PID: $MAIN_PID)"
    echo "🌐 API available at http://localhost:8000"
    echo "📊 Health check at http://localhost:8000/health"
    echo "📚 API docs at http://localhost:8000/docs"
    
    # Wait for main process
    wait $MAIN_PID
}

# Development mode
if [ "$ENVIRONMENT" = "development" ]; then
    echo "🔧 Running in development mode"
    export LOG_LEVEL=DEBUG
    export ENABLE_PERFORMANCE_MONITORING=true
    
    # Install development dependencies if needed
    if [ -f "requirements-dev.txt" ]; then
        pip install -r requirements-dev.txt
    fi
fi

# Production optimizations
if [ "$ENVIRONMENT" = "production" ]; then
    echo "🏭 Running in production mode"
    export PYTHONOPTIMIZE=1
    export LOG_LEVEL=${LOG_LEVEL:-INFO}
fi

# Execute main function
main "$@"