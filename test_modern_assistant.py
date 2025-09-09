#!/usr/bin/env python3
"""
Test script for Modern Voice Assistant
Quick test to verify the modern assistant with Gemini Live API works
"""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test if all required modules can be imported"""
    print("🧪 Testing Modern Voice Assistant Imports...")
    
    try:
        from voice_assistant.core.modern_assistant import ModernVoiceAssistant, ModernAssistantState
        print("✅ ModernVoiceAssistant imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import ModernVoiceAssistant: {e}")
        return False
    
    try:
        from voice_assistant.ai.gemini_live_client import GeminiLiveClient, GeminiLiveConfig
        print("✅ GeminiLiveClient imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import GeminiLiveClient: {e}")
        return False
    
    try:
        from voice_assistant.audio.realtime_audio_processor import RealTimeAudioProcessor, AudioConfig
        print("✅ RealTimeAudioProcessor imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import RealTimeAudioProcessor: {e}")
        return False
    
    try:
        from config.settings import get_settings
        settings = get_settings()
        print(f"✅ Settings loaded successfully - Assistant: {settings.assistant_name}")
    except Exception as e:
        print(f"❌ Failed to load settings: {e}")
        return False
    
    return True

def test_dependencies():
    """Test if all required dependencies are available"""
    print("\n🧪 Testing Dependencies...")
    
    dependencies = [
        ("websockets", "WebSocket support for Live API"),
        ("numpy", "Audio processing"),
        ("google.generativeai", "Gemini API"),
        ("speech_recognition", "Speech recognition"),
        ("gtts", "Text-to-speech"),
        ("pydantic", "Configuration management"),
        ("fastapi", "Web framework"),
    ]
    
    all_good = True
    for module, description in dependencies:
        try:
            __import__(module)
            print(f"✅ {module} - {description}")
        except ImportError:
            print(f"❌ {module} - {description} (MISSING)")
            all_good = False
    
    return all_good

def test_configuration():
    """Test configuration"""
    print("\n🧪 Testing Configuration...")
    
    try:
        from config.settings import get_settings
        settings = get_settings()
        
        # Check API key
        if settings.google_api_key and settings.google_api_key != "your-google-api-key-here":
            print("✅ Google API Key configured")
        else:
            print("❌ Google API Key not configured")
            return False
        
        # Check Live API settings
        print(f"✅ Live Model: {settings.gemini_live_model}")
        print(f"✅ Voice: {settings.gemini_voice}")
        print(f"✅ Audio Sample Rate: {settings.audio_sample_rate}Hz")
        print(f"✅ Audio Chunk Size: {settings.audio_chunk_size}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

def test_basic_functionality():
    """Test basic functionality without actually running the assistant"""
    print("\n🧪 Testing Basic Functionality...")
    
    try:
        from voice_assistant.core.modern_assistant import ModernVoiceAssistant, ModernAssistantState
        
        # Create assistant instance
        assistant = ModernVoiceAssistant()
        print("✅ Assistant instance created")
        
        # Test state management
        initial_state = assistant.state
        print(f"✅ Initial state: {initial_state.value}")
        
        # Test stats
        stats = assistant.get_stats()
        print(f"✅ Stats available: {len(stats)} metrics")
        
        # Test Live API status (without connecting)
        status = assistant.get_live_api_status()
        print(f"✅ Live API status check: {status.get('mode', 'unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Modern Voice Assistant Test Suite")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_imports),
        ("Dependencies Test", test_dependencies),
        ("Configuration Test", test_configuration),
        ("Basic Functionality Test", test_basic_functionality),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name}...")
        if test_func():
            print(f"✅ {test_name} PASSED")
            passed += 1
        else:
            print(f"❌ {test_name} FAILED")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your Modern Voice Assistant is ready!")
        print("\n🚀 To run the assistant:")
        print("python src/main.py")
        return 0
    else:
        print("⚠️  Some tests failed. Please fix the issues above.")
        print("\n💡 Common fixes:")
        print("1. Install missing dependencies: pip install -r requirements.txt")
        print("2. Configure API key: python setup_api_key.py")
        print("3. Check .env file exists and is properly configured")
        return 1

if __name__ == "__main__":
    sys.exit(main())