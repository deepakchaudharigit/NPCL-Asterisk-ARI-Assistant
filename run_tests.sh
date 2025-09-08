#!/bin/bash

# Shell script to run Voice Assistant tests on Linux/Mac

set -e  # Exit on any error

echo "================================================================================"
echo "                        VOICE ASSISTANT TEST RUNNER"
echo "================================================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    print_warning "Virtual environment not detected"
    if [[ -f ".venv/bin/activate" ]]; then
        print_status "Activating virtual environment..."
        source .venv/bin/activate
    elif [[ -f "venv/bin/activate" ]]; then
        print_status "Activating virtual environment..."
        source venv/bin/activate
    else
        print_warning "No virtual environment found. Continuing with system Python..."
    fi
fi

# Check if pytest is available
if ! python -c "import pytest" 2>/dev/null; then
    print_error "pytest not found. Installing test dependencies..."
    pip install -r requirements-test.txt
    if [[ $? -ne 0 ]]; then
        print_error "Failed to install test dependencies"
        exit 1
    fi
fi

# Function to run tests with error handling
run_tests() {
    local cmd="$1"
    local description="$2"
    
    print_status "Running: $description"
    echo "Command: $cmd"
    echo "--------------------------------------------------------------------------------"
    
    if eval "$cmd"; then
        print_success "$description completed successfully"
        return 0
    else
        print_error "$description failed"
        return 1
    fi
}

# Parse command line arguments
COVERAGE=false
PARALLEL=false
FAST=false
VERBOSE=false
CATEGORY="all"

while [[ $# -gt 0 ]]; do
    case $1 in
        --coverage)
            COVERAGE=true
            shift
            ;;
        --parallel)
            PARALLEL=true
            shift
            ;;
        --fast)
            FAST=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --unit)
            CATEGORY="unit"
            shift
            ;;
        --integration)
            CATEGORY="integration"
            shift
            ;;
        --performance)
            CATEGORY="performance"
            shift
            ;;
        --audio)
            CATEGORY="audio"
            shift
            ;;
        --e2e)
            CATEGORY="e2e"
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --coverage      Run with coverage reporting"
            echo "  --parallel      Run tests in parallel"
            echo "  --fast          Skip slow tests"
            echo "  --verbose       Verbose output"
            echo "  --unit          Run unit tests only"
            echo "  --integration   Run integration tests only"
            echo "  --performance   Run performance tests only"
            echo "  --audio         Run audio tests only"
            echo "  --e2e           Run end-to-end tests only"
            echo "  --help          Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                          # Run all tests"
            echo "  $0 --coverage               # Run with coverage"
            echo "  $0 --unit --fast            # Run unit tests, skip slow ones"
            echo "  $0 --parallel --coverage    # Run in parallel with coverage"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# If no arguments provided, show interactive menu
if [[ $# -eq 0 ]] && [[ -t 0 ]]; then
    echo ""
    echo "Choose test category to run:"
    echo "1. All tests"
    echo "2. Unit tests only"
    echo "3. Integration tests only"
    echo "4. Performance tests only"
    echo "5. Audio tests only"
    echo "6. End-to-end tests only"
    echo "7. All tests with coverage"
    echo "8. Quick tests (no slow tests)"
    echo "9. Parallel execution (all tests)"
    echo ""
    
    read -p "Enter your choice (1-9): " choice
    
    case $choice in
        1) CATEGORY="all" ;;
        2) CATEGORY="unit" ;;
        3) CATEGORY="integration" ;;
        4) CATEGORY="performance" ;;
        5) CATEGORY="audio" ;;
        6) CATEGORY="e2e" ;;
        7) CATEGORY="all"; COVERAGE=true ;;
        8) CATEGORY="all"; FAST=true ;;
        9) CATEGORY="all"; PARALLEL=true ;;
        *) print_warning "Invalid choice. Running all tests by default..."; CATEGORY="all" ;;
    esac
fi

# Build pytest command
CMD="python -m pytest"

# Add test paths/markers based on category
case $CATEGORY in
    "all")
        CMD="$CMD tests/"
        ;;
    "unit")
        CMD="$CMD tests/unit/"
        ;;
    "integration")
        CMD="$CMD tests/integration/"
        ;;
    "performance")
        CMD="$CMD tests/performance/"
        ;;
    "audio")
        CMD="$CMD -m audio"
        ;;
    "e2e")
        CMD="$CMD tests/e2e/"
        ;;
esac

# Add options
if [[ "$FAST" == true ]]; then
    CMD="$CMD -m 'not slow'"
fi

if [[ "$VERBOSE" == true ]]; then
    CMD="$CMD -vv"
else
    CMD="$CMD -v"
fi

if [[ "$PARALLEL" == true ]]; then
    CMD="$CMD -n auto"
fi

if [[ "$COVERAGE" == true ]]; then
    CMD="$CMD --cov=src/voice_assistant --cov-report=html --cov-report=term-missing"
fi

# Additional pytest options
CMD="$CMD --tb=short --color=yes --strict-markers"

# Create reports directory if needed
mkdir -p reports

# Run the tests
echo ""
print_status "Executing test command..."
echo "Category: $CATEGORY"
echo "Coverage: $COVERAGE"
echo "Parallel: $PARALLEL"
echo "Fast mode: $FAST"
echo ""

if run_tests "$CMD" "$CATEGORY tests"; then
    echo ""
    echo "================================================================================"
    echo "                              TEST EXECUTION SUMMARY"
    echo "================================================================================"
    print_success "ALL TESTS PASSED!"
    
    if [[ "$COVERAGE" == true ]]; then
        echo ""
        print_status "Coverage reports generated:"
        echo "  📄 HTML: htmlcov/index.html"
        echo "  📄 Terminal: See output above"
    fi
    
    echo ""
    print_success "Test execution completed successfully!"
    
else
    echo ""
    echo "================================================================================"
    echo "                              TEST EXECUTION SUMMARY"
    echo "================================================================================"
    print_error "SOME TESTS FAILED!"
    echo ""
    echo "To debug failures:"
    echo "  1. Run with --verbose flag for more details"
    echo "  2. Run specific test files: pytest tests/unit/test_specific.py"
    echo "  3. Use pytest -x to stop on first failure"
    echo "  4. Use pytest --pdb to drop into debugger on failure"
    echo ""
    
    exit 1
fi