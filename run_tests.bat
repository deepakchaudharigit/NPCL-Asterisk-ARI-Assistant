@echo off
REM Batch script to run Voice Assistant tests on Windows

echo ================================================================================
echo                        VOICE ASSISTANT TEST RUNNER
echo ================================================================================

REM Check if virtual environment is activated
if not defined VIRTUAL_ENV (
    echo Activating virtual environment...
    if exist .venv\Scripts\activate.bat (
        call .venv\Scripts\activate.bat
    ) else (
        echo Warning: Virtual environment not found at .venv\Scripts\activate.bat
        echo Please ensure you have created a virtual environment or activate it manually
    )
)

REM Check if pytest is available
python -c "import pytest" 2>nul
if errorlevel 1 (
    echo Error: pytest not found. Installing test dependencies...
    pip install -r requirements-test.txt
    if errorlevel 1 (
        echo Failed to install test dependencies
        pause
        exit /b 1
    )
)

echo.
echo Choose test category to run:
echo 1. All tests
echo 2. Unit tests only
echo 3. Integration tests only
echo 4. Performance tests only
echo 5. Audio tests only
echo 6. All tests with coverage
echo 7. Quick tests (no slow tests)
echo 8. Parallel execution (all tests)
echo.

set /p choice="Enter your choice (1-8): "

if "%choice%"=="1" (
    echo Running all tests...
    python -m pytest tests/ -v
) else if "%choice%"=="2" (
    echo Running unit tests...
    python -m pytest tests/unit/ -v
) else if "%choice%"=="3" (
    echo Running integration tests...
    python -m pytest tests/integration/ -v
) else if "%choice%"=="4" (
    echo Running performance tests...
    python -m pytest tests/performance/ -v
) else if "%choice%"=="5" (
    echo Running audio tests...
    python -m pytest -m audio -v
) else if "%choice%"=="6" (
    echo Running all tests with coverage...
    python -m pytest tests/ --cov=src/voice_assistant --cov-report=html --cov-report=term-missing -v
    echo.
    echo Coverage report generated at: htmlcov/index.html
) else if "%choice%"=="7" (
    echo Running quick tests (excluding slow tests)...
    python -m pytest tests/ -m "not slow" -v
) else if "%choice%"=="8" (
    echo Running tests in parallel...
    python -m pytest tests/ -n auto -v
) else (
    echo Invalid choice. Running all tests by default...
    python -m pytest tests/ -v
)

echo.
echo ================================================================================
echo                              TEST EXECUTION COMPLETE
echo ================================================================================

if errorlevel 1 (
    echo.
    echo Some tests failed. Check the output above for details.
    echo.
    echo Common troubleshooting steps:
    echo 1. Ensure all dependencies are installed: pip install -r requirements-test.txt
    echo 2. Check environment variables in .env file
    echo 3. Run specific failing tests for more details
    echo.
) else (
    echo.
    echo All tests passed successfully!
    echo.
)

pause