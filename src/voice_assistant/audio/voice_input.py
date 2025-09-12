#!/usr/bin/env python3
"""
Voice input module with speech recognition and timeout handling.
Provides clean voice input with fallback to chat mode.
"""

import speech_recognition as sr
import time
from typing import Optional, Tuple


class VoiceInputHandler:
    """Handles voice input with timeout and fallback options"""
    
    def __init__(self, language_code: str = "hi-IN", timeout: int = 10):
        self.language_code = language_code
        self.timeout = timeout
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self.is_initialized = False
        
        # Language mapping for speech recognition
        self.sr_language_map = {
            "en-IN": "en-IN",
            "hi-IN": "hi-IN", 
            "bn-IN": "bn-IN",
            "te-IN": "te-IN",
            "mr-IN": "mr-IN",
            "ta-IN": "ta-IN",
            "gu-IN": "gu-IN",
            "ur-IN": "ur-IN",
            "kn-IN": "kn-IN",
            "or-IN": "or-IN",
            "ml-IN": "ml-IN",
            "el-GR": "el-GR"
        }
    
    def initialize_microphone(self) -> bool:
        """Initialize microphone and adjust for ambient noise"""
        try:
            self.microphone = sr.Microphone()
            
            # Adjust for ambient noise
            print("🎤 Initializing microphone...")
            with self.microphone as source:
                print("📊 Adjusting for ambient noise... (please be quiet)")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            
            # Configure recognizer settings
            self.recognizer.energy_threshold = 300
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.pause_threshold = 0.8
            self.recognizer.phrase_time_limit = self.timeout
            
            self.is_initialized = True
            print("✅ Microphone ready!")
            return True
            
        except Exception as e:
            print(f"❌ Microphone initialization failed: {e}")
            return False
    
    def listen_for_speech(self) -> Tuple[Optional[str], str]:
        """
        Listen for speech with timeout
        Returns: (recognized_text, status)
        Status can be: 'success', 'timeout', 'no_speech', 'error'
        """
        if not self.is_initialized:
            if not self.initialize_microphone():
                return None, 'error'
        
        try:
            print(f"🎤 Listening... (speak within {self.timeout} seconds)")
            print("💡 Say something or wait for timeout to switch to chat mode")
            
            with self.microphone as source:
                # Listen with timeout
                try:
                    audio = self.recognizer.listen(
                        source, 
                        timeout=self.timeout,
                        phrase_time_limit=self.timeout
                    )
                except sr.WaitTimeoutError:
                    return None, 'timeout'
            
            # Recognize speech
            print("🔄 Processing speech...")
            
            # Get the appropriate language code for speech recognition
            sr_language = self.sr_language_map.get(self.language_code, "en-IN")
            
            try:
                # Try Google Speech Recognition first
                text = self.recognizer.recognize_google(audio, language=sr_language)
                return text, 'success'
                
            except sr.UnknownValueError:
                return None, 'no_speech'
            except sr.RequestError as e:
                print(f"⚠️  Google Speech Recognition error: {e}")
                
                # Fallback to offline recognition if available
                try:
                    text = self.recognizer.recognize_sphinx(audio)
                    return text, 'success'
                except:
                    return None, 'error'
                    
        except Exception as e:
            print(f"❌ Speech recognition error: {e}")
            return None, 'error'
    
    def get_voice_input_with_fallback(self, language_config: dict) -> Tuple[Optional[str], str]:
        """
        Get voice input with automatic fallback to chat mode
        Returns: (text, input_mode)
        input_mode can be: 'voice', 'chat', 'error'
        """
        lang_code = language_config["code"]
        lang_name = language_config["native"]
        
        # Messages in different languages
        messages = {
            "en-IN": {
                "listening": "🎤 Voice Mode Active - Speak now!",
                "timeout": "⏰ No voice detected. Switching to chat mode...",
                "no_speech": "🔇 Couldn't understand. Switching to chat mode...",
                "error": "❌ Voice recognition error. Switching to chat mode...",
                "chat_prompt": "💬 Chat Mode - Type your message: ",
                "success": "✅ Voice recognized!"
            },
            "hi-IN": {
                "listening": "🎤 वॉयस मोड सक्रिय - अब बोलें!",
                "timeout": "⏰ कोई आवाज़ नहीं मिली। चैट मोड में स्विच कर रहे हैं...",
                "no_speech": "🔇 समझ नहीं आया। चैट मोड में स्विच कर रहे हैं...",
                "error": "❌ वॉयस पहचान त्रुटि। चैट मोड में स्विच कर रहे हैं...",
                "chat_prompt": "💬 चैट मोड - अपना संदेश टाइप करें: ",
                "success": "✅ आवाज़ पहचान गई!"
            },
            "bn-IN": {
                "listening": "🎤 ভয়েস মোড সক্রিয় - এখন বলুন!",
                "timeout": "⏰ কোন আওয়াজ পাওয়া যায়নি। চ্যাট মোডে স্যুইচ করছি...",
                "no_speech": "🔇 বুঝতে পারিনি। চ্যাট মোডে স্যুইচ করছি...",
                "error": "❌ ভয়েস রিকগনিশন ত্রুটি। চ্যাট মোডে স্যুইচ করছি...",
                "chat_prompt": "💬 চ্যাট মোড - আপনার বার্তা টাইপ করুন: ",
                "success": "✅ আওয়াজ চিনতে পেরেছি!"
            }
        }
        
        msg = messages.get(lang_code, messages["en-IN"])
        
        print(msg["listening"])
        
        # Try to get voice input
        text, status = self.listen_for_speech()
        
        if status == 'success' and text:
            print(msg["success"])
            print(f"🗣️  You said: {text}")
            return text, 'voice'
        
        # Handle different failure cases
        if status == 'timeout':
            print(msg["timeout"])
        elif status == 'no_speech':
            print(msg["no_speech"])
        elif status == 'error':
            print(msg["error"])
        
        # Fallback to chat mode
        print()
        try:
            text = input(msg["chat_prompt"]).strip()
            if text:
                return text, 'chat'
            else:
                return None, 'error'
        except KeyboardInterrupt:
            return None, 'error'
    
    def cleanup(self):
        """Clean up resources"""
        self.microphone = None
        self.is_initialized = False


def test_voice_input():
    """Test the voice input functionality"""
    print("🧪 Testing Voice Input")
    print("=" * 30)
    
    # Test with Hindi
    handler = VoiceInputHandler("hi-IN", timeout=5)
    
    language_config = {
        "code": "hi-IN",
        "name": "Hindi", 
        "native": "हिन्दी"
    }
    
    text, mode = handler.get_voice_input_with_fallback(language_config)
    
    if text:
        print(f"✅ Got input: {text} (mode: {mode})")
    else:
        print("❌ No input received")
    
    handler.cleanup()


if __name__ == "__main__":
    test_voice_input()