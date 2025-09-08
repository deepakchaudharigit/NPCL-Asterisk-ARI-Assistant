#!/usr/bin/env python3
"""
Simple script to run all tests for the Voice Assistant project.
This script provides an easy way to execute different test categories.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def print_banner(text):
    """Print a banner with the given text."""
    print("\n" + "="*80)
    print(f"  {text}")
    print("="*80)


def run_command(cmd, description):
    """Run a command and return success status."""
    print(f"\n🚀 {description}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)
    
    try:
        result = subprocess.run(cmd, check=False, text=True)
        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
            return True
        else:
            print(f"❌ {description} - FAILED (exit code: {result.returncode})")
            return False
    except Exception as e:
        print(f"💥 {description} - ERROR: {e}")
        return False


def check_dependencies():
    """Check if required dependencies are installed."""
    print_banner("CHECKING DEPENDENCIES")
    
    required_packages = [
        "pytest",
        "pytest-asyncio", 
        "pytest-mock",
        "pytest-cov"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"✅ {package} - installed")
        except ImportError:
            print(f"❌ {package} - missing")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("Install with: pip install -r requirements-test.txt")
        return False
    
    print("\n✅ All required dependencies are installed!")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Run Voice Assistant tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_all_tests.py                    # Run all tests
  python run_all_tests.py --unit            # Run only unit tests
  python run_all_tests.py --coverage        # Run with coverage
  python run_all_tests.py --fast            # Skip slow tests
  python run_all_tests.py --parallel        # Run in parallel
        """
    )
    
    # Test category options
    parser.add_argument("--all", action="store_true", default=True, help="Run all tests (default)")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--performance", action="store_true", help="Run performance tests only")
    parser.add_argument("--e2e", action="store_true", help="Run end-to-end tests only")
    parser.add_argument("--audio", action="store_true", help="Run audio tests only")
    
    # Test execution options
    parser.add_argument("--coverage", action="store_true", help="Run with coverage reporting")
    parser.add_argument("--parallel", action="store_true", help="Run tests in parallel")
    parser.add_argument("--fast", action="store_true", help="Skip slow tests")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--debug", action="store_true", help="Debug mode (stop on first failure)")
    
    # Output options
    parser.add_argument("--html-report", action="store_true", help="Generate HTML report")
    parser.add_argument("--xml-report", action="store_true", help="Generate XML report")
    
    args = parser.parse_args()
    
    print_banner("VOICE ASSISTANT TEST RUNNER")
    
    # Check dependencies first
    if not check_dependencies():
        print("\n❌ Dependency check failed. Please install missing packages.")
        sys.exit(1)
    
    # Determine which tests to run
    test_categories = []
    if args.unit:
        test_categories.append("unit")
    if args.integration:
        test_categories.append("integration")
    if args.performance:
        test_categories.append("performance")
    if args.e2e:
        test_categories.append("e2e")
    if args.audio:
        test_categories.append("audio")
    
    # If no specific category selected, run all
    if not test_categories:
        test_categories = ["all"]
    
    print_banner(f"RUNNING TESTS: {', '.join(test_categories).upper()}")
    
    # Build pytest command
    base_cmd = [sys.executable, "-m", "pytest"]
    
    # Add test paths/markers
    if "all" in test_categories:
        base_cmd.append("tests/")
    else:
        for category in test_categories:
            if category in ["unit", "integration", "performance", "e2e"]:
                base_cmd.append(f"tests/{category}/")
            elif category == "audio":
                base_cmd.extend(["-m", "audio"])
    
    # Add options
    if args.fast:
        base_cmd.extend(["-m", "not slow"])
    
    if args.verbose:
        base_cmd.append("-vv")
    else:
        base_cmd.append("-v")
    
    if args.debug:
        base_cmd.extend(["-x", "--pdb"])
    
    if args.parallel:
        base_cmd.extend(["-n", "auto"])
    
    # Coverage options
    if args.coverage:
        base_cmd.extend([
            "--cov=src/voice_assistant",
            "--cov-report=term-missing"
        ])
        
        if args.html_report:
            base_cmd.append("--cov-report=html")
        
        if args.xml_report:
            base_cmd.append("--cov-report=xml")
    
    # Report options
    if args.html_report and not args.coverage:
        base_cmd.extend(["--html=reports/test_report.html", "--self-contained-html"])
    
    if args.xml_report and not args.coverage:
        base_cmd.append("--junitxml=reports/junit.xml")
    
    # Additional pytest options
    base_cmd.extend([
        "--tb=short",
        "--color=yes",
        "--strict-markers"
    ])
    
    # Create reports directory if needed
    if args.html_report or args.xml_report:
        Path("reports").mkdir(exist_ok=True)
    
    # Run the tests
    success = run_command(base_cmd, f"Running {', '.join(test_categories)} tests")
    
    # Summary
    print_banner("TEST EXECUTION SUMMARY")
    
    if success:
        print("🎉 ALL TESTS PASSED!")
        
        if args.coverage:
            print("\n📊 Coverage reports generated:")
            if args.html_report:
                print("  📄 HTML: htmlcov/index.html")
            if args.xml_report:
                print("  📄 XML: coverage.xml")
            print("  📄 Terminal: See output above")
        
        if args.html_report and not args.coverage:
            print("\n📊 Test report generated:")
            print("  📄 HTML: reports/test_report.html")
        
        if args.xml_report and not args.coverage:
            print("\n📊 JUnit report generated:")
            print("  📄 XML: reports/junit.xml")
            
    else:
        print("💥 SOME TESTS FAILED!")
        print("\nTo debug failures:")
        print("  1. Run with --debug flag to stop on first failure")
        print("  2. Run with --verbose flag for more details")
        print("  3. Run specific test files: pytest tests/unit/test_specific.py")
        print("  4. Check the test logs above for error details")
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()