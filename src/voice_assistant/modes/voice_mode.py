#!/usr/bin/env python3
"""
Enhanced Voice Mode with speech recognition, timeout handling, and clean interface.
Provides seamless voice interaction with automatic fallback to chat mode.
"""

import os
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def start_enhanced_voice_mode(api_key, language_config):
    """Start enhanced voice mode with speech recognition and fallback"""
    
    # Clear terminal for clean interface
    os.system('cls' if os.name == 'nt' else 'clear')
    
    lang_code = language_config["code"]
    lang_name = language_config["native"]
    flag = language_config["flag"]
    
    print(f"🎤 NPCL Voice Assistant - Enhanced Voice Mode")
    print(f"{flag} Language: {lang_name}")
    print("=" * 50)
    print("🎯 Features:")
    print("• 🎤 Voice input with 10-second timeout")
    print("• 💬 Automatic fallback to chat mode")
    print("• 🔊 Voice output for all responses")
    print("• 🔄 Seamless mode switching")
    print("=" * 50)
    print()
    
    # Initialize voice input handler
    try:
        from simple_voice_input import SimpleVoiceInput
        voice_handler = SimpleVoiceInput(timeout=10)
        voice_available = voice_handler.is_available
        if voice_available:
            print("✅ Voice recognition initialized")
        else:
            print("⚠️  Voice recognition not available")
    except ImportError:
        print("⚠️  Voice recognition not available. Install: pip install SpeechRecognition pyaudio")
        voice_available = False
        voice_handler = None
    except Exception as e:
        print(f"⚠️  Voice setup failed: {e}")
        voice_available = False
        voice_handler = None
    
    # Initialize TTS
    tts_available = False
    try:
        # Test TTS availability
        from voice_assistant.audio.enhanced_tts import speak_text_enhanced
        tts_available = True
        print("✅ Voice output enabled")
    except ImportError:
        print("⚠️  Enhanced TTS not available, using basic TTS")
        try:
            import pyttsx3
            tts_available = True
            print("✅ Basic voice output enabled")
        except ImportError:
            print("⚠️  No TTS available")
    
    print()
    
    # Initialize AI
    try:
        import google.generativeai as genai
        from main import get_npcl_system_instruction
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Test quota
        try:
            test_response = model.generate_content("test")
        except Exception as e:
            if "quota" in str(e).lower() or "429" in str(e):
                print(f"⚠️  API quota exceeded. Switching to offline mode...")
                start_offline_voice_mode(language_config, voice_handler if voice_available else None)
                return
            else:
                print(f"❌ API error: {e}")
                return
        
        # Generate welcome message
        system_prompt = get_npcl_system_instruction(lang_code)
        language_instruction = f"Please respond in {language_config['name']} language. "
        if lang_code != "en-IN":
            language_instruction += f"Always use {language_config['name']} script and vocabulary. "
        
        enhanced_prompt = system_prompt + f"\\n\\n{language_instruction}Please start by welcoming the customer to NPCL customer service in {language_config['name']} language."
        
        try:
            initial_response = model.generate_content(enhanced_prompt)
            ai_welcome = initial_response.text
            
            print(f"🤖 NPCL Assistant: {ai_welcome}")
            print()
            
            # Speak welcome message
            if tts_available:
                speak_text_robust(ai_welcome, lang_code)
            
        except Exception as e:
            print(f"❌ Failed to generate welcome: {e}")
            # Use fallback welcome
            welcome_messages = {
                "en-IN": "Welcome to NPCL Customer Service! I am ready to help you.",
                "hi-IN": "एनपीसीएल ग्राहक सेवा में आपका स्वागत है! मैं आपकी सहायता के लिए तैयार हूं।",
                "bn-IN": "এনপিসিএল গ্রাহক সেবায় আপনাকে স্বাগতম! আমি আপনাকে সাহায্য করতে প্রস্তুত।",
                "bho-IN": "एनपीसीएल ग्राहक सेवा में रउआ के स्वागत बा! हम रउआ के मदद खातिर तैयार बानी।"
            }
            fallback_welcome = welcome_messages.get(lang_code, welcome_messages["en-IN"])
            print(f"🤖 NPCL Assistant: {fallback_welcome}")
            if tts_available:
                speak_text_robust(fallback_welcome, lang_code)
        
        # Main conversation loop
        conversation_count = 0
        while True:
            try:
                conversation_count += 1
                print(f"\\n--- Turn {conversation_count} ---")
                
                # Get user input (voice with fallback to chat)
                if voice_available and voice_handler:
                    user_input, input_mode = voice_handler.get_input_with_fallback(language_config)
                else:
                    # Chat mode only
                    user_input = input(f"💬 You ({lang_name}): ").strip()
                    input_mode = 'chat'
                
                if not user_input:
                    continue
                
                # Check for exit commands
                if user_input.lower() in ['quit', 'exit', 'bye', 'goodbye', 'बाहर निकलें', 'প্রস্থান', 'बाहर निकलीं']:
                    goodbye_messages = {
                        "en-IN": "Thank you for contacting NPCL. Have a great day!",
                        "hi-IN": "एनपीसीएल से संपर्क करने के लिए धन्यवाद। आपका दिन शुभ हो!",
                        "bn-IN": "এনপিসিএল-এর সাথে যোগাযোগ করার জন্য ধন্যবাদ। আপনার দিন শুভ হোক!",
                        "bho-IN": "एनपीसीएल से संपर्क करे खातिर धन्यवाद। रउआ के दिन मंगलमय होखे!"
                    }
                    goodbye_msg = goodbye_messages.get(lang_code, goodbye_messages["en-IN"])
                    print(f"👋 {goodbye_msg}")
                    if tts_available:
                        speak_text_robust(goodbye_msg, lang_code)
                    break
                
                # Show input mode indicator
                mode_indicator = "🎤" if input_mode == 'voice' else "💬"
                print(f"{mode_indicator} You ({lang_name}): {user_input}")
                
                # Get AI response with faster processing
                try:
                    # Shorter, more direct prompt for faster response
                    if lang_code == "hi-IN":
                        quick_prompt = f"You are NPCL customer service. Respond in Hindi only. Keep response under 50 words.\n\nUser: {user_input}\nAssistant:"
                    elif lang_code == "bho-IN":
                        quick_prompt = f"You are NPCL customer service. Respond in Bhojpuri only. Keep response under 50 words.\n\nUser: {user_input}\nAssistant:"
                    else:
                        quick_prompt = f"You are NPCL customer service. Respond in {language_config['name']} only. Keep response under 50 words.\n\nUser: {user_input}\nAssistant:"
                    
                    print("🔄 Generating response...")
                    
                    # Use streaming for faster response
                    try:
                        response = model.generate_content(quick_prompt, stream=True)
                        response_text = ""
                        print("🤖 NPCL Assistant: ", end="", flush=True)
                        
                        for chunk in response:
                            if chunk.text:
                                response_text += chunk.text
                                print(chunk.text, end="", flush=True)
                        
                        print()  # New line after response
                        print()
                        
                    except Exception:
                        # Fallback to non-streaming
                        response = model.generate_content(quick_prompt)
                        response_text = response.text
                        print(f"🤖 NPCL Assistant: {response_text}")
                        print()
                    
                    # Always speak the response
                    if tts_available:
                        speak_text_robust(response_text, lang_code)
                    
                except Exception as e:
                    if "quota" in str(e).lower() or "429" in str(e):
                        print(f"⚠️  API quota exceeded. Switching to offline mode...")
                        start_offline_voice_mode(language_config, voice_handler if voice_available else None)
                        return
                    else:
                        error_messages = {
                            "en-IN": "I apologize, but I'm having technical difficulties. Please try again.",
                            "hi-IN": "मुझे खेद है, लेकिन मुझे तकनीकी कठिनाइयों का सामना कर रहा हूं। कृपया पुनः प्रयास करें।",
                            "bn-IN": "আমি দুঃখিত, কিন্তু আমার প্রযুক্তিগত সমস্যা হচ্ছে। অনুগ্রহ করে আবার চেষ্টা করুন।",
                            "bho-IN": "माफ करीं, लेकिन हमरा तकनीकী समस्या आ रहल बा। कृपया फिर से कोशिश करीं।"
                        }
                        fallback_response = error_messages.get(lang_code, error_messages["en-IN"])
                        print(f"🤖 NPCL Assistant: {fallback_response}")
                        if tts_available:
                            speak_text_robust(fallback_response, lang_code)
                
            except KeyboardInterrupt:
                print("\\n👋 Voice session ended.")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                
    except Exception as e:
        print(f"❌ Failed to initialize voice mode: {e}")
        print("\\n💡 Make sure you have:")
        print("1. Valid Google API key in .env file")
        print("2. Internet connection")
        print("3. google-generativeai package installed")
        print("4. SpeechRecognition and pyaudio for voice input")
    
    finally:
        # Cleanup
        if voice_available and voice_handler:
            # Simple voice input doesn't need cleanup
            pass


def start_offline_voice_mode(language_config, voice_handler=None):
    """Start offline voice mode with pre-defined responses"""
    
    os.system('cls' if os.name == 'nt' else 'clear')
    
    lang_code = language_config["code"]
    lang_name = language_config["native"]
    flag = language_config["flag"]
    
    print(f"🎙️ NPCL Voice Assistant - Offline Voice Mode")
    print(f"{flag} Language: {lang_name}")
    print("=" * 50)
    print("⚠️  API quota exceeded - using offline responses")
    print("🎤 Voice input still available with chat fallback")
    print("=" * 50)
    print()
    
    # Test TTS
    tts_available = False
    try:
        from voice_assistant.audio.enhanced_tts import speak_text_enhanced
        tts_available = True
        print("✅ Voice output enabled")
    except ImportError:
        try:
            import pyttsx3
            tts_available = True
            print("✅ Basic voice output enabled")
        except ImportError:
            print("⚠️  No TTS available")
    
    print()
    
    def get_offline_response(user_input, lang_code):
        """Get offline NPCL response"""
        user_lower = user_input.lower()
        
        responses = {
            "en-IN": {
                "greeting": "Namaste! Welcome to NPCL customer service. I'm in offline mode but can help with basic inquiries.",
                "power": "I understand you have a power issue. Your complaint number is NPCL-OFF-001. Our team will address this within 24 hours.",
                "complaint": "I can register your complaint. Your complaint number is NPCL-OFF-002. Please keep this for reference.",
                "default": "Thank you for contacting NPCL. I'm in offline mode. For immediate help, please call our helpline."
            },
            "hi-IN": {
                "greeting": "नमस्ते! एनपीसीएल ग्राहक सेवा में आपका स्वागत है। मैं ऑफ़लाइन मोड में हूं लेकिन बुनियादी सहायता कर सकता हूं।",
                "power": "मैं समझता हूं कि आपको बिजली की समस्या है। आपकी शिकायत संख्या NPCL-OFF-001 है। हमारी टीम 24 घंटों में इसका समाधान करेगी।",
                "complaint": "मैं आपकी शिकायत दर्ज कर सकता हूं। आपकी शिकायत संख्या NPCL-OFF-002 है। कृपया इसे संदर्भ के लिए रखें।",
                "default": "एनपीसीएल से संपर्क करने के लिए धन्यवाद। मैं ऑफ़लाइन मोड में हूं। तत्काल सहायता के लिए हमारी हेल्पलाइन पर कॉल करें।"
            },
            "bho-IN": {
                "greeting": "नमस्कार! एनपीसीएल ग्राहक सेवा में रउआ के स्वागत बा। हम ऑफलाइन मोड में बानी लेकिन बुनियादी मदद कर सकीं।",
                "power": "हम समझत बानी कि रउआ के बिजली के समस्या बा। रउआ के शिकायत नंबर NPCL-OFF-001 बा। हमार टीम 24 घंटा में एकर समाधान कर देई।",
                "complaint": "हम रउआ के शिकायत दर्ज कर सकीं। रउआ के शिकायत नंबर NPCL-OFF-002 बा। कृपया एकरा संदर्भ खातिर रखीं।",
                "default": "एनपीसीएल से संपर्क करे खातिर धन्यवाद। हम ऑफलाइन मोड में बानी। तुरंत मदद खातिर हमार हेल्पलाइन पर कॉल करीं।"
            }
        }
        
        lang_responses = responses.get(lang_code, responses["en-IN"])
        
        if any(word in user_lower for word in ['hello', 'hi', 'namaste', 'नमस्ते', 'नमस्कार']):
            return lang_responses["greeting"]
        elif any(word in user_lower for word in ['power', 'electricity', 'बिजली']):
            return lang_responses["power"]
        elif any(word in user_lower for word in ['complaint', 'problem', 'शिकायत']):
            return lang_responses["complaint"]
        else:
            return lang_responses["default"]
    
    # Welcome message
    welcome_messages = {
        "en-IN": "Welcome to NPCL! I'm in offline mode but ready to help with basic inquiries.",
        "hi-IN": "एनपीसीएल में आपका स्वागत है! मैं ऑफ़लाइन मोड में हूं लेकिन बुनियादी सहायता के लिए तैयार हूं।",
        "bho-IN": "एनपीसीएल में रउआ के स्वागत बा! हम ऑफलाइन मोड में बानी लेकिन बुनियादी मदद खातिर तैयार बानी।"
    }
    welcome = welcome_messages.get(lang_code, welcome_messages["en-IN"])
    
    print(f"🤖 NPCL Assistant: {welcome}")
    print()
    if tts_available:
        speak_text_robust(welcome, lang_code)
    
    # Conversation loop
    conversation_count = 0
    while True:
        try:
            conversation_count += 1
            print(f"\\n--- Turn {conversation_count} ---")
            
            # Get user input
            if voice_handler:
                user_input, input_mode = voice_handler.get_input_with_fallback(language_config)
            else:
                user_input = input(f"💬 You ({lang_name}): ").strip()
                input_mode = 'chat'
            
            if not user_input:
                continue
            
            # Check for exit
            if user_input.lower() in ['quit', 'exit', 'bye', 'goodbye', 'बाहर निकलें', 'बाहर निकलीं']:
                goodbye_messages = {
                    "en-IN": "Thank you for contacting NPCL. Have a great day!",
                    "hi-IN": "एनपीसीएल से संपर्क करने के लिए धन्यवाद। आपका दिन शुभ हो!",
                    "bho-IN": "एनपीसीएल से संपर्क करे खातिर धन्यवाद। रउआ के दिन मंगलमय होखे!"
                }
                goodbye_msg = goodbye_messages.get(lang_code, goodbye_messages["en-IN"])
                print(f"👋 {goodbye_msg}")
                if tts_available:
                    speak_text_robust(goodbye_msg, lang_code)
                break
            
            # Show input
            mode_indicator = "🎤" if input_mode == 'voice' else "💬"
            print(f"{mode_indicator} You ({lang_name}): {user_input}")
            
            # Get offline response (fast)
            print("🔄 Processing...")
            response_text = get_offline_response(user_input, lang_code)
            print(f"🤖 NPCL Assistant: {response_text}")
            print()
            
            # Speak response
            if tts_available:
                speak_text_robust(response_text, lang_code)
            
        except KeyboardInterrupt:
            print("\\n👋 Voice session ended.")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Cleanup
    if voice_handler:
        # Simple voice input doesn't need cleanup
        pass


def speak_text_robust(text, language_code="en-IN"):
    """Robust TTS function"""
    try:
        from voice_assistant.audio.enhanced_tts import speak_text_enhanced
        return speak_text_enhanced(text, language_code)
    except ImportError:
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty('rate', 120)
            engine.setProperty('volume', 1.0)
            engine.say(text)
            engine.runAndWait()
            engine.stop()
            del engine
            return True
        except Exception as e:
            print(f"⚠️  TTS error: {e}")
            return False