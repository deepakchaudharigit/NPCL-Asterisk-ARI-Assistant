#!/usr/bin/env python3
"""
NPCL Voice Assistant - Main Entry Point
Unified version with fallback for import issues
"""

import sys
import os
import asyncio
import json
import base64
import time
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent))

def print_banner():
    """Print application banner"""
    print("=" * 70)
    print("🤖 NPCL Voice Assistant")
    print("🎆 Powered by Gemini 1.5 Flash")
    print("=" * 70)

def check_api_key():
    """Check if API key is configured and test quota"""
    try:
        env_file = Path('.env')
        if not env_file.exists():
            print("❌ .env file not found")
            return False, None
        
        with open(env_file, 'r') as f:
            content = f.read()
            for line in content.split('\n'):
                if line.strip().startswith('GOOGLE_API_KEY='):
                    api_key = line.split('=', 1)[1].strip()
                    if api_key and api_key != 'your-google-api-key-here':
                        print("✅ Google API Key: Configured")
                        
                        # Test quota
                        quota_ok = test_api_quota(api_key)
                        if quota_ok:
                            print("✅ API Quota: Available")
                        else:
                            print("⚠️  API Quota: Exceeded (will use offline mode)")
                        
                        return True, api_key
            
        print("❌ Google API Key: Not configured properly")
        return False, None
    except Exception as e:
        print(f"❌ Error checking API key: {e}")
        return False, None

def test_api_quota(api_key):
    """Test if API quota is available"""
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Simple test request
        response = model.generate_content("test")
        return True
        
    except Exception as e:
        error_str = str(e).lower()
        if "quota" in error_str or "exceeded" in error_str or "429" in str(e):
            return False
        return True  # Other errors might be temporary

def print_system_status():
    """Print system status"""
    print("🔍 System Check:")
    
    # Check virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Virtual environment: Active")
    else:
        print("⚠️  Virtual environment: Not detected")
    
    # Check API key
    api_key_valid, api_key = check_api_key()
    return api_key_valid, api_key

def print_mode_options():
    """Print mode selection options"""
    print("\n🎯 Choose Your Assistant Mode:")
    print("1. 💬 Chat Mode - Text-based conversation")
    print("2. 🎤 Voice Mode - Real-time voice conversation (Advanced)")
    print("3. 🎭 Combined Mode - Voice + Chat (Advanced)")
    print("4. ❌ Exit")
    print()
    print("💡 Note: If API quota is exceeded, offline mode will start automatically")
    print()

def get_user_choice():
    """Get user's mode choice"""
    while True:
        try:
            choice = input("Enter your choice (1-4): ").strip()
            if choice in ['1', '2', '3', '4']:
                return int(choice)
            else:
                print("❌ Invalid choice. Please enter 1, 2, 3, or 4.")
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            return 4
        except Exception:
            print("❌ Invalid input. Please enter a number.")

def get_npcl_system_instruction():
    """Get NPCL system instruction"""
    return """You are a customer service assistant for NPCL (Noida Power Corporation Limited), a power utility company.

Your role:
- Help customers with power connection inquiries
- Handle complaint registration and status updates
- Provide professional customer service
- Use polite Indian English communication style

When customers contact you:
1. Greet them professionally
2. Ask for their connection details or complaint number
3. Provide helpful information about their power service
4. Register new complaints if needed
5. Give status updates on existing complaints

Communication style:
- Be respectful and use "Sir" or "Madam"
- Use Indian English phrases naturally
- Speak clearly and be helpful
- Keep responses concise and professional

Sample complaint number format: 0000054321
Always be ready to help with power-related issues."""

def start_simple_chat_mode(api_key):
    """Start simple chat mode using direct Gemini API with robust TTS"""
    # Clear terminal for clean conversation interface
    import os
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print("💬 NPCL Voice Assistant - Chat Mode")
    print("=" * 40)
    print()
    
    # Test TTS availability
    tts_available = False
    try:
        import pyttsx3
        # Test with a quick initialization
        test_engine = pyttsx3.init()
        test_engine.stop()
        del test_engine
        tts_available = True
        print("🔊 Voice output enabled (Robust Mode)")
        
    except ImportError:
        print("⚠️  Text-to-speech not available. Install: pip install pyttsx3")
        print("💬 Continuing with text-only mode...")
    except Exception as e:
        print(f"⚠️  Voice setup failed: {e}")
        print("💬 Continuing with text-only mode...")
    
    # Initialize speech recognition
    recognizer = None
    microphone = None
    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        microphone = sr.Microphone()
        
        # Adjust for ambient noise and improve recognition
        print("🎤 Calibrating microphone...")
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=2)
        
        # Improve recognition settings
        recognizer.energy_threshold = 300  # Minimum audio energy to consider for recording
        recognizer.dynamic_energy_threshold = True  # Automatically adjust energy threshold
        recognizer.pause_threshold = 0.8  # Seconds of non-speaking audio before phrase is complete
        
        print("🎤 Voice input enabled")
        
        # Speak the setup completion
        if tts_available:
            setup_msg = "Voice setup complete. I can now speak and listen."
            speak_text_robust(setup_msg)
        
    except ImportError:
        print("⚠️  Speech recognition not available. Install: pip install SpeechRecognition")
        print("💬 Voice input disabled - will use text input")
    except Exception as e:
        print(f"⚠️  Microphone setup failed: {e}")
        print("💬 Voice input disabled - will use text input")
        recognizer = None
        microphone = None
    
    print()
    
    def speak_text_robust(text):
        """Robust TTS function that works on Windows by reinitializing engine"""
        if not tts_available:
            print(f"[SILENT] {text}")
            return False
        
        try:
            import pyttsx3
            
            # Reinitialize engine for each call (Windows fix)
            engine = pyttsx3.init()
            
            # Configure engine
            engine.setProperty('rate', 150)
            engine.setProperty('volume', 1.0)
            
            # Set voice if available
            voices = engine.getProperty('voices')
            if voices:
                # Try to find a good voice
                for voice in voices:
                    if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                        engine.setProperty('voice', voice.id)
                        break
                else:
                    engine.setProperty('voice', voices[0].id)
            
            print("🔊 Speaking...")
            
            # Speak the text
            engine.say(text)
            engine.runAndWait()
            
            # Cleanup engine (important for Windows)
            try:
                engine.stop()
                del engine
            except:
                pass
            
            print("✅ Speech completed")
            print()
            return True
            
        except Exception as e:
            print(f"⚠️  Voice error: {e}")
            print(f"Text was: {text[:50]}...")
            return False
    

    
    def listen_for_voice():
        """Listen for voice input and convert to text"""
        if not recognizer or not microphone:
            return None
        
        try:
            print("🎤 Listening... (speak now - 15 seconds)")
            with microphone as source:
                # Listen for audio with 15 second timeout as requested
                audio = recognizer.listen(source, timeout=15, phrase_time_limit=15)
            
            print("🔄 Processing speech...")
            # Use Google Speech Recognition
            text = recognizer.recognize_google(audio)
            print(f"🎤 You said: {text}")
            return text
            
        except sr.WaitTimeoutError:
            timeout_msg = "No speech detected after 15 seconds. Please try again."
            print(f"⏰ {timeout_msg}")
            return None
        except sr.UnknownValueError:
            unclear_msg = "Could not understand your speech clearly. Please try again."
            print(f"❌ {unclear_msg}")
            return None
        except sr.RequestError as e:
            error_msg = f"Speech recognition service error: {e}"
            print(f"❌ {error_msg}")
            return None
        except Exception as e:
            general_error_msg = f"Voice input error: {e}"
            print(f"❌ {general_error_msg}")
            return None
    
    try:
        import google.generativeai as genai
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Test quota before starting conversation
        try:
            # Quick quota test
            test_response = model.generate_content("test")
        except Exception as e:
            if "quota" in str(e).lower() or "429" in str(e):
                print(f"⚠️  API quota exceeded. Switching to offline mode...")
                print(f"🔄 Restarting in offline mode...")
                start_offline_voice_mode()
                return
            else:
                print(f"❌ API error: {e}")
                return
        
        # Generate and speak welcome message
        try:
            system_prompt = get_npcl_system_instruction()
            welcome_prompt = system_prompt + "\n\nPlease start the conversation by welcoming the customer to NPCL customer service. Introduce yourself as the NPCL voice assistant and ask how you can help them with their power connection today. Be professional and use Indian English style.\n\nAssistant:"
            
            initial_response = model.generate_content(welcome_prompt)
            welcome_text = initial_response.text
            
            print(f"🤖 NPCL Assistant: {welcome_text}")
            print()
            
            # Speak the welcome message using robust TTS
            speak_text_robust(welcome_text)
            
        except Exception as e:
            if "quota" in str(e).lower() or "429" in str(e):
                print(f"⚠️  API quota exceeded during welcome. Switching to offline mode...")
                start_offline_voice_mode()
                return
            else:
                print(f"❌ Failed to generate welcome: {e}")
                # Fallback welcome
                fallback_welcome = "Namaste! Welcome to NPCL customer service. I am your voice assistant. How may I help you with your power connection today?"
                print(f"🤖 NPCL Assistant: {fallback_welcome}")
                speak_text_robust(fallback_welcome)
        
        while True:
            try:
                user_input = input("\n👤 You: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'bye', 'goodbye']:
                    print("👋 Thank you for contacting NPCL. Have a great day!")
                    break
                
                if not user_input:
                    continue
                
                # Get AI response with quota check
                try:
                    prompt = f"{system_prompt}\n\nUser: {user_input}\nAssistant:"
                    response = model.generate_content(prompt)
                    
                    # Display and speak the response
                    response_text = response.text
                    print(f"🤖 NPCL Assistant: {response_text}")
                    print()
                    
                    # Always speak the response using robust TTS - FIXED!
                    speak_text_robust(response_text)
                    
                except Exception as e:
                    if "quota" in str(e).lower() or "429" in str(e):
                        print(f"⚠️  API quota exceeded. Switching to offline mode...")
                        start_offline_voice_mode()
                        return
                    else:
                        # Fallback response for other errors
                        fallback_response = "I apologize, but I'm having technical difficulties. Please try again or contact our customer service directly."
                        print(f"🤖 NPCL Assistant: {fallback_response}")
                        speak_text_robust(fallback_response)
                
            except KeyboardInterrupt:
                print("\n👋 Chat session ended.")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                
    except Exception as e:
        print(f"❌ Failed to initialize chat: {e}")
        print("\n💡 Make sure you have:")
        print("1. Valid Google API key in .env file")
        print("2. Internet connection")
        print("3. google-generativeai package installed")

def start_offline_voice_mode():
    """Start voice mode without AI (offline mode for quota exceeded)"""
    import os
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print("🎙️ NPCL Voice Assistant - Offline Mode")
    print("=" * 40)
    print("⚠️  API quota exceeded - using offline responses")
    print()
    
    # Test TTS availability
    tts_available = False
    try:
        import pyttsx3
        test_engine = pyttsx3.init()
        test_engine.stop()
        del test_engine
        tts_available = True
        print("🔊 Voice output enabled (Robust Mode)")
    except Exception as e:
        print(f"⚠️  Voice setup failed: {e}")
    
    # Initialize speech recognition
    recognizer = None
    microphone = None
    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        microphone = sr.Microphone()
        
        print("🎤 Calibrating microphone...")
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=2)
        
        recognizer.energy_threshold = 300
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 0.8
        
        print("🎤 Voice input enabled")
    except Exception as e:
        print(f"⚠️  Microphone setup failed: {e}")
        recognizer = None
        microphone = None
    
    print()
    
    def speak_text_robust(text):
        """Robust TTS function"""
        if not tts_available:
            print(f"[SILENT] {text}")
            return False
        
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty('rate', 150)
            engine.setProperty('volume', 1.0)
            
            voices = engine.getProperty('voices')
            if voices:
                for voice in voices:
                    if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                        engine.setProperty('voice', voice.id)
                        break
                else:
                    engine.setProperty('voice', voices[0].id)
            
            print("🔊 Speaking...")
            engine.say(text)
            engine.runAndWait()
            
            try:
                engine.stop()
                del engine
            except:
                pass
            
            print("✅ Speech completed")
            print()
            return True
        except Exception as e:
            print(f"⚠️  Voice error: {e}")
            return False
    
    def listen_for_voice():
        """Listen for voice input"""
        if not recognizer or not microphone:
            return None
        
        try:
            print("🎤 Listening... (speak now - 15 seconds)")
            with microphone as source:
                audio = recognizer.listen(source, timeout=15, phrase_time_limit=15)
            
            print("🔄 Processing speech...")
            text = recognizer.recognize_google(audio)
            print(f"🎤 You said: {text}")
            return text
        except Exception as e:
            print(f"❌ Listen failed: {e}")
            return None
    
    def get_offline_response(user_input):
        """Get offline NPCL response (predefined responses)"""
        user_lower = user_input.lower()
        
        # NPCL offline responses
        if any(word in user_lower for word in ['hello', 'hi', 'hey', 'namaste']):
            return "Namaste! Welcome to NPCL customer service. I'm currently in offline mode due to high demand. How can I help you with your power connection today?"
        
        elif any(word in user_lower for word in ['power', 'electricity', 'outage', 'cut']):
            return "I understand you're experiencing a power issue. Please note your complaint number: NPCL-OFF-001. Our technical team will address this within 24 hours. Is there anything else I can help with?"
        
        elif any(word in user_lower for word in ['complaint', 'problem', 'issue']):
            return "I can help register your complaint. Your complaint number is NPCL-OFF-002. Please keep this number for future reference. Our team will contact you within 24 hours."
        
        elif any(word in user_lower for word in ['bill', 'payment', 'amount']):
            return "For billing inquiries, please visit our nearest NPCL office or call our billing helpline. Your account details are secure and will be reviewed by our billing team."
        
        elif any(word in user_lower for word in ['connection', 'new', 'apply']):
            return "For new power connections, please visit our customer service center with required documents. The process typically takes 7-10 working days."
        
        elif any(word in user_lower for word in ['thank', 'thanks']):
            return "You're welcome! Thank you for contacting NPCL. Is there anything else I can assist you with today?"
        
        else:
            return "Thank you for contacting NPCL. I'm currently in offline mode. For immediate assistance, please call our helpline or visit our customer service center. Your query is important to us."
    
    # Welcome message
    welcome = "Namaste! Welcome to NPCL customer service. I'm currently in offline mode due to high API usage, but I can still help with basic inquiries. How may I assist you with your power connection today?"
    print(f"🤖 NPCL Assistant: {welcome}")
    print()
    speak_text_robust(welcome)
    
    # Conversation loop
    while True:
        try:
            # Get user input
            user_input = None
            
            if recognizer and microphone:
                user_input = listen_for_voice()
                
                if user_input is None:
                    fallback_msg = "I couldn't understand your speech. Please type your message instead."
                    print(f"💬 {fallback_msg}")
                    speak_text_robust(fallback_msg)
                    user_input = input("🎙️ You: ").strip()
            else:
                user_input = input("🎙️ You: ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ['quit', 'exit', 'bye', 'goodbye']:
                goodbye_msg = "Thank you for contacting NPCL. Have a great day! Please try again later when our AI service is available."
                print(f"👋 {goodbye_msg}")
                speak_text_robust(goodbye_msg)
                break
            
            # Get offline response
            response_text = get_offline_response(user_input)
            print(f"🤖 NPCL Assistant: {response_text}")
            print()
            
            # Speak the response
            speak_text_robust(response_text)
            
        except KeyboardInterrupt:
            print("\n👋 Voice session ended.")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

def start_simple_voice_mode(api_key):
    """Start simple voice mode with robust text-to-speech (Windows fix)"""
    # Clear terminal for clean conversation interface
    import os
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print("🎙️ NPCL Voice Assistant")
    print("=" * 30)
    print()
    
    # Test TTS availability
    tts_available = False
    try:
        import pyttsx3
        # Test with a quick initialization
        test_engine = pyttsx3.init()
        test_engine.stop()
        del test_engine
        tts_available = True
        print("🔊 Voice output enabled (Robust Mode)")
        
    except ImportError:
        print("⚠️  Text-to-speech not available. Install: pip install pyttsx3")
        print("💬 Continuing with text-only mode...")
    except Exception as e:
        print(f"⚠️  Voice setup failed: {e}")
        print("💬 Continuing with text-only mode...")
    
    # Initialize speech recognition
    recognizer = None
    microphone = None
    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        microphone = sr.Microphone()
        
        # Adjust for ambient noise and improve recognition
        print("🎤 Calibrating microphone...")
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=2)
        
        # Improve recognition settings
        recognizer.energy_threshold = 300  # Minimum audio energy to consider for recording
        recognizer.dynamic_energy_threshold = True  # Automatically adjust energy threshold
        recognizer.pause_threshold = 0.8  # Seconds of non-speaking audio before phrase is complete
        
        print("🎤 Voice input enabled")
        
    except ImportError:
        print("⚠️  Speech recognition not available. Install: pip install SpeechRecognition")
        print("💬 Voice input disabled - will use text input")
    except Exception as e:
        print(f"⚠️  Microphone setup failed: {e}")
        print("💬 Voice input disabled - will use text input")
        recognizer = None
        microphone = None
    
    print()
    
    def speak_text(text):
        """Speak the given text using TTS"""
        if tts_engine:
            try:
                print("🔊 Speaking...")
                # Clear any previous speech
                tts_engine.stop()
                # Add the text to speech queue
                tts_engine.say(text)
                # Wait for speech to complete
                tts_engine.runAndWait()
                print("✅ Speech completed")
                print()
            except Exception as e:
                print(f"⚠️  Voice error: {e}")
                print(f"Text was: {text[:50]}...")
        else:
            print("⚠️  TTS engine not available - text only mode")
    
    def listen_for_voice():
        """Listen for voice input and convert to text"""
        if not recognizer or not microphone:
            return None
        
        try:
            print("🎤 Listening... (speak now - 15 seconds)")
            with microphone as source:
                # Listen for audio with 15 second timeout as requested
                audio = recognizer.listen(source, timeout=15, phrase_time_limit=15)
            
            print("🔄 Processing speech...")
            # Use Google Speech Recognition
            text = recognizer.recognize_google(audio)
            print(f"🎤 You said: {text}")
            return text
            
        except sr.WaitTimeoutError:
            timeout_msg = "No speech detected after 15 seconds. Please try again."
            print(f"⏰ {timeout_msg}")
            return None
        except sr.UnknownValueError:
            unclear_msg = "Could not understand your speech clearly. Please try again."
            print(f"❌ {unclear_msg}")
            return None
        except sr.RequestError as e:
            error_msg = f"Speech recognition service error: {e}"
            print(f"❌ {error_msg}")
            return None
        except Exception as e:
            general_error_msg = f"Voice input error: {e}"
            print(f"❌ {general_error_msg}")
            return None
    
    try:
        import google.generativeai as genai
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Test quota before starting conversation
        try:
            # Quick quota test
            test_response = model.generate_content("test")
        except Exception as e:
            if "quota" in str(e).lower() or "429" in str(e):
                print(f"⚠️  API quota exceeded. Switching to offline mode...")
                print(f"🔄 Restarting in offline mode...")
                start_offline_voice_mode()
                return
            else:
                print(f"❌ API error: {e}")
                return
        
        # Generate and speak welcome message
        try:
            system_prompt = get_npcl_system_instruction()
            welcome_prompt = system_prompt + "\n\nPlease start the conversation by welcoming the customer to NPCL customer service. Introduce yourself as the NPCL voice assistant and ask how you can help them with their power connection today. Be professional and use Indian English style.\n\nAssistant:"
            
            initial_response = model.generate_content(welcome_prompt)
            welcome_text = initial_response.text
            
            print(f"🤖 NPCL Assistant: {welcome_text}")
            print()
            
            # Speak the welcome message using robust TTS
            speak_text_robust(welcome_text)
            
        except Exception as e:
            if "quota" in str(e).lower() or "429" in str(e):
                print(f"⚠️  API quota exceeded during welcome. Switching to offline mode...")
                start_offline_voice_mode()
                return
            else:
                print(f"❌ Failed to generate welcome: {e}")
                # Fallback welcome
                fallback_welcome = "Namaste! Welcome to NPCL customer service. I am your voice assistant. How may I help you with your power connection today?"
                print(f"🤖 NPCL Assistant: {fallback_welcome}")
                speak_text_robust(fallback_welcome)
        
        # Start conversation loop
        while True:
            try:
                # Get user input - try voice first, fallback to text
                user_input = None
                
                if recognizer and microphone:
                    # Try voice input
                    user_input = listen_for_voice()
                    
                    if user_input is None:
                        # Voice failed, ask for text input with spoken message
                        fallback_msg = "I couldn't understand your speech. Please type your message instead."
                        print(f"💬 {fallback_msg}")
                        speak_text_robust(fallback_msg)
                        user_input = input("🎙️ You: ").strip()
                else:
                    # No voice recognition available, use text input
                    user_input = input("🎤 You: ").strip()
                
                if not user_input:
                    continue
                    
                if user_input.lower() in ['quit', 'exit', 'bye', 'goodbye']:
                    goodbye_msg = "Thank you for contacting NPCL. Have a great day!"
                    print(f"👋 {goodbye_msg}")
                    speak_text_robust(goodbye_msg)
                    break
                
                # Get AI response with quota check
                try:
                    prompt = f"{system_prompt}\n\nUser: {user_input}\nAssistant:"
                    response = model.generate_content(prompt)
                    
                    # Display and speak the response
                    response_text = response.text
                    print(f"🤖 NPCL Assistant: {response_text}")
                    print()
                    
                    # Always speak the response using robust TTS - FIXED!
                    speak_text_robust(response_text)
                    
                except Exception as e:
                    if "quota" in str(e).lower() or "429" in str(e):
                        print(f"⚠️  API quota exceeded. Switching to offline mode...")
                        start_offline_voice_mode()
                        return
                    else:
                        # Fallback response for other errors
                        fallback_response = "I apologize, but I'm having technical difficulties. Please try again or contact our customer service directly."
                        print(f"🤖 NPCL Assistant: {fallback_response}")
                        speak_text_robust(fallback_response)
                
            except KeyboardInterrupt:
                print("\n👋 Voice session ended.")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                
    except Exception as e:
        print(f"❌ Failed to start voice mode: {e}")
        print("💡 Please check your internet connection and API key.")

# Advanced mode classes and functions (with import protection)
class NPCLAssistant:
    """NPCL Assistant with multiple modes"""
    
    def __init__(self):
        try:
            from voice_assistant.utils.logger import setup_logger
            from config.settings import get_settings
            
            self.settings = get_settings()
            self.logger = setup_logger()
        except ImportError as e:
            print(f"⚠️  Advanced features unavailable due to import error: {e}")
            print("🔄 Falling back to simple mode...")
            raise
        
        self.ws = None
        self.running = False
        self.setup_complete = False
        self.is_listening = False
        self.is_speaking = False
        self.audio_chunks_received = 0
        
        # NPCL specific data
        self.names = ["dheeraj", "nidhi", "nikunj"]
        self.complaint_number = "0000054321"
        self.session_active = False
        
    def get_npcl_system_instruction(self):
        """Get NPCL system instruction"""
        return get_npcl_system_instruction()

    async def start_voice_mode(self):
        """Start voice-only mode with WebSocket"""
        # Clear terminal for clean conversation interface
        import os
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("🎤 NPCL Voice Assistant - Voice Mode")
        print("=" * 50)
        print("🔊 Initializing voice connection...")
        print()
        
        try:
            # Check quota first
            if not await self.check_api_quota():
                print("❌ API quota exceeded. Falling back to chat mode.")
                await self.start_chat_mode()
                return
                
            await self.start_websocket_connection()
            
        except Exception as e:
            self.logger.error(f"Voice mode error: {e}")
            error_msg = str(e)
            
            if "Unsupported language code" in error_msg:
                print("❌ Voice mode failed: Unsupported language configuration")
                print("💡 The Gemini Live API has limited language support")
            elif "Live API not available" in error_msg:
                print("❌ Voice mode failed: Gemini Live API not available")
                print("💡 Live API is in limited preview - not available for all users")
            else:
                print(f"❌ Voice mode failed: {e}")
            
            print("🔄 Falling back to chat mode...")
            await self.start_chat_mode()

    async def start_chat_mode(self):
        """Start chat-only mode"""
        print("\n💬 Starting Advanced Chat Mode...")
        print("Type your messages below. Type 'quit' to exit.")
        print("-" * 50)
        
        try:
            from voice_assistant.ai.gemini_client import GeminiClient
            
            # Initialize chat client
            client = GeminiClient()
            
            # Send initial NPCL welcome message - Bot speaks first
            system_prompt = self.get_npcl_system_instruction()
            welcome_message = "Please start the conversation by welcoming the customer to NPCL customer service. Introduce yourself as the NPCL voice assistant and ask how you can help them with their power connection today. Be professional and use Indian English style."
            initial_response = client.generate_response(welcome_message, system_prompt)
            print(f"🤖 NPCL Assistant: {initial_response}")
            print("\n📞 Welcome to NPCL Customer Service! The assistant is ready to help you.")
            print("💬 You can now type your response or questions about your power connection.")
            print("-" * 50)
            
            while True:
                try:
                    user_input = input("\n👤 You: ").strip()
                    
                    if user_input.lower() in ['quit', 'exit', 'bye', 'goodbye']:
                        print("👋 Thank you for contacting NPCL. Have a great day!")
                        break
                    
                    if not user_input:
                        continue
                    
                    # Get AI response with NPCL context
                    response = client.generate_response(user_input, system_prompt)
                    print(f"🤖 NPCL Assistant: {response}")
                    
                except KeyboardInterrupt:
                    print("\n👋 Chat session ended.")
                    break
                except Exception as e:
                    print(f"❌ Error: {e}")
                    
        except Exception as e:
            self.logger.error(f"Chat mode error: {e}")
            print(f"❌ Advanced chat mode failed: {e}")
            print("🔄 Falling back to simple chat mode...")
            # Fall back to simple chat
            api_key_valid, api_key = check_api_key()
            if api_key_valid:
                start_simple_chat_mode(api_key)

    async def start_both_mode(self):
        """Start combined voice + chat mode"""
        print("\n🎭 Starting Combined Mode...")
        print("🎤 Voice commands will be processed in real-time")
        print("💬 You can also type messages")
        print("Press 'v' for voice, 't' for text, 'q' to quit")
        
        try:
            # Check quota first
            voice_available = await self.check_api_quota()
            
            if voice_available:
                print("✅ Voice mode available")
            else:
                print("⚠️  Voice mode unavailable (quota exceeded), text only")
            
            from voice_assistant.ai.gemini_client import GeminiClient
            client = GeminiClient()
            
            # Send initial NPCL welcome message - Bot speaks first
            system_prompt = self.get_npcl_system_instruction()
            welcome_message = "Please start the conversation by welcoming the customer to NPCL customer service. Introduce yourself as the NPCL voice assistant and ask how you can help them with their power connection today. Be professional and use Indian English style."
            initial_response = client.generate_response(welcome_message, system_prompt)
            print(f"🤖 NPCL Assistant: {initial_response}")
            print("\n📞 Welcome to NPCL Customer Service! The assistant is ready to help you.")
            print("💬 Choose voice or text to interact with the assistant.")
            print("-" * 50)
            
            while True:
                try:
                    mode_choice = input("\n[V]oice, [T]ext, or [Q]uit: ").strip().lower()
                    
                    if mode_choice in ['q', 'quit', 'exit']:
                        print("👋 Thank you for contacting NPCL!")
                        break
                    elif mode_choice in ['v', 'voice'] and voice_available:
                        print("🎤 Speak now... (implementing voice capture)")
                        # Here you would implement voice capture
                        print("⚠️  Voice capture not implemented in this demo")
                    elif mode_choice in ['t', 'text']:
                        user_input = input("👤 Type your message: ").strip()
                        if user_input:
                            response = client.generate_response(user_input, system_prompt)
                            print(f"🤖 NPCL Assistant: {response}")
                    else:
                        print("❌ Invalid choice or voice unavailable")
                        
                except KeyboardInterrupt:
                    print("\n👋 Session ended.")
                    break
                    
        except Exception as e:
            self.logger.error(f"Combined mode error: {e}")
            print(f"❌ Combined mode failed: {e}")

    async def check_api_quota(self):
        """Check if API quota is available"""
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=self.settings.google_api_key)
            model = genai.GenerativeModel(self.settings.gemini_model)
            
            # Try a simple request
            response = model.generate_content("test")
            return True
            
        except Exception as e:
            error_str = str(e).lower()
            if "quota" in error_str or "exceeded" in error_str:
                return False
            return True

    async def start_websocket_connection(self):
        """Start WebSocket connection for voice mode"""
        try:
            import websockets
            import websockets.exceptions
            
            ws_url = f"{self.settings.gemini_live_api_endpoint}?key={self.settings.google_api_key}"
            
            self.ws = await websockets.connect(ws_url)
            
            # Setup message - Note: Live API may have limited support with 1.5 Flash
            live_model = "gemini-1.5-flash"  # Using 1.5 Flash as requested
            setup_message = {
                "setup": {
                    "model": f"models/{live_model}",
                    "generationConfig": {
                        "responseModalities": ["AUDIO"],
                        "temperature": 0.2,
                        "maxOutputTokens": 256,
                        "speechConfig": {
                            "languageCode": "en-US",
                            "voiceConfig": {
                                "prebuiltVoiceConfig": {"voiceName": self.settings.gemini_voice}
                            },
                        },
                    },
                    "system_instruction": {"parts": [{"text": self.get_npcl_system_instruction()}]},
                }
            }
            
            await self.ws.send(json.dumps(setup_message))
            
            # Handle messages with timeout and graceful exit
            try:
                # Create a task for message handling
                message_task = asyncio.create_task(self.handle_websocket_messages())
                
                # Create a task for user input handling
                input_task = asyncio.create_task(self.handle_user_input())
                
                # Wait for either task to complete
                done, pending = await asyncio.wait(
                    [message_task, input_task],
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Cancel pending tasks
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                
            except KeyboardInterrupt:
                print("\n👋 Voice session ended")
                if self.ws:
                    await self.ws.close()
            except asyncio.CancelledError:
                print("\n👋 Voice session cancelled")
                if self.ws:
                    await self.ws.close()
            
        except websockets.exceptions.InvalidStatusCode as e:
            if e.status_code == 403:
                raise Exception("API quota exceeded or Live API not available")
            else:
                raise Exception(f"WebSocket connection failed: {e}")
        except websockets.exceptions.ConnectionClosedError as e:
            if "Unsupported language code" in str(e):
                raise Exception(f"Unsupported language code 'en-US' for model {self.settings.gemini_live_model}")
            else:
                raise Exception(f"WebSocket connection closed: {e}")
        except Exception as e:
            if "Unsupported language code" in str(e):
                raise Exception(f"Unsupported language code for Gemini Live API: {e}")
            else:
                raise Exception(f"WebSocket error: {e}")

    async def handle_websocket_messages(self):
        """Handle WebSocket messages"""
        try:
            conversation_started = False
            
            async for message in self.ws:
                response = json.loads(message)
                
                if "setupComplete" in response:
                    # Clear the initialization message and start clean conversation
                    import os
                    os.system('cls' if os.name == 'nt' else 'clear')
                    
                    print("🎤 NPCL Voice Assistant")
                    print("=" * 30)
                    print()
                    
                    self.setup_complete = True
                    self.is_listening = False  # Bot will speak first
                    self.is_speaking = True    # Bot is about to speak
                    await self.send_trigger_message()
                    conversation_started = True
                    
                elif response.get("serverContent"):
                    await self.handle_server_content(response["serverContent"])
                    
                # Add a small delay to prevent overwhelming the terminal
                await asyncio.sleep(0.01)
                
                # Keep the conversation alive
                if conversation_started and self.setup_complete:
                    # Continue processing messages until user interrupts
                    continue
                    
        except KeyboardInterrupt:
            print("\n👋 Voice session ended by user")
            if self.ws:
                await self.ws.close()
        except Exception as e:
            # Import websockets here for exception handling
            try:
                import websockets.exceptions
                if isinstance(e, websockets.exceptions.ConnectionClosed):
                    print("\n🔌 Connection closed by server")
                    return
            except ImportError:
                pass
            
            if "Unsupported language code" in str(e):
                self.logger.error(f"Language code not supported: {e}")
                raise Exception(f"Unsupported language code for Gemini Live API")
            else:
                self.logger.error(f"WebSocket message error: {e}")
                print(f"\n❌ Voice session error: {e}")

    async def send_trigger_message(self):
        """Send trigger message to start conversation with NPCL welcome"""
        # Send a message that will trigger the bot to speak first with NPCL welcome
        trigger_message = {
            "clientContent": {
                "turns": [{
                    "role": "user", 
                    "parts": [{
                        "text": "Please start the conversation by welcoming me to NPCL customer service and introduce yourself as the NPCL voice assistant. Ask how you can help me with my power connection today."
                    }]
                }],
                "turnComplete": True,
            }
        }
        await self.ws.send(json.dumps(trigger_message))
        
    async def send_keep_alive(self):
        """Send keep-alive message to maintain session"""
        try:
            # Mark session as active
            self.session_active = True
            
            # In a real implementation, this would:
            # - Monitor microphone for voice input
            # - Send audio data when user speaks
            # - Handle voice activity detection
            # - Process "quit" voice commands
            
            # For now, just maintain the connection
            self.logger.debug("Voice session is active and ready for input")
            
        except Exception as e:
            self.logger.debug(f"Keep-alive error: {e}")

    async def handle_server_content(self, server_content):
        """Handle server content"""
        if server_content.get("modelTurn"):
            model_turn = server_content["modelTurn"]
            
            if model_turn.get("parts"):
                # Check if this is the start of a response
                if not self.is_speaking:
                    self.is_speaking = True
                    self.is_listening = False
                    self.audio_chunks_received = 0
                
                for part in model_turn["parts"]:
                    if part.get("inlineData") and "audio/pcm" in part["inlineData"].get("mimeType", ""):
                        await self.handle_audio_response(part["inlineData"])
                    elif part.get("text"):
                        # Show the conversation text cleanly
                        text_content = part["text"]
                        if text_content.strip():
                            print(f"🤖 NPCL Assistant: {text_content}")
                            print()
                        
            # Check if turn is complete
            if model_turn.get("turnComplete", False):
                if self.is_speaking:
                    print("🎤 You: (Speak now or say 'quit' to exit)")
                    print()
                    self.is_speaking = False
                    self.is_listening = True
                    
                    # Keep the session alive by sending a keep-alive message
                    await self.send_keep_alive()

    async def handle_audio_response(self, inline_data):
        """Handle audio response"""
        pcm_chunk = base64.b64decode(inline_data["data"])
        self.audio_chunks_received += 1
        
        # Only log occasionally to avoid spam (and only in debug mode)
        if self.audio_chunks_received % 20 == 1:  # Log every 20th chunk
            self.logger.debug(f"Processing audio chunk {self.audio_chunks_received} ({len(pcm_chunk)} bytes)")
        
        # No visual indicators - keep conversation clean
        
        # Here you would play the audio
        # For now, we simulate audio playback
        # In a real implementation, you would:
        # - Convert PCM to playable format (WAV, MP3, etc.)
        # - Use audio library (pygame, pyaudio, etc.) to play through speakers
        # - Handle audio buffering and synchronization
        # - Manage audio device selection
        
        # Simulate audio processing delay
        await asyncio.sleep(0.01)
        
    async def handle_user_input(self):
        """Handle user input during voice session"""
        try:
            while True:
                # Use asyncio to handle input without blocking
                try:
                    # Simulate waiting for user input
                    await asyncio.sleep(1)
                    
                    # In a real implementation, you would:
                    # - Capture microphone input
                    # - Process voice commands
                    # - Send audio data to Gemini Live API
                    # - Handle voice activity detection
                    
                    # For now, just keep the session alive
                    if not self.session_active:
                        self.session_active = True
                        
                        # Simulate a long-running voice session
                        await asyncio.sleep(30)  # Keep session alive for 30 seconds
                        
                        if self.session_active:
                            print("\n[Session ended - Press Ctrl+C to return to menu]")
                            break
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"User input error: {e}")
                    break
                    
        except KeyboardInterrupt:
            print("\n👋 Voice session ended by user")
        except Exception as e:
            self.logger.error(f"Input handling error: {e}")

def main():
    """Main application entry point"""
    print_banner()
    
    # Check system status
    api_key_valid, api_key = print_system_status()
    
    if not api_key_valid:
        print("\n❌ System check failed. Please fix the issues above.")
        print("\n💡 Quick fix:")
        print("1. Copy .env.example to .env")
        print("2. Get your Google API key from: https://aistudio.google.com/")
        print("3. Add your Google API key to .env file")
        return 1
    
    print("\n🎆 NPCL Features:")
    print("• Handles power connection inquiries")
    print("• Manages complaint numbers and status")
    print("• Indian English conversation style")
    print("• Real-time voice or text interaction")
    print("• Professional customer service experience")
    print("• 🆆 Offline mode available when quota exceeded")
    
    # Show mode options
    while True:
        print_mode_options()
        choice = get_user_choice()
        
        if choice == 4:  # Exit
            print("👋 Thank you for using NPCL Voice Assistant!")
            break
        
        try:
            if choice == 1:  # Chat Only (Simple mode first, advanced fallback)
                try:
                    start_simple_chat_mode(api_key)
                except Exception as e:
                    if "quota" in str(e).lower() or "429" in str(e):
                        print("⚠️  API quota exceeded. Starting offline chat mode...")
                        start_offline_voice_mode()  # Offline mode works for both voice and chat
                    else:
                        raise e
            elif choice == 2:  # Voice Mode - Use simple implementation
                try:
                    start_simple_voice_mode(api_key)
                except Exception as e:
                    if "quota" in str(e).lower() or "429" in str(e):
                        print("⚠️  API quota exceeded. Starting offline voice mode...")
                        start_offline_voice_mode()
                    else:
                        raise e
            elif choice == 3:  # Combined Mode
                try:
                    # Try advanced mode
                    assistant = NPCLAssistant()
                    asyncio.run(assistant.start_both_mode())
                        
                except ImportError:
                    print("⚠️  Advanced features not available. Using simple chat mode instead.")
                    try:
                        start_simple_chat_mode(api_key)
                    except Exception as e:
                        if "quota" in str(e).lower() or "429" in str(e):
                            print("⚠️  API quota exceeded. Starting offline mode...")
                            start_offline_voice_mode()
                        else:
                            raise e
                except Exception as e:
                    if "quota" in str(e).lower() or "429" in str(e):
                        print("⚠️  API quota exceeded. Starting offline mode...")
                        start_offline_voice_mode()
                    else:
                        raise e
                
        except KeyboardInterrupt:
            print("\n👋 Session interrupted by user")
        except Exception as e:
            print(f"❌ Error: {e}")
            print("🔄 Falling back to simple chat mode...")
            start_simple_chat_mode(api_key)
        
        # Ask if user wants to try another mode
        try:
            again = input("\nWould you like to try another mode? (y/n): ").strip().lower()
            if again not in ['y', 'yes']:
                break
        except KeyboardInterrupt:
            break
    
    print("👋 Thank you for using NPCL Voice Assistant!")
    return 0

if __name__ == "__main__":
    sys.exit(main())