"""
Test runner script for Gemini Voice Assistant tests.
Provides organized test execution with different test categories.
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle the result."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('='*60)
    
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode != 0:
        print(f"\n❌ {description} failed with exit code {result.returncode}")
        return False
    else:
        print(f"\n✅ {description} completed successfully")
        return True


def main():
    parser = argparse.ArgumentParser(description="Run Gemini Voice Assistant tests")
    parser.add_argument(
        "--category", 
        choices=["all", "unit", "integration", "performance", "audio", "websocket", "e2e"],
        default="all",
        help="Test category to run"
    )
    parser.add_argument(
        "--coverage", 
        action="store_true",
        help="Run with coverage reporting"
    )
    parser.add_argument(
        "--parallel", 
        action="store_true",
        help="Run tests in parallel"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--fast", 
        action="store_true",
        help="Skip slow tests"
    )
    
    args = parser.parse_args()
    
    # Base pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add test directory
    test_dir = Path(__file__).parent
    
    # Select test category
    if args.category == "all":
        cmd.append(str(test_dir))
    elif args.category == "unit":
        cmd.append(str(test_dir / "unit"))
    elif args.category == "integration":
        cmd.append(str(test_dir / "integration"))
    elif args.category == "performance":
        cmd.append(str(test_dir / "performance"))
    elif args.category == "audio":
        cmd.extend(["-m", "audio"])
    elif args.category == "websocket":
        cmd.extend(["-m", "websocket"])
    elif args.category == "e2e":
        cmd.extend(["-m", "e2e"])
    
    # Add markers
    if args.fast:
        cmd.extend(["-m", "not slow"])
    
    # Add coverage
    if args.coverage:
        cmd.extend([
            "--cov=src/voice_assistant",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--cov-report=xml"
        ])
    
    # Add parallel execution
    if args.parallel:
        cmd.extend(["-n", "auto"])
    
    # Add verbosity
    if args.verbose:
        cmd.append("-vv")
    else:
        cmd.append("-v")
    
    # Additional options
    cmd.extend([
        "--tb=short",
        "--color=yes",
        "--strict-markers"
    ])
    
    # Run the tests
    success = run_command(cmd, f"{args.category.title()} Tests")
    
    if success:
        print(f"\n🎉 All {args.category} tests passed!")
        
        if args.coverage:
            print("\n📊 Coverage report generated:")
            print("  - HTML: htmlcov/index.html")
            print("  - XML: coverage.xml")
    else:
        print(f"\n💥 Some {args.category} tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()