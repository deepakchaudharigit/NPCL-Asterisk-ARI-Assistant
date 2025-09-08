#!/usr/bin/env python3
"""
Run ARI server with automatic dependency installation
"""

import subprocess
import sys
import os
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import fastapi
        import uvicorn
        print("✅ FastAPI and Uvicorn are available")
        return True
    except ImportError:
        print("❌ Missing FastAPI or Uvicorn")
        return False

def install_dependencies():
    """Install required dependencies"""
    deps = ["fastapi>=0.104.0", "uvicorn>=0.24.0"]
    
    for dep in deps:
        try:
            print(f"📦 Installing {dep}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install {dep}: {e}")
            return False
    return True

def run_simple_ari():
    """Run simple ARI handler"""
    try:
        print("🚀 Starting Simple Advanced ARI Handler...")
        print("📡 Server will be available at: http://localhost:8000")
        print("📋 API docs at: http://localhost:8000/docs")
        print("💡 Press Ctrl+C to stop")
        print("-" * 50)
        
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "src.voice_assistant.telephony.simple_ari_handler:create_simple_advanced_ari_app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ])
    except KeyboardInterrupt:
        print("\n👋 ARI server stopped")
    except Exception as e:
        print(f"❌ Failed to start server: {e}")

def run_full_ari():
    """Run full ARI handler with WebSocket support"""
    try:
        # First install websockets
        print("📦 Installing websockets...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "websockets>=11.0.0"])
        
        print("🚀 Starting Full Advanced ARI Handler...")
        print("📡 Server will be available at: http://localhost:8000")
        print("🔌 WebSocket support enabled")
        print("📋 API docs at: http://localhost:8000/docs")
        print("💡 Press Ctrl+C to stop")
        print("-" * 50)
        
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "src.voice_assistant.telephony.advanced_ari_handler:create_advanced_ari_app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ])
    except KeyboardInterrupt:
        print("\n👋 ARI server stopped")
    except Exception as e:
        print(f"❌ Failed to start full server: {e}")
        print("💡 Falling back to simple ARI handler...")
        run_simple_ari()

def main():
    """Main function"""
    print("🤖 Voice Assistant ARI Server Launcher")
    print("=" * 50)
    
    # Check if dependencies are available
    if not check_dependencies():
        print("📦 Installing required dependencies...")
        if not install_dependencies():
            print("❌ Failed to install dependencies")
            return 1
    
    print("\n🎯 Choose ARI handler version:")
    print("1. Simple ARI Handler (recommended, no WebSocket)")
    print("2. Full ARI Handler (with WebSocket support)")
    print("3. Auto-detect (try full, fallback to simple)")
    
    try:
        choice = input("\nEnter choice (1-3) [default: 1]: ").strip()
        if not choice:
            choice = "1"
        
        if choice == "1":
            run_simple_ari()
        elif choice == "2":
            run_full_ari()
        elif choice == "3":
            try:
                import websockets
                print("✅ WebSocket support detected, using full handler")
                run_full_ari()
            except ImportError:
                print("⚠️  WebSocket not available, using simple handler")
                run_simple_ari()
        else:
            print("❌ Invalid choice, using simple handler")
            run_simple_ari()
            
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        return 0
    
    return 0

if __name__ == "__main__":
    sys.exit(main())