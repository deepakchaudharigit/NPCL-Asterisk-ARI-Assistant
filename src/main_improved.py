#!/usr/bin/env python3
"""
Improved Voice Assistant - Enhanced Traditional Mode
Better speech recognition and more reliable operation
"""

import sys
import os
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent))

import logging
import time
import speech_recognition as sr
from voice_assistant.utils.logger import setup_logger
from voice_assistant.ai.gemini_client import GeminiClient
from voice_assistant.audio.text_to_speech import TextToSpeech
from config.settings import get_settings


def print_banner():
    """Print application banner"""
    print("=" * 70)
    print("🤖 Voice Assistant - Improved Traditional Mode")
    print("🔧 Enhanced Speech Recognition • Reliable Operation")
    print("=" * 70)


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


class ImprovedVoiceAssistant:
    """Improved voice assistant with better speech recognition"""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.gemini_client = GeminiClient()
        self.tts = TextToSpeech()
        
        # Improve recognition settings
        self.recognizer.energy_threshold = 300  # Adjust based on environment
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8  # Seconds of silence before considering phrase complete
        self.recognizer.phrase_threshold = 0.3  # Minimum seconds of speaking audio before considering phrase
        
        # Statistics
        self.stats = {
            "conversations": 0,
            "successful_recognitions": 0,
            "failed_recognitions": 0,
            "start_time": time.time()
        }
        
        self.logger.info("Improved Voice Assistant initialized")
    
    def calibrate_microphone(self):
        """Calibrate microphone for ambient noise"""
        print("🎤 Calibrating microphone for ambient noise...")
        print("   Please remain quiet for 2 seconds...")
        
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
            
            print(f"✅ Microphone calibrated (energy threshold: {self.recognizer.energy_threshold})")
            return True
            
        except Exception as e:
            print(f"❌ Microphone calibration failed: {e}")
            return False
    
    def listen_for_speech(self) -> tuple:
        """Listen for speech with improved error handling"""
        try:
            print("\n[🎤 Listening - Speak now]")
            
            with self.microphone as source:
                # Listen for audio with timeout
                audio = self.recognizer.listen(
                    source, 
                    timeout=self.settings.listen_timeout,
                    phrase_time_limit=self.settings.phrase_time_limit
                )
            
            print("[🧠 Processing speech...]")
            
            # Try multiple recognition services
            text = None
            
            # Try Google Speech Recognition first
            try:
                text = self.recognizer.recognize_google(
                    audio, 
                    language=self.settings.voice_language
                )
                self.logger.info(f"Google Speech Recognition: {text}")
                
            except sr.UnknownValueError:
                # Try alternative recognition
                try:
                    text = self.recognizer.recognize_sphinx(audio)
                    self.logger.info(f"Sphinx Recognition: {text}")
                except:
                    pass
            
            except sr.RequestError as e:
                self.logger.error(f"Google Speech Recognition error: {e}")
                # Try offline recognition as fallback
                try:
                    text = self.recognizer.recognize_sphinx(audio)
                    self.logger.info(f"Sphinx Recognition (fallback): {text}")
                except:
                    pass
            
            if text:
                self.stats["successful_recognitions"] += 1
                return True, text.strip(), None
            else:
                self.stats["failed_recognitions"] += 1
                return False, "", "Could not understand speech"
                
        except sr.WaitTimeoutError:
            self.stats["failed_recognitions"] += 1
            return False, "", "Listening timeout - no speech detected"
            
        except Exception as e:
            self.stats["failed_recognitions"] += 1
            self.logger.error(f"Speech recognition error: {e}")
            return False, "", str(e)
    
    def process_conversation_turn(self) -> bool:
        """Process one conversation turn"""
        try:
            # Listen for user input
            success, user_text, error = self.listen_for_speech()
            
            if not success:
                if "timeout" in error.lower():
                    print("[⏰ Timeout - Try speaking again]")
                    return True  # Continue listening
                else:
                    print(f"[❌ {error}]")
                    print("[💡 Try speaking more clearly or closer to the microphone]")
                    return True  # Continue listening
            
            # Display user input
            print(f"👤 You: {user_text}")
            
            # Check for exit commands
            if self.is_exit_command(user_text):
                return False
            
            # Process with Gemini
            print("[🧠 Processing - Thinking...]")
            try:
                response = self.gemini_client.generate_response(user_text)
                print(f"🤖 Assistant: {response}")
                
                # Speak response
                print("[🗣️ Speaking - Response ready]")
                if not self.tts.speak(response):
                    print("[⚠️ TTS failed - response shown as text only]")
                
                self.stats["conversations"] += 1
                
            except Exception as e:
                self.logger.error(f"Error processing response: {e}")
                fallback_response = "I'm sorry, I'm having trouble processing your request right now. Could you try again?"
                print(f"🤖 Assistant: {fallback_response}")
                self.tts.speak(fallback_response)
            
            return True
            
        except KeyboardInterrupt:
            return False
        except Exception as e:
            self.logger.error(f"Error in conversation turn: {e}")
            return True  # Try to continue
    
    def is_exit_command(self, text: str) -> bool:
        """Check if text contains exit command"""
        exit_words = ['quit', 'exit', 'goodbye', 'bye', 'stop', 'end']
        return any(word in text.lower() for word in exit_words)
    
    def run_conversation_loop(self):
        """Run the main conversation loop"""
        try:
            # Calibrate microphone
            if not self.calibrate_microphone():
                print("⚠️ Continuing without calibration...")
            
            # Welcome message
            welcome = f"Hello! I'm {self.settings.assistant_name}, your voice assistant. How can I help you today?"
            print(f"🤖 Assistant: {welcome}")
            self.tts.speak(welcome)
            
            print("\n💡 Instructions:")
            print("• Speak clearly after seeing '🎤 Listening'")
            print("• Wait for the listening indicator before speaking")
            print("• Say 'quit', 'exit', or 'goodbye' to end")
            print("• Press Ctrl+C to force quit")
            print("\n" + "=" * 70)
            
            # Main conversation loop
            while True:
                if not self.process_conversation_turn():
                    break
            
            # Farewell
            farewell = "Goodbye! It was great talking with you. Have a wonderful day!"
            print(f"🤖 Assistant: {farewell}")
            self.tts.speak(farewell)
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye! Session ended by user.")
        except Exception as e:
            self.logger.error(f"Error in conversation loop: {e}")
            print(f"\n❌ Error: {e}")
        finally:
            self.show_session_stats()
    
    def show_session_stats(self):
        """Show session statistics"""
        duration = time.time() - self.stats["start_time"]
        total_attempts = self.stats["successful_recognitions"] + self.stats["failed_recognitions"]
        success_rate = (self.stats["successful_recognitions"] / total_attempts * 100) if total_attempts > 0 else 0
        
        print(f"\n📊 Session Summary:")
        print(f"   Duration: {duration:.1f} seconds")
        print(f"   Conversations: {self.stats['conversations']}")
        print(f"   Speech Recognition Success Rate: {success_rate:.1f}% ({self.stats['successful_recognitions']}/{total_attempts})")


def main():
    """Main application entry point"""
    print_banner()
    
    # Setup logging
    logger = setup_logger()
    logger.info("Starting Improved Voice Assistant")
    
    # Check system status
    if not print_status_info():
        print("\n❌ System check failed. Please fix the issues above.")
        print("\n💡 Quick fix:")
        print("1. Copy .env.example to .env")
        print("2. Add your Google API key to .env")
        print("3. Run: python setup_api_key.py")
        return 1
    
    print("\n🔧 Improvements in this version:")
    print("• Better microphone calibration")
    print("• Multiple speech recognition engines")
    print("• Improved error handling")
    print("• Fallback recognition methods")
    print("• Enhanced timeout handling")
    print("• Better user feedback")
    
    try:
        # Create and run assistant
        assistant = ImprovedVoiceAssistant()
        assistant.run_conversation_loop()
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye! Session ended by user.")
        return 0
    except Exception as e:
        logger.error(f"Application error: {e}")
        print(f"\n❌ Application error: {e}")
        print("\n💡 Troubleshooting:")
        print("1. Check your microphone permissions")
        print("2. Try adjusting microphone volume")
        print("3. Ensure you're in a quiet environment")
        print("4. Check internet connection for speech recognition")
        return 1


if __name__ == "__main__":
    sys.exit(main())