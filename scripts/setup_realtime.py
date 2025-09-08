"""
Setup script for the Real-time Gemini Voice Assistant with Asterisk ARI.
This script helps configure and validate the environment for the real-time integration.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import get_settings


class RealtimeSetup:
    """Setup and validation for real-time Gemini Voice Assistant"""
    
    def __init__(self):
        self.project_root = project_root
        self.logger = self._setup_logging()
        self.settings = None
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for setup script"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
    
    def run_setup(self) -> bool:
        """Run complete setup process"""
        try:
            print("\\n" + "="*80)
            print("🚀 GEMINI VOICE ASSISTANT - REAL-TIME SETUP")
            print("="*80)
            
            # Step 1: Check environment
            if not self.check_environment():
                return False
            
            # Step 2: Validate configuration
            if not self.validate_configuration():
                return False
            
            # Step 3: Create directories
            if not self.create_directories():
                return False
            
            # Step 4: Check dependencies
            if not self.check_dependencies():
                return False
            
            # Step 5: Test connections
            if not self.test_connections():
                return False
            
            # Step 6: Generate startup scripts
            if not self.generate_startup_scripts():
                return False
            
            print("\\n" + "="*80)
            print("✅ SETUP COMPLETED SUCCESSFULLY!")
            print("="*80)
            self.print_next_steps()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Setup failed: {e}")
            return False
    
    def check_environment(self) -> bool:
        """Check environment requirements"""
        print("\\n🔍 Checking Environment...")
        
        # Check Python version
        python_version = sys.version_info
        if python_version < (3, 8):
            print(f"❌ Python 3.8+ required, found {python_version.major}.{python_version.minor}")
            return False
        print(f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
        
        # Check virtual environment
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            print("✅ Virtual environment detected")
        else:
            print("⚠️  Virtual environment not detected (recommended)")
        
        # Check .env file
        env_file = self.project_root / ".env"
        if env_file.exists():
            print("✅ .env file found")
        else:
            print("⚠️  .env file not found, copying from .env.example")
            example_file = self.project_root / ".env.example"
            if example_file.exists():
                import shutil
                shutil.copy(example_file, env_file)
                print("✅ .env file created from example")
            else:
                print("❌ .env.example file not found")
                return False
        
        return True
    
    def validate_configuration(self) -> bool:
        """Validate configuration settings"""
        print("\\n⚙️  Validating Configuration...")
        
        try:
            self.settings = get_settings()
            
            # Check Google API key
            if not self.settings.google_api_key or self.settings.google_api_key == "your-google-api-key-here":
                print("❌ Google API key not configured")
                print("   Please set GOOGLE_API_KEY in your .env file")
                print("   Get your API key from: https://aistudio.google.com/")
                return False
            print("✅ Google API key configured")
            
            # Validate audio settings
            if self.settings.audio_format != "slin16":
                print(f"⚠️  Audio format is {self.settings.audio_format}, recommended: slin16")
            else:
                print("✅ Audio format: slin16 (optimal for Asterisk)")
            
            if self.settings.audio_sample_rate != 16000:
                print(f"⚠️  Sample rate is {self.settings.audio_sample_rate}Hz, recommended: 16000Hz")
            else:
                print("✅ Sample rate: 16000Hz (optimal for Gemini Live)")
            
            # Validate ARI settings
            print(f"✅ ARI endpoint: {self.settings.ari_base_url}")
            print(f"✅ Stasis app: {self.settings.stasis_app}")
            print(f"✅ External media: {self.settings.external_media_host}:{self.settings.external_media_port}")
            
            return True
            
        except Exception as e:
            print(f"❌ Configuration validation failed: {e}")
            return False
    
    def create_directories(self) -> bool:
        """Create required directories"""
        print("\\n📁 Creating Directories...")
        
        directories = [
            self.settings.sounds_dir,
            self.settings.temp_audio_dir,
            self.settings.recordings_dir,
            "logs"
        ]
        
        for directory in directories:
            dir_path = self.project_root / directory
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                print(f"✅ {directory}/")
            except Exception as e:
                print(f"❌ Failed to create {directory}/: {e}")
                return False
        
        return True
    
    def check_dependencies(self) -> bool:
        """Check Python dependencies"""
        print("\\n📦 Checking Dependencies...")
        
        required_packages = [
            "google-generativeai",
            "websockets",
            "fastapi",
            "uvicorn",
            "pydantic",
            "requests",
            "numpy"
        ]
        
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package.replace("-", "_"))
                print(f"✅ {package}")
            except ImportError:
                print(f"❌ {package} (missing)")
                missing_packages.append(package)
        
        if missing_packages:
            print(f"\\n⚠️  Missing packages: {', '.join(missing_packages)}")
            print("Run: pip install -r requirements.txt")
            return False
        
        return True
    
    def test_connections(self) -> bool:
        """Test external connections"""
        print("\\n🔗 Testing Connections...")
        
        # Test Google API (basic check)
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.settings.google_api_key)
            print("✅ Google Generative AI library configured")
        except Exception as e:
            print(f"❌ Google API configuration failed: {e}")
            return False
        
        # Test ARI endpoint (basic connectivity)
        try:
            import requests
            response = requests.get(
                f"{self.settings.ari_base_url.replace('/ari', '')}/ari/asterisk/info",
                auth=(self.settings.ari_username, self.settings.ari_password),
                timeout=5
            )
            if response.status_code == 200:
                print("✅ Asterisk ARI endpoint accessible")
            else:
                print(f"⚠️  Asterisk ARI endpoint returned status {response.status_code}")
        except Exception as e:
            print(f"⚠️  Asterisk ARI endpoint not accessible: {e}")
            print("   This is normal if Asterisk is not running yet")
        
        return True
    
    def generate_startup_scripts(self) -> bool:
        """Generate startup scripts"""
        print("\\n📜 Generating Startup Scripts...")
        
        # Create start script
        start_script = self.project_root / "start_realtime.sh"
        start_content = f"""#!/bin/bash
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
"""
        
        try:
            with open(start_script, 'w') as f:
                f.write(start_content)
            os.chmod(start_script, 0o755)
            print("✅ start_realtime.sh")
        except Exception as e:
            print(f"❌ Failed to create start script: {e}")
            return False
        
        # Create Windows batch file
        start_bat = self.project_root / "start_realtime.bat"
        bat_content = f"""@echo off
REM Start script for Gemini Voice Assistant - Real-time ARI

echo 🚀 Starting Gemini Voice Assistant - Real-time ARI...

REM Activate virtual environment if it exists
if exist ".venv\\Scripts\\activate.bat" (
    echo Activating virtual environment...
    call .venv\\Scripts\\activate.bat
)

REM Check if .env file exists
if not exist ".env" (
    echo ❌ .env file not found!
    echo Please copy .env.example to .env and configure your settings
    pause
    exit /b 1
)

REM Start the server
echo Starting FastAPI server...
python src\\run_realtime_server.py
pause
"""
        
        try:
            with open(start_bat, 'w') as f:
                f.write(bat_content)
            print("✅ start_realtime.bat")
        except Exception as e:
            print(f"❌ Failed to create Windows batch file: {e}")
            return False
        
        return True
    
    def print_next_steps(self):
        """Print next steps for the user"""
        print("\\n📋 NEXT STEPS:")
        print("-" * 40)
        print("1. Configure your .env file:")
        print("   - Set your Google API key (GOOGLE_API_KEY)")
        print("   - Adjust Asterisk ARI settings if needed")
        print("   - Configure external media host/port")
        print()
        print("2. Configure Asterisk:")
        print("   - Copy asterisk-config/* to your Asterisk configuration directory")
        print("   - Restart Asterisk to load new configuration")
        print("   - Ensure ARI is enabled and accessible")
        print()
        print("3. Start the application:")
        print("   Linux/Mac: ./start_realtime.sh")
        print("   Windows:   start_realtime.bat")
        print("   Manual:    python src/run_realtime_server.py")
        print()
        print("4. Test the integration:")
        print("   - Call extension 1000 for Gemini conversation")
        print("   - Call extension 1001 for external media test")
        print("   - Call extension 1002 for basic audio test")
        print()
        print("5. Monitor the system:")
        print("   - Check logs for any errors")
        print("   - Visit http://localhost:8000/docs for API documentation")
        print("   - Use http://localhost:8000/status for system status")
        print()
        print("🎉 Enjoy your real-time AI voice assistant!")


def main():
    """Main entry point"""
    setup = RealtimeSetup()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Gemini Voice Assistant - Real-time Setup")
        print("Usage: python scripts/setup_realtime.py")
        print()
        print("This script will:")
        print("- Check environment requirements")
        print("- Validate configuration")
        print("- Create required directories")
        print("- Check dependencies")
        print("- Test connections")
        print("- Generate startup scripts")
        return
    
    success = setup.run_setup()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()