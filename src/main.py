#!/usr/bin/env python3
"""
Main entry point for NPCL Asterisk ARI Voice Assistant with Multi-Language Support
Provides multiple interaction modes including chat, voice, and combined modes with Gemini AI integration.

NPCL Voice Assistant - Main Entry Point with 12 Language Support
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

# Suppress warnings and debug messages for clean output
try:
    from suppress_warnings import *
except ImportError:
    # Fallback warning suppression
    os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=UserWarning)

def print_banner():
    """Print application banner"""
    print("=" * 70)
    print("🌍 NPCL Multilingual Voice Assistant")
    print("🎆 Powered by Gemini 1.5 Flash")
    print("🗣️ Supporting 12 Languages")
    print("=" * 70)

def print_language_selection():
    """Print language selection menu"""
    print("\n🌍 Choose Your Language / अपनी भाषा चुनें / আপনার ভাষা বেছে নিন:")
    print("=" * 60)
    print("1.  🇮🇳 English (India)")
    print("2.  🇮🇳 हिन्दी (Hindi)")
    print("3.  🇮🇳 বাংলা (Bengali)")
    print("4.  🇮🇳 తెలుగు (Telugu)")
    print("5.  🇮🇳 मराठी (Marathi)")
    print("6.  🇮🇳 தமிழ் (Tamil)")
    print("7.  🇮🇳 ગુજરાતી (Gujarati)")
    print("8.  🇮🇳 اردو (Urdu)")
    print("9.  🇮🇳 ಕನ್ನಡ (Kannada)")
    print("10. 🇮🇳 ଓଡ଼ିଆ (Odia)")
    print("11. 🇮🇳 മലയാളം (Malayalam)")
    print("12. 🇮🇳 भोजपुरी (Bhojpuri)")
    print("=" * 60)

def get_language_choice():
    """Get user's language choice"""
    while True:
        try:
            choice = input("\nEnter your choice (1-12): ").strip()
            if choice in [str(i) for i in range(1, 13)]:
                return int(choice)
            else:
                print("❌ Invalid choice. Please enter 1-12.")
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            return None
        except Exception:
            print("❌ Invalid input. Please enter a number.")

def get_language_config(choice):
    """Get language configuration based on choice"""
    languages = {
        1: {"code": "en-IN", "name": "English", "native": "English", "flag": "🇮🇳"},
        2: {"code": "hi-IN", "name": "Hindi", "native": "हिन्दी", "flag": "🇮🇳"},
        3: {"code": "bn-IN", "name": "Bengali", "native": "বাংলা", "flag": "🇮🇳"},
        4: {"code": "te-IN", "name": "Telugu", "native": "తెలుగు", "flag": "🇮🇳"},
        5: {"code": "mr-IN", "name": "Marathi", "native": "मराठी", "flag": "🇮🇳"},
        6: {"code": "ta-IN", "name": "Tamil", "native": "தமிழ்", "flag": "🇮🇳"},
        7: {"code": "gu-IN", "name": "Gujarati", "native": "ગુજરાતી", "flag": "🇮🇳"},
        8: {"code": "ur-IN", "name": "Urdu", "native": "اردو", "flag": "🇮🇳"},
        9: {"code": "kn-IN", "name": "Kannada", "native": "ಕನ್ನಡ", "flag": "🇮🇳"},
        10: {"code": "or-IN", "name": "Odia", "native": "ଓଡ଼ିଆ", "flag": "🇮🇳"},
        11: {"code": "ml-IN", "name": "Malayalam", "native": "മലയാളം", "flag": "🇮🇳"},
        12: {"code": "bho-IN", "name": "Bhojpuri", "native": "भोजपुरी", "flag": "🇮🇳"}
    }
    return languages.get(choice)

def get_welcome_messages():
    """Get welcome messages in all languages"""
    return {
        "en-IN": "Welcome to NPCL Customer Service! I am your multilingual voice assistant.",
        "hi-IN": "एनपीसीएल ग्राहक सेवा में आपका स्वागत है! मैं आपका बहुभाषी आवाज सहायक हूं।",
        "bn-IN": "এনপিসিএল গ্রাহক সেবায় আপনাকে স্বাগতম! আমি আপনার বহুভাষিক কণ্ঠ সহায়ক।",
        "te-IN": "NPCL కస్టమర్ సర్వీస్‌కు స్వాగతం! నేను మీ బహుభాషా వాయిస్ అసిస్టెంట్‌ని।",
        "mr-IN": "एनपीसीएल ग्राहक सेवेत आपले स्वागत आहे! मी तुमचा बहुभाषिक आवाज सहाय्यक आहे।",
        "ta-IN": "NPCL வாடிக்கையாளர் சேவைக்கு வரவேற்கிறோம்! நான் உங்கள் பன்மொழி குரல் உதவியாளர்।",
        "gu-IN": "NPCL કસ્ટમર સર્વિસમાં આપનું સ્વાગત છે! હું તમારો બહુભાષી અવાજ સહાયક છું।",
        "ur-IN": "NPCL کسٹمر سروس میں آپ کا خوش آمدید! میں آپ کا کثیر لسانی آواز معاون ہوں۔",
        "kn-IN": "NPCL ಗ್ರಾಹಕ ಸೇವೆಗೆ ಸ್ವಾಗತ! ನಾನು ನಿಮ್ಮ ಬಹುಭಾಷಾ ಧ್ವನಿ ಸಹಾಯಕ.",
        "or-IN": "NPCL ଗ୍ରାହକ ସେବାରେ ଆପଣଙ୍କୁ ସ୍ୱାଗତ! ମୁଁ ଆପଣଙ୍କର ବହୁଭାଷୀ ସ୍ୱର ସହାୟକ।",
        "ml-IN": "NPCL കസ്റ്റമർ സർവീസിലേക്ക് സ്വാഗതം! ഞാൻ നിങ്ങളുടെ ബഹുഭാഷാ ശബ്ദ സഹായകനാണ്।",
        "bho-IN": "एनपीसीएल ग्राहक सेवा में रउआ के स्वागत बा! हम रउआ के बहुभाषी आवाज सहायक बानी।"
    }

def get_mode_selection_messages():
    """Get mode selection messages in all languages"""
    return {
        "en-IN": {
            "title": "🎯 Choose Your Assistant Mode:",
            "chat": "💬 Chat Mode - Text-based conversation",
            "voice": "🎤 Voice Mode - Real-time voice conversation",
            "combined": "🎭 Combined Mode - Voice + Chat",
            "exit": "❌ Exit",
            "prompt": "Enter your choice (1-4): ",
            "note": "💡 Note: If API quota is exceeded, offline mode will start automatically"
        },
        "hi-IN": {
            "title": "🎯 अपना सहायक मोड चुनें:",
            "chat": "💬 चैट मोड - टेक्स्ट-आधारित बातचीत",
            "voice": "🎤 वॉयस मोड - रियल-टाइम वॉयस बातचीत",
            "combined": "🎭 संयुक्त मोड - वॉयस + चैट",
            "exit": "❌ बाहर निकलें",
            "prompt": "अपनी पसंद दर्ज करें (1-4): ",
            "note": "💡 नोट: यदि API कोटा समाप्त हो जाता है, तो ऑफ़लाइन मोड अपने आप शुरू हो जाएगा"
        },
        "bn-IN": {
            "title": "🎯 আপনার সহায়ক মোড বেছে নিন:",
            "chat": "💬 চ্যাট মোড - টেক্সট-ভিত্তিক কথোপকথন",
            "voice": "🎤 ভয়েস মোড - রিয়েল-টাইম ভয়েস কথোপকথন",
            "combined": "🎭 সম্মিলিত মোড - ভয়েস + চ্যাট",
            "exit": "❌ প্রস্থান",
            "prompt": "আপনার পছন্দ লিখুন (1-4): ",
            "note": "💡 নোট: যদি API কোটা শেষ হয়ে যায়, অফলাইন মোড স্বয়ংক্রিয়ভাবে শুরু হবে"
        },
        "bho-IN": {
            "title": "🎯 मोड चुनीं:",
            "chat": "💬 चैट मोड - टेक्स्ट-आधारित बातचीत",
            "voice": "🎤 वॉयस मोड - रियल-टाइम वॉयस बातचीत",
            "combined": "🎭 संयुक्त मोड - वॉयस + चैट",
            "exit": "❌ बाहर निकलीं",
            "prompt": "अपना विकल्प दर्ज करीं (1-4): ",
            "note": "💡 नोट: यदि API कोटा समाप्त हो जाता है, तो ऑफ़लाइन मोड अपने आप शुरू हो जाएगा"
        }
    }

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

def speak_text_robust(text, language_code="en-IN"):
    """Enhanced TTS function with multilingual support and text cleaning"""
    try:
        # Try to import the enhanced TTS module
        from voice_assistant.audio.enhanced_tts import speak_text_enhanced
        return speak_text_enhanced(text, language_code)
    except ImportError:
        # Fallback to basic implementation if module not available
        return speak_text_basic(text, language_code)

def speak_text_basic(text, language_code="en-IN"):
    """Basic TTS fallback function"""
    try:
        import pyttsx3
        import re
        
        # Basic text cleaning for Hindi
        cleaned_text = text
        if language_code == "hi-IN":
            # Replace problematic characters
            cleaned_text = cleaned_text.replace('/', ' ')
            cleaned_text = cleaned_text.replace('\n', ' ')
            cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
            cleaned_text = cleaned_text.strip()
        
        # Reinitialize engine for each call (Windows fix)
        engine = pyttsx3.init()
        
        # Configure engine
        engine.setProperty('rate', 120)  # Slower for better clarity
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
        
        # Speak the cleaned text
        engine.say(cleaned_text)
        engine.runAndWait()
        
        # Cleanup engine (important for Windows)
        try:
            engine.stop()
            del engine
        except:
            pass
        
        return True
        
    except Exception as e:
        print(f"⚠️  Voice error: {e}")
        print(f"Text was: {text[:50]}...")
        return False

def get_npcl_system_instruction(language_code="en-IN"):
    """Get NPCL system instruction in specified language"""
    instructions = {
        "en-IN": """You are a customer service assistant for NPCL (Noida Power Corporation Limited), a power utility company.

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
Always be ready to help with power-related issues.""",

        "hi-IN": """आप एनपीसीएल (नोएडा पावर कॉर्पोरेशन लिमिटेड) के लिए ग्राहक सेवा सहायक हैं, जो एक पावर यूटिलिटी कंपनी है।

आपकी भूमिका:
- बिजली कनेक्शन की पूछताछ में ग्राहकों की सहायता करना
- शिकायत पंजीकरण और स्थिति अपडेट को संभालना
- पेशेवर ग्राहक सेवा प्रदान करना
- विनम्र हिंदी संवाद शैली का उपयोग करना

जब ग्राहक आपसे संपर्क करते हैं:
1. उनका पेशेवर तरीके से स्वागत करें
2. उनके कनेक्शन विवरण या शिकायत संख्या के लिए पूछें
3. उनकी बिजली सेवा के बारे में सहायक जानकारी प्रदान करें
4. आवश्यकता पड़ने पर नई शिकायतें दर्ज करें
5. मौजूदा शिकायतों पर स्थिति अपडेट दें

संवाद शैली:
- सम्मानजनक रहें और "सर" या "मैडम" का उपयोग करें
- हिंदी वाक्यों का प्राकृतिक उपयोग करें
- स्पष्ट रूप से बोलें और सहायक बनें
- प्रतिक्रियाओं को संक्षिप्त और पेशेवर रखें

नमूना शिकायत संख्या प्रारूप: 0000054321
हमेशा बिजली संबंधी समस्याओं में मदद के लिए तैयार रहें।""",

        "bn-IN": """আপনি এনপিসিএল (নোয়েডা পাওয়ার কর্পোরেশন লিমিটেড) এর জন্য একজন গ্রাহক সেবা সহায়ক, যা একটি পাওয়ার ইউটিলিটি কোম্পানি।

আপনার ভূমিকা:
- বিদ্যুৎ সংযোগের অনুসন্ধানে গ্রাহকদের সাহায্য করা
- অভিযোগ নিবন্ধন এবং স্থিতি আপডেট পরিচালনা করা
- পেশাদার গ্রাহক সেবা প্রদান করা
- ভদ্র বাংলা যোগাযোগ শৈলী ব্যবহার করা

যখন গ্রাহকরা আপনার সাথে যোগাযোগ করেন:
1. তাদের পেশাদারভাবে স্বাগত জানান
2. তাদের সংযোগের বিবরণ বা অভিযোগ নম্বর জিজ্ঞাসা করুন
3. তাদের বিদ্যুৎ সেবা সম্পর্কে সহায়ক তথ্য প্রদান করুন
4. প্রয়োজনে নতুন অভিযোগ নিবন্ধন করুন
5. বিদ্যমান অভিযোগের স্থিতি আপডেট দিন

যোগাযোগ শৈলী:
- সম্মানজনক থাকুন এবং "স্যার" বা "ম্যাডাম" ব্যবহার করুন
- বাংলা বাক্যাংশ প্রাকৃতিকভাবে ব্যবহার করুন
- স্পষ্টভাবে কথা বলুন এবং সহায়ক হন
- প্রতিক্রিয়া সংক্ষিপ্ত এবং পেশাদার রাখুন

নমুনা অভিযোগ নম্বর বিন্যাস: 0000054321
সর্বদা বিদ্যুৎ সংক্রান্ত সমস্যায় সাহায্যের জন্য প্রস্তুত থাকুন।""",

        "bho-IN": """रउआ एनपीसीएल (नोएडा पावर कॉर्पोरेशन लिमिटेड) के ग्राहक सेवा सहायक बानी, ई एगो बिजली उपयोगिता कंपनी बा।

रउआ के भूमिका:
- बिजली कनेक्शन के पूछताछ में ग्राहकन के मदद करीं
- शिकायत पंजीकरण आ स्थिति अपडेट के संभालीं
- पेशेवर ग्राहक सेवा प्रदान करीं
- विनम्र भोजपुरी संवाद शैली के उपयोग करीं

जब ग्राहक रउआ से संपर्क करे:
1. ओकरा के पेशेवर तरीका से स्वागत करीं
2. ओकरा के कनेक्शन विवरण या शिकायत नंबर के पूछीं
3. ओकरा के बिजली सेवा के बारे में सहायक जानकारी दीं
4. जरूरत पड़े पर नया शिकायत दर्ज करीं
5. मौजूदा शिकायतन पर स्थिति अपडेट दीं

संवाद शैली:
- सम्मानजनक रहीं आ "सर" या "मैडम" के उपयोग करीं
- भोजपुरी वाक्यन के प्राकृतिक उपयोग करीं
- स्पष्ट रूप से बोलीं आ सहायक बनीं
- जवाबन के संक्षिप्त आ पेशेवर रखीं

नमूना शिकायत नंबर प्रारूप: 0000054321
हमेशा बिजली संबंधी समस्यान में मदद खातिर तैयार रहीं।"""
    }
    
    return instructions.get(language_code, instructions["en-IN"])

def start_multilingual_chat_mode(api_key, language_config):
    """Start multilingual chat mode"""
    # Clear terminal for clean conversation interface
    import os
    os.system('cls' if os.name == 'nt' else 'clear')
    
    lang_code = language_config["code"]
    lang_name = language_config["native"]
    flag = language_config["flag"]
    
    print(f"💬 NPCL Voice Assistant - Chat Mode")
    print(f"{flag} Language: {lang_name}")
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
    
    print()
    
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
                start_offline_mode(language_config)
                return
            else:
                print(f"❌ API error: {e}")
                return
        
        # Generate and speak welcome message
        try:
            system_prompt = get_npcl_system_instruction(lang_code)
            welcome_messages = get_welcome_messages()
            welcome_text = welcome_messages.get(lang_code, welcome_messages["en-IN"])
            
            # Add instruction to respond in the selected language
            language_instruction = f"Please respond in {language_config['name']} language. "
            if lang_code != "en-IN":
                language_instruction += f"Always use {language_config['name']} script and vocabulary. "
            
            enhanced_prompt = system_prompt + f"\n\n{language_instruction}Please start by welcoming the customer to NPCL customer service in {language_config['name']} language."
            
            initial_response = model.generate_content(enhanced_prompt)
            ai_welcome = initial_response.text
            
            print(f"🤖 NPCL Assistant: {ai_welcome}")
            print()
            
            # Speak the welcome message using robust TTS
            if tts_available:
                speak_text_robust(ai_welcome, lang_code)
            
        except Exception as e:
            if "quota" in str(e).lower() or "429" in str(e):
                print(f"⚠️  API quota exceeded during welcome. Switching to offline mode...")
                start_offline_mode(language_config)
                return
            else:
                print(f"❌ Failed to generate welcome: {e}")
                # Fallback welcome
                welcome_messages = get_welcome_messages()
                fallback_welcome = welcome_messages.get(lang_code, welcome_messages["en-IN"])
                print(f"🤖 NPCL Assistant: {fallback_welcome}")
                if tts_available:
                    speak_text_robust(fallback_welcome, lang_code)
        
        while True:
            try:
                user_input = input(f"\n👤 You ({lang_name}): ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'bye', 'goodbye', 'बाहर निकलें', 'প্রস্থান', 'έξοδος']:
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
                
                if not user_input:
                    continue
                
                # Get AI response with quota check
                try:
                    # Enhanced prompt with language instruction
                    language_instruction = f"Please respond in {language_config['name']} language only. "
                    if lang_code != "en-IN":
                        language_instruction += f"Use {language_config['name']} script and vocabulary. "
                    
                    prompt = f"{system_prompt}\n\n{language_instruction}\n\nUser: {user_input}\nAssistant:"
                    response = model.generate_content(prompt)
                    
                    # Display and speak the response
                    response_text = response.text
                    print(f"🤖 NPCL Assistant: {response_text}")
                    print()
                    
                    # Always speak the response using robust TTS
                    if tts_available:
                        speak_text_robust(response_text, lang_code)
                    
                except Exception as e:
                    if "quota" in str(e).lower() or "429" in str(e):
                        print(f"⚠️  API quota exceeded. Switching to offline mode...")
                        start_offline_mode(language_config)
                        return
                    else:
                        # Fallback response for other errors
                        error_messages = {
                            "en-IN": "I apologize, but I'm having technical difficulties. Please try again or contact our customer service directly.",
                            "hi-IN": "मुझे खेद है, लेकिन मुझे तकनीकी कठिनाइयों का सामना कर रहा हूं। कृपया पुनः प्रयास करें या सीधे हमारी ग्राहक सेवा से संपर्क करें।",
                            "bn-IN": "আমি দুঃখিত, কিন্তু আমার প্রযুক্তিগত সমস্যা হচ্ছে। অনুগ্রহ করে আবার চেষ্টা করুন বা সরাসরি আমাদের গ্রাহক সেবায় যোগাযোগ করুন।",
                            "bho-IN": "माफ करीं, लेकिन हमरा तकनीकी समस्या आ रहल बा। कृपया फिर से कोशिश करीं या सीधे हमार ग्राहक सेवा से संपर्क करीं।"
                        }
                        fallback_response = error_messages.get(lang_code, error_messages["en-IN"])
                        print(f"🤖 NPCL Assistant: {fallback_response}")
                        if tts_available:
                            speak_text_robust(fallback_response, lang_code)
                
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

def start_offline_mode(language_config):
    """Start offline mode with multilingual support and voice input"""
    try:
        # Try to use enhanced offline voice mode
        from voice_assistant.modes.voice_mode import start_offline_voice_mode
        start_offline_voice_mode(language_config)
        return
    except ImportError:
        # Fallback to basic offline mode
        pass
    
    import os
    os.system('cls' if os.name == 'nt' else 'clear')
    
    lang_code = language_config["code"]
    lang_name = language_config["native"]
    flag = language_config["flag"]
    
    print(f"🎙️ NPCL Voice Assistant - Offline Mode")
    print(f"{flag} Language: {lang_name}")
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
    
    print()
    
    def get_offline_response(user_input, lang_code):
        """Get offline NPCL response in specified language"""
        user_lower = user_input.lower()
        
        # Offline responses in multiple languages
        responses = {
            "en-IN": {
                "greeting": "Namaste! Welcome to NPCL customer service. I'm currently in offline mode due to high demand. How can I help you with your power connection today?",
                "power": "I understand you're experiencing a power issue. Please note your complaint number: NPCL-OFF-001. Our technical team will address this within 24 hours. Is there anything else I can help with?",
                "complaint": "I can help register your complaint. Your complaint number is NPCL-OFF-002. Please keep this number for future reference. Our team will contact you within 24 hours.",
                "bill": "For billing inquiries, please visit our nearest NPCL office or call our billing helpline. Your account details are secure and will be reviewed by our billing team.",
                "connection": "For new power connections, please visit our customer service center with required documents. The process typically takes 7-10 working days.",
                "thanks": "You're welcome! Thank you for contacting NPCL. Is there anything else I can assist you with today?",
                "default": "Thank you for contacting NPCL. I'm currently in offline mode. For immediate assistance, please call our helpline or visit our customer service center. Your query is important to us."
            },
            "hi-IN": {
                "greeting": "नमस्ते! एनपीसीएल ग्राहक सेवा में आपका स्वागत है। मैं वर्तमान में उच्च मांग के कारण ऑफ़लाइन मोड में हूं। आज मैं आपके बिजली कनेक्शन के लिए कैसे सहायता कर सकता हूं?",
                "power": "मैं समझता हूं कि आप बिजली की समस्या का सामना कर रहे हैं। कृपया अपनी शिकायत संख्या नोट करें: NPCL-OFF-001। हमारी तकनीकी टीम 24 घंटों के भीतर इसका समाधान करेगी।",
                "complaint": "मैं आपकी शिकायत दर्ज करने में सहायता कर सकता हूं। आपकी शिकायत संख्या है NPCL-OFF-002। कृपया भविष्य के संदर्भ के लिए इस संख्या को रखें।",
                "bill": "बिलिंग पूछताछ के लिए, कृपया हमारे निकटतम एनपीसीएल कार्यालय में जाएं या हमारी बिलिंग हेल्पलाइन पर कॉल करें।",
                "connection": "नए बिजली कनेक्शन के लिए, कृपया आवश्यक दस्तावेजों के साथ हमारे ग्राहक सेवा केंद्र में जाएं।",
                "thanks": "आपका स्वागत है! एनपीसीएल से संपर्क करने के लिए धन्यवाद। क्या आज मैं आपकी कोई और सहायता कर सकता हूं?",
                "default": "एनपीसीएल से संपर्क करने के लिए धन्यवाद। मैं वर्तमान में ऑफ़लाइन मोड में हूं। तत्काल सहायता के लिए, कृपया हमारी हेल्पलाइन पर कॉल करें।"
            },
            "bn-IN": {
                "greeting": "নমস্কার! এনপিসিএল গ্রাহক সেবায় আপনাকে স্বাগতম। উচ্চ চাহিদার কারণে আমি বর্তমানে অফলাইন মোডে আছি। আজ আপনার বিদ্যুৎ সংযোগের জন্য আমি কীভাবে সাহায্য করতে পারি?",
                "power": "আমি বুঝতে পারছি আপনি বিদ্যুৎ সমস্যার সম্মুখীন হচ্ছেন। অনুগ্রহ করে আপনার অভিযোগ নম্বর নোট করুন: NPCL-OFF-001। আমাদের প্রযুক্তিগত দল ২৪ ঘন্টার মধ্যে এটি সমাধান করবে।",
                "complaint": "আমি আপনার অভিযোগ নিবন্ধন করতে সাহায্য করতে পারি। আপনার অভিযোগ নম্বর হল NPCL-OFF-002। ভবিষ্যতের রেফারেন্সের জন্য এই নম্বরটি রাখুন।",
                "bill": "বিলিং অনুসন্ধানের জন্য, অনুগ্রহ করে আমাদের নিকটতম এনপিসিএল অফিসে যান বা আমাদের বিলিং হেল্পলাইনে কল করুন।",
                "connection": "নতুন বিদ্যুৎ সংযোগের জন্য, প্রয়োজনীয় কাগজপত্র নিয়ে আমাদের গ্রাহক সেবা কেন্দ্রে যান।",
                "thanks": "আপনাকে স্বাগতম! এনপিসিএল-এর সাথে যোগাযোগ করার জন্য ধন্যবাদ। আজ আমি আপনার আর কোন সাহায্য করতে পারি?",
                "default": "এনপিসিএল-এর সাথে যোগাযোগ করার জন্য ধন্যবাদ। আমি বর্তমানে অফলাইন মোডে আছি। তাৎক্ষণিক সহায়তার জন্য, আমাদের হেল্পলাইনে কল করুন।"
            },
            "bho-IN": {
                "greeting": "नमस्कार! एनपीसीएल ग्राहक सेवा में रउआ के स्वागत बा। हम अभी ऑफलाइन मोड में बानी उच्च मांग के कारण। आज हम रउआ के बिजली कनेक्शन खातिर कइसे मदद कर सकीं?",
                "power": "हम समझत बानी कि रउआ के बिजली के समस्या आ रहल बा। कृपया अपना शिकायत नंबर नोट करीं: NPCL-OFF-001। हमार तकनीकी टीम 24 घंटा में एकर समाधान कर देई।",
                "complaint": "हम रउआ के शिकायत दर्ज करे में मदद कर सकीं। रउआ के शिकायत नंबर बा NPCL-OFF-002। कृपया भविष्य के संदर्भ खातिर ई नंबर रखीं।",
                "bill": "बिलिंग पूछताछ खातिर, कृपया हमार निकटतम एनपीसीएल कार्यालय जाईं या हमार बिलिंग हेल्पलाइन पर कॉल करीं।",
                "connection": "नया बिजली कनेक्शन खातिर, कृपया जरूरी कागजात के साथ हमार ग्राहक सेवा केंद्र जाईं।",
                "thanks": "रउआ के स्वागत बा! एनपीसीएल से संपर्क करे खातिर धन्यवाद। आज हम रउआ के कवनो आउर मदद कर सकीं?",
                "default": "एनपीसीएल से संपर्क करे खातिर धन्यवाद। हम अभी ऑफलाइन मोड में बानी। तुरंत मदद खातिर, हमार हेल्पलाइन पर कॉल करीं।"
            }
        }
        
        lang_responses = responses.get(lang_code, responses["en-IN"])
        
        # Check for greeting words
        if any(word in user_lower for word in ['hello', 'hi', 'hey', 'namaste', 'नमस्ते', 'নমস্কার', 'γεια']):
            return lang_responses["greeting"]
        
        elif any(word in user_lower for word in ['power', 'electricity', 'outage', 'cut', 'बिजली', 'বিদ্যুৎ', 'ρεύμα']):
            return lang_responses["power"]
        
        elif any(word in user_lower for word in ['complaint', 'problem', 'issue', 'शिकायत', 'অভিযোগ', 'παράπονο']):
            return lang_responses["complaint"]
        
        elif any(word in user_lower for word in ['bill', 'payment', 'amount', 'बिल', 'বিল', 'λογαριασμός']):
            return lang_responses["bill"]
        
        elif any(word in user_lower for word in ['connection', 'new', 'apply', 'कनेक्शन', 'সংযোগ', 'σύνδεση']):
            return lang_responses["connection"]
        
        elif any(word in user_lower for word in ['thank', 'thanks', 'धन्यवाद', 'ধন্যবাদ', 'ευχαριστώ']):
            return lang_responses["thanks"]
        
        else:
            return lang_responses["default"]
    
    # Welcome message
    welcome_messages = get_welcome_messages()
    welcome = welcome_messages.get(lang_code, welcome_messages["en-IN"])
    welcome += " I'm currently in offline mode due to high API usage, but I can still help with basic inquiries."
    
    print(f"🤖 NPCL Assistant: {welcome}")
    print()
    if tts_available:
        speak_text_robust(welcome, lang_code)
    
    # Conversation loop
    while True:
        try:
            user_input = input(f"\n👤 You ({lang_name}): ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ['quit', 'exit', 'bye', 'goodbye', 'बाहर निकलें', 'প্রস্থান', 'έξοδος']:
                goodbye_messages = {
                    "en-IN": "Thank you for contacting NPCL. Have a great day! Please try again later when our AI service is available.",
                    "hi-IN": "एनपीसीएल से संपर्क करने के लिए धन्यवाद। आपका दिन शुभ हो! जब हमारी AI सेवा उपलब्ध हो तो कृपया बाद में पुनः प्रयास करें।",
                    "bn-IN": "এনপিসিএল-এর সাথে যোগাযোগ করার জন্য ধন্যবাদ। আপনার দিন শুভ হোক! আমাদের AI সেবা উপলব্ধ হলে পরে আবার চেষ্টা করুন।",
                    "bho-IN": "एनपीसीएल से संपर्क करे खातिर धन्यवाद। रउआ के दिन मंगलमय होखे! जब हमार AI सेवा उपलब्ध होखे तब फिर से कोशिश करीं।"
                }
                goodbye_msg = goodbye_messages.get(lang_code, goodbye_messages["en-IN"])
                print(f"👋 {goodbye_msg}")
                if tts_available:
                    speak_text_robust(goodbye_msg, lang_code)
                break
            
            # Get offline response
            response_text = get_offline_response(user_input, lang_code)
            print(f"🤖 NPCL Assistant: {response_text}")
            print()
            
            # Speak the response
            if tts_available:
                speak_text_robust(response_text, lang_code)
            
        except KeyboardInterrupt:
            print("\n👋 Voice session ended.")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

def print_mode_options(language_config):
    """Print mode selection options in selected language"""
    lang_code = language_config["code"]
    mode_messages = get_mode_selection_messages()
    messages = mode_messages.get(lang_code, mode_messages["en-IN"])
    
    print(f"\n{messages['title']}")
    print(f"1. {messages['chat']}")
    print(f"2. {messages['voice']}")
    print(f"3. {messages['combined']}")
    print(f"4. {messages['exit']}")
    print()
    print(messages['note'])
    print()

def get_user_choice(language_config):
    """Get user's mode choice in selected language"""
    lang_code = language_config["code"]
    mode_messages = get_mode_selection_messages()
    messages = mode_messages.get(lang_code, mode_messages["en-IN"])
    
    while True:
        try:
            choice = input(messages['prompt']).strip()
            if choice in ['1', '2', '3', '4']:
                return int(choice)
            else:
                error_messages = {
                    "en-IN": "❌ Invalid choice. Please enter 1, 2, 3, or 4.",
                    "hi-IN": "❌ गलत विकल्प। कृपया 1, 2, 3, या 4 दर्ज करें।",
                    "bn-IN": "❌ ভুল পছন্দ। অনুগ্রহ করে 1, 2, 3, বা 4 লিখুন।",
                    "bho-IN": "❌ गलत विकल्प। कृपया 1, 2, 3, या 4 दर्ज करीं।"
                }
                error_msg = error_messages.get(lang_code, error_messages["en-IN"])
                print(error_msg)
        except KeyboardInterrupt:
            goodbye_messages = {
                "en-IN": "\n👋 Goodbye!",
                "hi-IN": "\n👋 अलविदा!",
                "bn-IN": "\n👋 বিদায়!",
                "bho-IN": "\n👋 अलविदा!"
            }
            goodbye_msg = goodbye_messages.get(lang_code, goodbye_messages["en-IN"])
            print(goodbye_msg)
            return 4
        except Exception:
            error_messages = {
                "en-IN": "❌ Invalid input. Please enter a number.",
                "hi-IN": "❌ गलत इनपुट। कृपया एक संख्या दर्ज करें।",
                "bn-IN": "❌ ভুল ইনপুট। অনুগ্রহ করে একটি সংখ্যা লিখুন।",
                "bho-IN": "❌ गलत इनपुट। कृपया एगो नंबर दर्ज करीं।"
            }
            error_msg = error_messages.get(lang_code, error_messages["en-IN"])
            print(error_msg)

def main():
    """Main application entry point with multilingual support"""
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
    
    # Language selection first
    print_language_selection()
    language_choice = get_language_choice()
    
    if language_choice is None:
        return 1
    
    language_config = get_language_config(language_choice)
    
    # Clear screen and show selected language
    import os
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print("=" * 70)
    print("🌍 NPCL Multilingual Voice Assistant")
    print("🎆 Powered by Gemini 1.5 Flash")
    print(f"{language_config['flag']} Selected Language: {language_config['native']}")
    print("=" * 70)
    
    print("\n🎆 NPCL Features:")
    print("• Handles power connection inquiries")
    print("• Manages complaint numbers and status")
    print(f"• {language_config['native']} conversation style")
    print("• Real-time voice or text interaction")
    print("• Professional customer service experience")
    print("• 🆆 Offline mode available when quota exceeded")
    
    # Show mode options in selected language
    while True:
        print_mode_options(language_config)
        choice = get_user_choice(language_config)
        
        if choice == 4:  # Exit
            goodbye_messages = {
                "en-IN": "👋 Thank you for using NPCL Voice Assistant!",
                "hi-IN": "👋 एनपीसीएल वॉयस असिस्टेंट का उपयोग करने के लिए धन्यवाद!",
                "bn-IN": "👋 এনপিসিএল ভয়েস অ্যাসিস্ট্যান্ট ব্যবহার করার জন্য ধন্যবাদ!",
                "bho-IN": "👋 एनपीसीएल वॉयस असिस्टेंट के उपयोग करे खातिर धन्यवाद!"
            }
            goodbye_msg = goodbye_messages.get(language_config["code"], goodbye_messages["en-IN"])
            print(goodbye_msg)
            break
        
        try:
            if choice == 1:  # Chat Mode
                try:
                    start_multilingual_chat_mode(api_key, language_config)
                except Exception as e:
                    if "quota" in str(e).lower() or "429" in str(e):
                        print("⚠️  API quota exceeded. Starting offline mode...")
                        start_offline_mode(language_config)
                    else:
                        raise e
            elif choice == 2:  # Voice Mode
                try:
                    # Use enhanced voice mode with speech recognition
                    from voice_assistant.modes.voice_mode import start_enhanced_voice_mode
                    start_enhanced_voice_mode(api_key, language_config)
                except ImportError:
                    print("⚠️  Enhanced voice mode not available. Using basic voice mode...")
                    print("🎤 Voice Mode (Enhanced Chat with Voice Output)")
                    start_multilingual_chat_mode(api_key, language_config)
                except Exception as e:
                    if "quota" in str(e).lower() or "429" in str(e):
                        print("⚠️  API quota exceeded. Starting offline mode...")
                        start_offline_mode(language_config)
                    else:
                        raise e
            elif choice == 3:  # Combined Mode
                try:
                    print("🎭 Combined Mode (Enhanced Chat with Voice)")
                    start_multilingual_chat_mode(api_key, language_config)
                except Exception as e:
                    if "quota" in str(e).lower() or "429" in str(e):
                        print("⚠️  API quota exceeded. Starting offline mode...")
                        start_offline_mode(language_config)
                    else:
                        raise e
                
        except KeyboardInterrupt:
            print("\n👋 Session interrupted by user")
        except Exception as e:
            print(f"❌ Error: {e}")
            print("🔄 Falling back to offline mode...")
            start_offline_mode(language_config)
        
        # Ask if user wants to try another mode
        try:
            again_messages = {
                "en-IN": "\nWould you like to try another mode? (y/n): ",
                "hi-IN": "\nक्या आप कोई और मोड आज़माना चाहते हैं? (y/n): ",
                "bn-IN": "\nআপনি কি অন্য কোন মোড চেষ্টা করতে চান? (y/n): ",
                "bho-IN": "\nका रउआ कवनो आउर मोड आजमाना चाहत बानी? (y/n): "
            }
            again_msg = again_messages.get(language_config["code"], again_messages["en-IN"])
            again = input(again_msg).strip().lower()
            if again not in ['y', 'yes', 'हां', 'হ্যাঁ', 'ναι']:
                break
        except KeyboardInterrupt:
            break
    
    goodbye_messages = {
        "en-IN": "👋 Thank you for using NPCL Voice Assistant!",
        "hi-IN": "👋 एनपीसीएल वॉयस असिस्टेंट का उपयोग करने के लिए धन्यवाद!",
        "bn-IN": "👋 এনপিসিএল ভয়েস অ্যাসিস্ট্যান্ট ব্যবহার করার জন্য ধন্যবাদ!",
        "bho-IN": "👋 एनपीसीएल वॉयस असिस्टेंट के उपयोग करे खातिर धन्यवाद!"
    }
    goodbye_msg = goodbye_messages.get(language_config["code"], goodbye_messages["en-IN"])
    print(goodbye_msg)
    return 0

if __name__ == "__main__":
    sys.exit(main())