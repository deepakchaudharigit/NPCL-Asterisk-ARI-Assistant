#!/usr/bin/env python3
"""
Installation script for voice recognition features.
This will install speech recognition and audio input dependencies.
"""

import subprocess
import sys
import os
import platform

def install_package(package):
    """Install a package using pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except subprocess.CalledProcessError:
        return False

def install_system_dependencies():
    """Install system-level dependencies for audio"""
    system = platform.system().lower()
    
    if system == "linux":
        print("📦 Installing Linux audio dependencies...")
        try:
            # Try to install portaudio for pyaudio
            subprocess.run(["sudo", "apt-get", "update"], check=False)
            subprocess.run(["sudo", "apt-get", "install", "-y", "portaudio19-dev", "python3-pyaudio"], check=False)
            return True
        except:
            print("⚠️  Could not install system dependencies. You may need to install portaudio manually.")
            return False
    
    elif system == "darwin":  # macOS
        print("📦 Installing macOS audio dependencies...")
        try:
            # Try to install portaudio via homebrew
            subprocess.run(["brew", "install", "portaudio"], check=False)
            return True
        except:
            print("⚠️  Could not install via homebrew. You may need to install portaudio manually.")
            return False
    
    else:  # Windows
        print("📦 Windows detected - pyaudio should install directly")
        return True

def main():
    print("🎤 Voice Features Installation Script")
    print("=" * 50)
    print("This will install voice recognition dependencies:")
    print("• SpeechRecognition (Google Speech API)")
    print("• pyaudio (Microphone input)")
    print("• Enhanced TTS dependencies (if not already installed)")
    print()
    
    # Ask for confirmation
    response = input("Do you want to proceed? (y/n): ").strip().lower()
    if response not in ['y', 'yes']:
        print("Installation cancelled.")
        return
    
    print("\n🔧 Installing system dependencies...")
    install_system_dependencies()
    
    print("\n📦 Installing Python packages...")
    
    packages = [
        "SpeechRecognition>=3.10.0",
        "pyaudio>=0.2.11",
        "gtts>=2.4.0",
        "pygame>=2.5.0"
    ]
    
    success_count = 0
    failed_packages = []
    
    for package in packages:
        print(f"\nInstalling {package}...")
        if install_package(package):
            print(f"✅ {package} installed successfully")
            success_count += 1
        else:
            print(f"❌ Failed to install {package}")
            failed_packages.append(package)
    
    print(f"\n📊 Installation Summary:")
    print(f"✅ Successfully installed: {success_count}/{len(packages)} packages")
    
    if success_count == len(packages):
        print("\n🎉 All voice features installed successfully!")
        print("\nThe NPCL Voice Assistant now supports:")
        print("• 🎤 Voice input with 10-second timeout")
        print("• 💬 Automatic fallback to chat mode")
        print("• 🔊 Enhanced voice output")
        print("• 🌍 Multilingual speech recognition")
        print("\n💡 Restart the voice assistant and select Voice Mode (option 2).")
        
        # Test voice functionality
        print("\n🧪 Testing voice functionality...")
        try:
            import speech_recognition as sr
            import pyaudio
            print("✅ Speech recognition: Available")
            print("✅ Microphone input: Available")
            
            # Quick microphone test
            r = sr.Recognizer()
            mic = sr.Microphone()
            print("✅ Microphone initialization: Success")
            
        except ImportError as e:
            print(f"⚠️  Import test failed: {e}")
        except Exception as e:
            print(f"⚠️  Microphone test failed: {e}")
            print("💡 This might be normal if no microphone is connected.")
    
    else:
        print(f"\n⚠️  {len(failed_packages)} packages failed to install:")
        for package in failed_packages:
            print(f"  • {package}")
        
        print("\n🔧 Troubleshooting:")
        print("1. For pyaudio issues on Linux:")
        print("   sudo apt-get install portaudio19-dev python3-pyaudio")
        print("2. For pyaudio issues on macOS:")
        print("   brew install portaudio")
        print("3. For Windows, try:")
        print("   pip install pipwin")
        print("   pipwin install pyaudio")
        print("\n💡 You can still use chat mode and basic TTS without voice input.")

if __name__ == "__main__":
    main()