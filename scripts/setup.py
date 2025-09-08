#!/usr/bin/env python3
"""
Setup script for Voice Assistant with Gemini 2.5 Flash
"""

import os
import sys
import subprocess
from pathlib import Path


def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"   Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True


def check_virtual_environment():
    """Check if virtual environment is active"""
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Virtual environment: Active")
        return True
    else:
        print("⚠️  Virtual environment: Not detected")
        print("   Recommendation: Activate virtual environment first")
        return False


def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False


def setup_environment():
    """Setup environment configuration"""
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if env_file.exists():
        print("✅ .env file already exists")
        return True
    
    if env_example.exists():
        print("📝 Creating .env file from template...")
        try:
            env_example.read_text()
            with open(env_file, 'w') as f:
                f.write(env_example.read_text())
            print("✅ .env file created")
            print("⚠️  Please edit .env and add your Google API key")
            return True
        except Exception as e:
            print(f"❌ Failed to create .env file: {e}")
            return False
    else:
        print("❌ .env.example file not found")
        return False


def create_directories():
    """Create necessary directories"""
    directories = ["sounds", "sounds/temp", "logs"]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("✅ Directories created")


def test_installation():
    """Test the installation"""
    print("🧪 Testing installation...")
    try:
        # Test imports
        sys.path.insert(0, "src")
        from voice_assistant.ai.gemini_client import GeminiClient
        from voice_assistant.audio.speech_recognition import SpeechRecognizer
        from voice_assistant.audio.text_to_speech import TextToSpeech
        from config.settings import get_settings
        
        print("✅ All modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def main():
    """Main setup function"""
    print("🚀 Voice Assistant with Gemini 2.5 Flash - Setup")
    print("=" * 60)
    
    # Check requirements
    if not check_python_version():
        return 1
    
    check_virtual_environment()
    
    # Setup steps
    steps = [
        ("Installing dependencies", install_dependencies),
        ("Setting up environment", setup_environment),
        ("Creating directories", create_directories),
        ("Testing installation", test_installation),
    ]
    
    for step_name, step_func in steps:
        print(f"\n{step_name}...")
        if not step_func():
            print(f"❌ Setup failed at: {step_name}")
            return 1
    
    print("\n" + "=" * 60)
    print("🎉 Setup completed successfully!")
    print("\n📝 Next steps:")
    print("1. Edit .env file and add your Google API key")
    print("2. Get API key from: https://aistudio.google.com/")
    print("3. Run the assistant: python src/main.py")
    print("\n💡 For help, see docs/README.md")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())