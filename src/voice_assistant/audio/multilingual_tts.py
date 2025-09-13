"""
Enhanced Text-to-Speech with multi-language support for NPCL Voice Assistant
Supports all Indian regional languages plus Bhojpuri and English
"""

import logging
import tempfile
import os
from typing import Optional, Dict, List
from pathlib import Path
import pygame
from gtts import gTTS

from ..i18n.language_manager import LanguageManager, SupportedLanguage

logger = logging.getLogger(__name__)

class MultilingualTTS:
    """Enhanced Text-to-Speech with multi-language support"""
    
    def __init__(self, language_manager: LanguageManager):
        self.language_manager = language_manager
        self.temp_dir = Path(tempfile.gettempdir()) / "npcl_voice_assistant"
        self.temp_dir.mkdir(exist_ok=True)
        
        # Initialize pygame mixer for audio playback
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            self.audio_initialized = True
            logger.info("Audio system initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize audio system: {e}")
            self.audio_initialized = False
        
        # Language-specific TTS configurations
        self.tts_configs = {
            SupportedLanguage.ENGLISH: {"lang": "en", "tld": "co.in", "slow": False},
            SupportedLanguage.HINDI: {"lang": "hi", "tld": "co.in", "slow": False},
            SupportedLanguage.BENGALI: {"lang": "bn", "tld": "com", "slow": False},
            SupportedLanguage.TELUGU: {"lang": "te", "tld": "com", "slow": False},
            SupportedLanguage.MARATHI: {"lang": "mr", "tld": "com", "slow": False},
            SupportedLanguage.TAMIL: {"lang": "ta", "tld": "com", "slow": False},
            SupportedLanguage.GUJARATI: {"lang": "gu", "tld": "com", "slow": False},
            SupportedLanguage.URDU: {"lang": "ur", "tld": "com", "slow": False},
            SupportedLanguage.KANNADA: {"lang": "kn", "tld": "com", "slow": False},
            SupportedLanguage.ODIA: {"lang": "or", "tld": "com", "slow": False},
            SupportedLanguage.MALAYALAM: {"lang": "ml", "tld": "com", "slow": False},
            SupportedLanguage.BHOJPURI: {"lang": "hi", "tld": "co.in", "slow": False},
        }
        
        # Voice settings
        self.default_speed = "normal"
        self.default_volume = 1.0
        
        logger.info(f"MultilingualTTS initialized with {len(self.tts_configs)} languages")
    
    def speak(self, text: str, language: Optional[SupportedLanguage] = None, 
              voice_speed: str = "normal", volume: float = 1.0) -> bool:
        """Convert text to speech and play it"""
        if not self.audio_initialized:
            logger.error("Audio system not initialized")
            return False
        
        try:
            if language is None:
                language = self.language_manager.current_language
            
            if not language.voice_support:
                logger.warning(f"Voice support not available for {language.english_name}")
                return False
            
            if not text.strip():
                logger.warning("Empty text provided for TTS")
                return False
            
            # Get TTS configuration for the language
            tts_config = self.tts_configs.get(language)
            if not tts_config:
                logger.error(f"TTS configuration not found for {language.english_name}")
                return False
            
            # Adjust speed based on voice_speed parameter
            slow = voice_speed == "slow"
            
            logger.info(f"Generating speech in {language.english_name}: {text[:50]}...")
            
            # Generate speech
            tts = gTTS(
                text=text,
                lang=tts_config["lang"],
                tld=tts_config["tld"],
                slow=slow
            )
            
            # Save to temporary file
            temp_file = self.temp_dir / f"tts_{language.iso_code}_{hash(text)}.mp3"
            tts.save(str(temp_file))
            
            # Set volume
            pygame.mixer.music.set_volume(min(max(volume, 0.0), 1.0))
            
            # Play the audio
            pygame.mixer.music.load(str(temp_file))
            pygame.mixer.music.play()
            
            # Wait for playback to complete
            while pygame.mixer.music.get_busy():
                pygame.time.wait(100)
            
            # Clean up temporary file
            try:
                temp_file.unlink()
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temp file: {cleanup_error}")
            
            logger.info(f"Successfully spoke text in {language.english_name}")
            return True
            
        except Exception as e:
            logger.error(f"TTS error for {language.english_name if language else 'unknown'}: {e}")
            return False
    
    def speak_translation(self, key: str, namespace: str = "common", 
                         language: Optional[SupportedLanguage] = None, 
                         voice_speed: str = "normal", **kwargs) -> bool:
        """Speak a translated text"""
        text = self.language_manager.get_translation(key, namespace, language, **kwargs)
        return self.speak(text, language, voice_speed)
    
    def speak_npcl_greeting(self, language: Optional[SupportedLanguage] = None) -> bool:
        """Speak NPCL-specific greeting"""
        return self.speak_translation("npcl_greeting", "npcl_specific", language)
    
    def get_available_voices(self, language: Optional[SupportedLanguage] = None) -> List[Dict[str, str]]:
        """Get available voices for a language"""
        if language is None:
            language = self.language_manager.current_language
        
        # For gTTS, we return the available TLD options
        tts_config = self.tts_configs.get(language, {})
        
        return [{
            "id": f"{tts_config.get('lang', 'en')}_{tts_config.get('tld', 'com')}",
            "name": f"{language.english_name} Voice",
            "language": language.code,
            "gender": "neutral",  # gTTS doesn't specify gender
            "quality": "standard",
            "provider": "Google TTS"
        }]
    
    def test_language_voice(self, language: SupportedLanguage) -> bool:
        """Test if voice is available for a language"""
        test_text = self.language_manager.get_translation(
            "voice_test", "voice_prompts", language
        )
        if not test_text or test_text == "voice_test":
            # Fallback test text
            test_texts = {
                SupportedLanguage.ENGLISH: "This is a voice test in English",
                SupportedLanguage.HINDI: "यह हिंदी में एक आवाज परीक्षण है",
                SupportedLanguage.BENGALI: "এটি বাংলায় একটি কণ্ঠস্বর পরীক্ষা",
                SupportedLanguage.TELUGU: "ఇది తెలుగులో వాయిస్ టెస్ట్",
                SupportedLanguage.MARATHI: "हे मराठीत आवाज चाचणी आहे",
                SupportedLanguage.TAMIL: "இது தமிழில் குரல் சோதனை",
                SupportedLanguage.GUJARATI: "આ ગુજરાતીમાં અવાજ પરીક્ષણ છે",
                SupportedLanguage.URDU: "یہ اردو میں آواز کا ٹیسٹ ہے",
                SupportedLanguage.KANNADA: "ಇದು ಕನ್ನಡದಲ್ಲಿ ಧ್ವನಿ ಪರೀಕ್ಷೆ",
                SupportedLanguage.ODIA: "ଏହା ଓଡ଼ିଆରେ ସ୍ୱର ପରୀକ୍ଷା",
                SupportedLanguage.MALAYALAM: "ഇത് മലയാളത്തിൽ ശബ്ദ പരിശോധന",
                SupportedLanguage.BHOJPURI: "ई भोजपुरी में एगो आवाज परीक्षण बा"
            }
            test_text = test_texts.get(language, "Voice test")
        
        return self.speak(test_text, language)
    
    def set_voice_settings(self, speed: str = "normal", volume: float = 1.0):
        """Set default voice settings"""
        self.default_speed = speed
        self.default_volume = min(max(volume, 0.0), 1.0)
        logger.info(f"Voice settings updated: speed={speed}, volume={volume}")
    
    def get_supported_languages(self) -> List[Dict[str, any]]:
        """Get list of supported languages for TTS"""
        supported = []
        for language in SupportedLanguage:
            if language.voice_support and language in self.tts_configs:
                config = self.tts_configs[language]
                supported.append({
                    "code": language.code,
                    "iso_code": language.iso_code,
                    "name": language.english_name,
                    "native_name": language.native_name,
                    "direction": language.direction,
                    "script": language.script,
                    "flag": language.flag,
                    "tts_lang": config["lang"],
                    "tts_tld": config["tld"]
                })
        return supported
    
    def is_language_supported(self, language_code: str) -> bool:
        """Check if a language is supported for TTS"""
        language = self.language_manager.get_language_by_code(language_code)
        return language is not None and language in self.tts_configs
    
    def cleanup_temp_files(self):
        """Clean up temporary audio files"""
        try:
            for file in self.temp_dir.glob("tts_*.mp3"):
                file.unlink()
            logger.info("Cleaned up temporary TTS files")
        except Exception as e:
            logger.warning(f"Error cleaning up temp files: {e}")
    
    def stop_speaking(self):
        """Stop current speech playback"""
        if self.audio_initialized:
            try:
                pygame.mixer.music.stop()
                logger.debug("Stopped current speech playback")
            except Exception as e:
                logger.warning(f"Error stopping speech: {e}")
    
    def is_speaking(self) -> bool:
        """Check if currently speaking"""
        if self.audio_initialized:
            return pygame.mixer.music.get_busy()
        return False
    
    def get_voice_statistics(self) -> Dict[str, any]:
        """Get TTS statistics"""
        return {
            "audio_initialized": self.audio_initialized,
            "supported_languages": len(self.tts_configs),
            "temp_files": len(list(self.temp_dir.glob("tts_*.mp3"))),
            "current_language": self.language_manager.current_language.english_name,
            "default_settings": {
                "speed": self.default_speed,
                "volume": self.default_volume
            },
            "is_speaking": self.is_speaking()
        }
    
    def __del__(self):
        """Cleanup on destruction"""
        try:
            self.cleanup_temp_files()
        except:
            pass