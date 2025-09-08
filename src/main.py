<<<<<<< HEAD
#!/usr/bin/env python3
"""
Voice Assistant with Gemini 2.5 Flash - Main Entry Point
Professional voice assistant system
"""

import sys
import os
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent))

import logging
from voice_assistant.core.assistant import VoiceAssistant, AssistantState
from voice_assistant.utils.logger import setup_logger
from config.settings import get_settings


def print_banner():
    """Print application banner"""
    print("=" * 60)
    print("🤖 Voice Assistant with Gemini 2.5 Flash")
    print("Professional Voice Assistant System")
    print("=" * 60)


def print_status_info():
    """Print system status information"""
    settings = get_settings()
    
    print("✅ System Information:")
    print(f"   Assistant Name: {settings.assistant_name}")
    print(f"   AI Model: {settings.gemini_model}")
    print(f"   Voice Language: {settings.voice_language}")
    print(f"   Listen Timeout: {settings.listen_timeout}s")
    
    # Check virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Virtual environment: Active")
    else:
        print("⚠️  Virtual environment: Not detected")
    
    # Check .env file
    if Path(".env").exists():
        print("✅ Configuration: .env file found")
    else:
        print("❌ Configuration: .env file not found")
        return False
    
    # Check API key
    if settings.google_api_key and settings.google_api_key != "your-google-api-key-here":
        print("✅ Google API Key: Configured")
    else:
        print("❌ Google API Key: Not configured")
        return False
    
    return True


def on_state_change(state: AssistantState):
    """Handle assistant state changes"""
    state_messages = {
        AssistantState.IDLE: "💤 Ready - Waiting for input",
        AssistantState.LISTENING: "🎤 Listening - Speak now",
        AssistantState.PROCESSING: "🧠 Processing - Thinking...",
        AssistantState.SPEAKING: "🗣️  Speaking - Response ready",
        AssistantState.ERROR: "❌ Error - Please check logs"
    }
    
    message = state_messages.get(state, f"Unknown state: {state}")
    print(f"\n[{message}]")


def on_user_speech(text: str):
    """Handle user speech events"""
    print(f"👤 You: {text}")


def on_assistant_response(text: str):
    """Handle assistant response events"""
    print(f"🤖 Assistant: {text}")


def main():
    """Main application entry point"""
    print_banner()
    
    # Setup logging
    logger = setup_logger()
    logger.info("Starting Voice Assistant application")
    
    # Check system status
    if not print_status_info():
        print("\n❌ System check failed. Please fix the issues above.")
        return 1
    
    print("\n💡 Instructions:")
    print("- Speak clearly after seeing '🎤 Listening'")
    print("- Say 'quit', 'exit', or 'goodbye' to end")
    print("- Press Ctrl+C to force quit")
    print("\n" + "=" * 60)
    
    try:
        # Create and configure assistant
        assistant = VoiceAssistant(
            on_state_change=on_state_change,
            on_user_speech=on_user_speech,
            on_assistant_response=on_assistant_response
        )
        
        # Run conversation loop
        assistant.run_conversation_loop()
        
        # Show session statistics
        stats = assistant.get_stats()
        print(f"\n📊 Session Summary:")
        print(f"   Conversations: {stats['conversations']}")
        print(f"   Duration: {stats.get('duration', 0):.1f} seconds")
        print(f"   Recognition Success Rate: {stats['successful_recognitions']}/{stats['successful_recognitions'] + stats['failed_recognitions']}")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye! Session ended by user.")
        return 0
    except Exception as e:
        logger.error(f"Application error: {e}")
        print(f"\n❌ Application error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
=======
# main.py
from fastapi import FastAPI
from src.ari_handler import router as ari_router

app = FastAPI()
app.include_router(ari_router, prefix="/ari")
>>>>>>> 978c090094b55f79e8769e28b18536e68993dd09
