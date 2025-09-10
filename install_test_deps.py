#!/usr/bin/env python3
"""
Install missing test dependencies
"""

import subprocess
import sys
import os

def run_command(command):
    """Run a command and return success status"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def main():
    print("=" * 80)
    print("  INSTALLING TEST DEPENDENCIES")
    print("=" * 80)
    
    # Check if we're in a virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Virtual environment detected")
    else:
        print("⚠️  Virtual environment not detected - installing globally")
    
    # Install the missing packages directly
    missing_packages = [
        "pytest-mock>=3.10.0",
        "pytest-cov>=4.0.0"
    ]
    
    print(f"\n📦 Installing missing packages...")
    
    for package in missing_packages:
        print(f"  Installing {package}...")
        success, stdout, stderr = run_command(f"pip install {package}")
        
        if success:
            print(f"  ✅ {package} installed successfully")
        else:
            print(f"  ❌ Failed to install {package}")
            print(f"     Error: {stderr}")
    
    # Try to install all test requirements
    print(f"\n📋 Installing all test requirements...")
    success, stdout, stderr = run_command("pip install -r requirements-test.txt")
    
    if success:
        print("✅ All test requirements installed successfully")
    else:
        print("⚠️  Some packages may have failed to install")
        print(f"Output: {stdout}")
        if stderr:
            print(f"Errors: {stderr}")
    
    # Verify installation
    print(f"\n🔍 Verifying installations...")
    
    test_packages = ["pytest", "pytest-asyncio", "pytest-mock", "pytest-cov"]
    all_installed = True
    
    for package in test_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"  ✅ {package} - available")
        except ImportError:
            print(f"  ❌ {package} - missing")
            all_installed = False
    
    if all_installed:
        print("\n🎉 All test dependencies are now installed!")
        print("\n🚀 You can now run tests with:")
        print("   python run_all_tests.py")
        return 0
    else:
        print("\n❌ Some dependencies are still missing")
        print("\n💡 Try running manually:")
        print("   pip install pytest pytest-asyncio pytest-mock pytest-cov")
        return 1

if __name__ == "__main__":
    sys.exit(main())