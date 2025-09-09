#!/usr/bin/env python3
"""
Voice Assistant with Gemini 2.5 Flash Live API - Clean Version
Modern voice assistant with real-time conversation and interruption support
"""

import sys
import os
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent))

import logging
from voice_assistant.core.modern_assistant import ModernVoiceAssistant, ModernAssistantState
from voice_assistant.utils.logger import setup_logger
from config.settings import get_settings


def print_banner():
    """Print application banner"""
    print("=" * 70)
    print("🤖 Voice Assistant with Gemini 2.5 Flash Live API")
    print("🎆 Real-time Conversation • Interruption Support • Dialogue Flow")
    print("=" * 70)


def print_status_info():
    """Print system status information"""
    settings = get_settings()
    
    print("✅ System Information:")
    print(f"   Assistant Name: {settings.assistant_name}")
    print(f"   AI Model: {settings.gemini_model}")
    print(f"   Live Model: {settings.gemini_live_model}")
    print(f"   Voice: {settings.gemini_voice}")
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


def on_state_change(state: ModernAssistantState):
    """Handle assistant state changes"""
    state_messages = {
        ModernAssistantState.IDLE: "💤 Ready - Waiting for input",
        ModernAssistantState.LISTENING: "🎤 Listening - Speak now",
        ModernAssistantState.PROCESSING: "🧠 Processing - Thinking...",
        ModernAssistantState.SPEAKING: "🗣️  Speaking - Response ready",
        ModernAssistantState.INTERRUPTED: "⚡ Interrupted - Processing interruption",
        ModernAssistantState.ERROR: "❌ Error - Please check logs",
        ModernAssistantState.CONNECTING: "🔄 Connecting to Gemini Live API...",
        ModernAssistantState.CONNECTED: "🎆 Connected to Live API - Real-time mode enabled!"
    }
    
    message = state_messages.get(state, f"Unknown state: {state}")
    print(f"\n[{message}]")


def on_user_speech(text: str):
    """Handle user speech events"""
    print(f"👤 You: {text}")


def on_assistant_response(text: str):
    """Handle assistant response events"""
    print(f"🤖 Assistant: {text}")


def print_features():
    """Print modern features information"""
    print("\n🎆 Modern Features:")
    print("• Real-time voice conversation with Gemini Live API")
    print("• Natural interruption support - speak anytime!")
    print("• Voice activity detection with smart turn-taking")
    print("• Ultra-low latency audio processing")
    print("• Automatic fallback to traditional mode if needed")
    print("• Professional dialogue flow management")
    print("• Clean UI with spinning indicators (no text spam!)")


def print_instructions():
    """Print usage instructions"""
    print("\n💡 Instructions:")
    print("• Speak naturally after seeing '🎤 Listening'")
    print("• You can interrupt the assistant anytime while it's speaking")
    print("• The assistant will detect when you start and stop talking")
    print("• Say 'quit', 'exit', or 'goodbye' to end the conversation")
    print("• Press Ctrl+C to force quit")
    
    print("\n🎯 Pro Tips:")
    print("• Speak clearly and at normal volume")
    print("• Wait for the listening indicator before speaking")
    print("• Try interrupting during a long response!")
    print("• The assistant learns from your conversation style")
    print("• Audio responses show as spinning indicators (no spam!)")


def main():
    """Main application entry point"""
    print_banner()
    
    # Setup logging
    logger = setup_logger()
    logger.info("Starting Modern Voice Assistant application")
    
    # Check system status
    if not print_status_info():
        print("\n❌ System check failed. Please fix the issues above.")
        print("\n💡 Quick fix:")
        print("1. Copy .env.example to .env")
        print("2. Add your Google API key to .env")
        print("3. Run: python setup_api_key.py")
        return 1
    
    print_features()
    print_instructions()
    print("\n" + "=" * 70)
    
    try:
        # Create and configure modern assistant (NO audio response callback to avoid spam)
        assistant = ModernVoiceAssistant(
            on_state_change=on_state_change,
            on_user_speech=on_user_speech,
            on_assistant_response=on_assistant_response
            # No on_audio_response callback - spinner handles this cleanly
        )
        
        # Run conversation loop
        assistant.run_conversation_loop()
        
        # Show session statistics
        stats = assistant.get_stats()
        print(f"\n📊 Session Summary:")
        print(f"   Mode: {'🎆 Live API' if stats.get('is_live_mode') else '🔄 Traditional'}")
        print(f"   Conversations: {stats['conversations']}")
        print(f"   Duration: {stats.get('duration', 0):.1f} seconds")
        print(f"   Recognition Success Rate: {stats['successful_recognitions']}/{stats['successful_recognitions'] + stats['failed_recognitions']}")
        print(f"   AI Responses: {stats['ai_responses']}")
        print(f"   Interruptions: {stats['interruptions']}")
        
        if stats.get('is_live_mode'):
            print(f"   🎆 Live API Features Used Successfully!")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye! Session ended by user.")
        return 0
    except Exception as e:
        logger.error(f"Application error: {e}")
        print(f"\n❌ Application error: {e}")
        print("\n💡 Troubleshooting:")
        print("1. Check your internet connection")
        print("2. Verify your Google API key is valid")
        print("3. Try running: pip install -r requirements.txt")
        print("4. Check the logs for more details")
        return 1


if __name__ == "__main__":
    sys.exit(main())