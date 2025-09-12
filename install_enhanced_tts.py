#!/usr/bin/env python3
"""
Installation script for enhanced TTS dependencies.
This will install Google TTS and pygame for better multilingual speech support.
"""

import subprocess
import sys
import os

def install_package(package):
    """Install a package using pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except subprocess.CalledProcessError:
        return False

def main():
    print("🔊 Enhanced TTS Installation Script")
    print("=" * 50)
    print("This will install enhanced TTS dependencies for better Hindi/multilingual support:")
    print("• gtts (Google Text-to-Speech)")
    print("• pygame (Audio playback)")
    print()
    
    # Ask for confirmation
    response = input("Do you want to proceed? (y/n): ").strip().lower()
    if response not in ['y', 'yes']:
        print("Installation cancelled.")
        return
    
    print("\n📦 Installing enhanced TTS dependencies...")
    
    packages = [
        "gtts>=2.4.0",
        "pygame>=2.5.0"
    ]
    
    success_count = 0
    for package in packages:
        print(f"\nInstalling {package}...")
        if install_package(package):
            print(f"✅ {package} installed successfully")
            success_count += 1
        else:
            print(f"❌ Failed to install {package}")
    
    print(f"\n📊 Installation Summary:")
    print(f"✅ Successfully installed: {success_count}/{len(packages)} packages")
    
    if success_count == len(packages):
        print("\n🎉 All enhanced TTS dependencies installed successfully!")
        print("\nThe NPCL Voice Assistant will now use:")
        print("• Google TTS for better Hindi pronunciation")
        print("• Automatic text cleaning for special characters")
        print("• Fallback to system TTS if needed")
        print("\n💡 Restart the voice assistant to use enhanced TTS.")
    else:
        print("\n⚠️  Some packages failed to install.")
        print("The voice assistant will still work with basic TTS.")
        print("\nYou can try installing manually:")
        for package in packages:
            print(f"  pip install {package}")

if __name__ == "__main__":
    main()