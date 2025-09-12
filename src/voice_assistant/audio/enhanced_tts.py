#!/usr/bin/env python3
"""
Enhanced Text-to-Speech module with Google TTS integration and multiple fallbacks.
Provides high-quality multilingual speech synthesis with automatic fallback mechanisms.
"""

import os
import re
import tempfile
import time
from typing import Optional

# Suppress pygame welcome message globally
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'


def clean_text_for_tts(text: str, language_code: str = "en-IN") -> str:
    """Clean and prepare text for TTS to handle special characters and multilingual content"""
    
    # Remove or replace problematic characters
    cleaned_text = text
    
    # Replace common problematic characters
    replacements = {
        '/': ' ',  # Replace slash with space
        '\n': ' ',  # Replace newlines with space
        '\t': ' ',  # Replace tabs with space
        '  ': ' ',  # Replace double spaces with single space
        '।': '.',   # Replace Hindi full stop with English period
        '॥': '.',   # Replace double danda with period
        '?': '.',   # Replace question marks that might cause issues
        '!': '.',   # Replace exclamation marks
        '"': '',    # Remove quotes
        "'": '',    # Remove apostrophes
        '(': '',    # Remove parentheses
        ')': '',
        '[': '',    # Remove brackets
        ']': '',
        '{': '',    # Remove braces
        '}': '',
        '*': '',    # Remove asterisks
        '#': '',    # Remove hash symbols
        '@': '',    # Remove at symbols
        '$': '',    # Remove dollar signs
        '%': '',    # Remove percent signs
        '^': '',    # Remove caret
        '&': ' और ',  # Replace & with Hindi 'and' for Hindi text
        '+': ' प्लस ',  # Replace + with Hindi 'plus'
        '=': ' बराबर ',  # Replace = with Hindi 'equals'
        '<': '',    # Remove less than
        '>': '',    # Remove greater than
        '|': '',    # Remove pipe
        '\\': '',   # Remove backslash
        '~': '',    # Remove tilde
        '`': '',    # Remove backtick
    }
    
    # Apply replacements
    for old, new in replacements.items():
        cleaned_text = cleaned_text.replace(old, new)
    
    # For Hindi text, handle specific issues
    if language_code == "hi-IN":
        # Replace English words that might be mixed in
        english_replacements = {
            'NPCL': 'एनपीसीएल',
            'Limited': 'लिमिटेड',
            'Corporation': 'कॉर्पोरेशन',
            'Power': 'पावर',
            'Noida': 'नोएडा',
        }
        
        for eng, hindi in english_replacements.items():
            cleaned_text = cleaned_text.replace(eng, hindi)
    
    # Clean up multiple spaces
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
    cleaned_text = cleaned_text.strip()
    
    return cleaned_text


def speak_with_gtts(text: str, language_code: str = "en-IN") -> bool:
    """Try to use Google TTS for better multilingual support"""
    try:
        from gtts import gTTS
        import pygame
        import time
        
        # Clean text for TTS
        cleaned_text = clean_text_for_tts(text, language_code)
        
        # Skip if text is too short or empty
        if not cleaned_text or len(cleaned_text.strip()) < 2:
            return False
        
        # Map language codes to gTTS language codes
        gtts_lang_map = {
            "en-IN": "en",
            "hi-IN": "hi",
            "bn-IN": "bn",
            "te-IN": "te",
            "mr-IN": "mr",
            "ta-IN": "ta",
            "gu-IN": "gu",
            "ur-IN": "ur",
            "kn-IN": "kn",
            "or-IN": "or",
            "ml-IN": "ml",
            "el-GR": "el"
        }
        
        gtts_lang = gtts_lang_map.get(language_code, "en")
        
        # Create TTS object
        tts = gTTS(text=cleaned_text, lang=gtts_lang, slow=False)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
            temp_path = temp_file.name
        
        try:
            # Save TTS to file
            tts.save(temp_path)
            
            # Wait a moment for file to be written
            time.sleep(0.1)
            
            # Verify file exists and has content
            if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
                raise Exception("TTS file creation failed")
            
            # Initialize pygame mixer with better settings (suppress output)
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=512)
                pygame.mixer.init()
            
            # Load and play the audio
            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.play()
            
            # Wait for playback to complete with timeout
            timeout = 30  # Maximum 30 seconds
            start_time = time.time()
            
            while pygame.mixer.music.get_busy():
                if time.time() - start_time > timeout:
                    pygame.mixer.music.stop()
                    break
                time.sleep(0.1)
            
            return True
            
        finally:
            # Always cleanup the temp file
            try:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            except:
                pass
        
    except ImportError:
        # gTTS or pygame not available
        return False
    except Exception as e:
        return False


def speak_with_pyttsx3(text: str, language_code: str = "en-IN") -> bool:
    """Fallback TTS using pyttsx3 with enhanced text cleaning"""
    try:
        import pyttsx3
        
        # Clean text for better pronunciation
        cleaned_text = clean_text_for_tts(text, language_code)
        
        # Skip if text is too short or empty
        if not cleaned_text or len(cleaned_text.strip()) < 2:
            return False
        
        # For Hindi, do additional transliteration to help pronunciation
        if language_code == "hi-IN":
            # Convert some common Hindi words to phonetic equivalents
            hindi_phonetic = {
                'नमस्ते': 'namaste',
                'धन्यवाद': 'dhanyawad',
                'कृपया': 'kripaya',
                'सर': 'sir',
                'मैडम': 'madam',
                'एनपीसीएल': 'N P C L',
                'नोएडा': 'noida',
                'पावर': 'power',
                'कॉर्पोरेशन': 'corporation',
                'लिमिटेड': 'limited',
                'ग्राहक': 'grahak',
                'सेवा': 'seva',
                'सहायता': 'sahayata',
                'समस्या': 'samasya',
                'शिकायत': 'shikayat',
                'कनेक्शन': 'connection',
                'बिजली': 'bijli',
                'समाधान': 'samadhan'
            }
            
            # Apply phonetic replacements for better pronunciation
            for hindi, phonetic in hindi_phonetic.items():
                cleaned_text = cleaned_text.replace(hindi, phonetic)
        
        # Reinitialize engine for each call (Windows fix)
        engine = pyttsx3.init()
        
        # Configure engine for better speech
        engine.setProperty('rate', 100)  # Even slower for Hindi
        engine.setProperty('volume', 1.0)
        
        # Set voice if available
        voices = engine.getProperty('voices')
        if voices:
            # Try to find the best voice for the language
            best_voice = None
            
            # For Hindi, try to find Hindi voice or good English voice
            if language_code == "hi-IN":
                # First try to find Hindi voice
                for voice in voices:
                    if any(keyword in voice.name.lower() for keyword in ['hindi', 'india']):
                        best_voice = voice.id
                        break
                
                # If no Hindi voice, try Zira (good for Indian pronunciation)
                if not best_voice:
                    for voice in voices:
                        if 'zira' in voice.name.lower():
                            best_voice = voice.id
                            break
            
            # If no specific voice found, use default logic
            if not best_voice:
                for voice in voices:
                    if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                        best_voice = voice.id
                        break
                else:
                    best_voice = voices[0].id
            
            engine.setProperty('voice', best_voice)
        
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
        return False


def speak_text_enhanced(text: str, language_code: str = "en-IN") -> bool:
    """Enhanced TTS function with multilingual support and text cleaning"""
    try:
        # Skip empty or very short text
        if not text or len(text.strip()) < 2:
            return False
        
        # First, try Google TTS for better multilingual support
        success = speak_with_gtts(text, language_code)
        if success:
            return True
        
        # Fallback to pyttsx3 with text cleaning
        success = speak_with_pyttsx3(text, language_code)
        if success:
            return True
        
        # Final fallback to simple TTS
        try:
            from .simple_tts import speak_text_simple
            return speak_text_simple(text, language_code)
        except ImportError:
            return False
        
    except Exception as e:
        return False


# For backward compatibility
def speak_text_robust(text: str, language_code: str = "en-IN") -> bool:
    """Backward compatible function name"""
    return speak_text_enhanced(text, language_code)