#!/usr/bin/env python3
"""
Simple voice input handler that works without complex dependencies.
Provides 10-second timeout voice input with fallback to chat.
"""

import time
from typing import Optional, Tuple


class SimpleVoiceInput:
    """Simple voice input handler with timeout"""
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.recognizer = None
        self.microphone = None
        self.is_available = False
        
        # Try to initialize speech recognition
        self._initialize_speech_recognition()
    
    def _initialize_speech_recognition(self):
        """Try to initialize speech recognition"""
        try:
            import speech_recognition as sr
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
            
            # Quick microphone test
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            
            # Configure recognizer for better Hindi recognition
            self.recognizer.energy_threshold = 200  # Lower threshold for better sensitivity
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.pause_threshold = 1.0  # Longer pause for Hindi speech
            self.recognizer.operation_timeout = None  # No operation timeout
            
            self.is_available = True
            print("✅ Voice input initialized")
            
        except ImportError:
            print("⚠️  Speech recognition not available")
            print("💡 Install with: pip install SpeechRecognition pyaudio")
            self.is_available = False
        except Exception as e:
            print(f"⚠️  Voice setup failed: {e}")
            self.is_available = False
    
    def listen_with_timeout(self, language_code: str = "hi-IN") -> Tuple[Optional[str], str]:
        """
        Listen for speech with timeout
        Returns: (text, status)
        Status: 'success', 'timeout', 'no_speech', 'error', 'unavailable'
        """
        if not self.is_available:
            return None, 'unavailable'
        
        try:
            import speech_recognition as sr
            
            print(f"🎤 Listening for {self.timeout} seconds...")
            print("💡 Speak now or wait for timeout to switch to chat mode")
            
            # Start listening with timeout
            start_time = time.time()
            
            with self.microphone as source:
                try:
                    # Listen with timeout
                    audio = self.recognizer.listen(
                        source, 
                        timeout=self.timeout,
                        phrase_time_limit=self.timeout
                    )
                    
                    elapsed = time.time() - start_time
                    print(f"🔄 Processing speech (listened for {elapsed:.1f}s)...")
                    
                except sr.WaitTimeoutError:
                    elapsed = time.time() - start_time
                    print(f"⏰ Timeout after {elapsed:.1f} seconds")
                    return None, 'timeout'
            
            # Try to recognize speech with multiple attempts
            try:
                # First try Google Speech Recognition with Hindi
                text = self.recognizer.recognize_google(audio, language=language_code)
                print(f"✅ Recognized: {text}")
                return text, 'success'
                
            except sr.UnknownValueError:
                # Try with English if Hindi fails
                try:
                    text = self.recognizer.recognize_google(audio, language="en-IN")
                    print(f"✅ Recognized (English): {text}")
                    return text, 'success'
                except sr.UnknownValueError:
                    print("🔇 Could not understand audio in Hindi or English")
                    return None, 'no_speech'
                
            except sr.RequestError as e:
                print(f"⚠️  Speech recognition error: {e}")
                return None, 'error'
                
        except Exception as e:
            print(f"❌ Voice input error: {e}")
            return None, 'error'
    
    def get_input_with_fallback(self, language_config: dict) -> Tuple[Optional[str], str]:
        """
        Get voice input with automatic fallback to chat
        Returns: (text, mode) where mode is 'voice' or 'chat'
        """
        lang_code = language_config["code"]
        lang_name = language_config["native"]
        
        # Messages in different languages
        messages = {
            "en-IN": {
                "timeout": "⏰ No voice detected. Switching to chat mode...",
                "no_speech": "🔇 Couldn't understand. Switching to chat mode...",
                "error": "❌ Voice error. Switching to chat mode...",
                "unavailable": "⚠️  Voice input unavailable. Using chat mode...",
                "chat_prompt": "💬 Type your message: "
            },
            "hi-IN": {
                "timeout": "⏰ कोई आवाज़ नहीं मिली। चैट मोड में स्विच कर रहे हैं...",
                "no_speech": "🔇 समझ नहीं आया। चैट मोड में स्विच कर रहे हैं...",
                "error": "❌ वॉयस त्रुटि। चैट मोड में स्विच कर रहे हैं...",
                "unavailable": "⚠️  वॉयस इनपुट उपलब्ध नहीं। चैट मोड का उपयोग कर रहे हैं...",
                "chat_prompt": "💬 अपना संदेश टाइप करें: "
            }
        }
        
        msg = messages.get(lang_code, messages["en-IN"])
        
        # Try voice input first
        if self.is_available:
            text, status = self.listen_with_timeout(lang_code)
            
            if status == 'success' and text:
                return text, 'voice'
            
            # Handle different failure cases
            if status == 'timeout':
                print(msg["timeout"])
            elif status == 'no_speech':
                print(msg["no_speech"])
            elif status == 'error':
                print(msg["error"])
        else:
            print(msg["unavailable"])
        
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


def test_simple_voice():
    """Test the simple voice input"""
    print("🧪 Testing Simple Voice Input")
    print("=" * 40)
    
    voice_input = SimpleVoiceInput(timeout=5)  # 5 seconds for testing
    
    language_config = {
        "code": "hi-IN",
        "name": "Hindi",
        "native": "हिन्दी"
    }
    
    text, mode = voice_input.get_input_with_fallback(language_config)
    
    if text:
        print(f"✅ Got input: '{text}' (mode: {mode})")
    else:
        print("❌ No input received")


if __name__ == "__main__":
    test_simple_voice()