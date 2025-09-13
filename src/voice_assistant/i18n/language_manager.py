"""
Language Manager for NPCL Voice Assistant
Handles language settings, translations, and language-specific configurations
"""

from enum import Enum
from typing import Dict, List, Optional, Union
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class SupportedLanguage(Enum):
    """Supported languages with their codes and metadata"""
    ENGLISH = ("en-IN", "English", "English (India)", "ltr", "latin", True, True, "🇮🇳")
    HINDI = ("hi-IN", "हिन्दी", "Hindi", "ltr", "devanagari", True, True, "🇮🇳")
    BENGALI = ("bn-IN", "বাংলা", "Bengali", "ltr", "bengali", True, True, "🇮🇳")
    TELUGU = ("te-IN", "తెలుగు", "Telugu", "ltr", "telugu", True, True, "🇮🇳")
    MARATHI = ("mr-IN", "मराठी", "Marathi", "ltr", "devanagari", True, True, "🇮🇳")
    TAMIL = ("ta-IN", "தமிழ்", "Tamil", "ltr", "tamil", True, True, "🇮🇳")
    GUJARATI = ("gu-IN", "ગુજરાતી", "Gujarati", "ltr", "gujarati", True, True, "🇮🇳")
    URDU = ("ur-IN", "اردو", "Urdu", "rtl", "arabic", True, True, "🇮🇳")
    KANNADA = ("kn-IN", "ಕನ್ನಡ", "Kannada", "ltr", "kannada", True, True, "🇮🇳")
    ODIA = ("or-IN", "ଓଡ଼ିଆ", "Odia", "ltr", "odia", True, True, "🇮🇳")
    MALAYALAM = ("ml-IN", "മലയാളം", "Malayalam", "ltr", "malayalam", True, True, "🇮🇳")
    BHOJPURI = ("bho-IN", "भोजपुरी", "Bhojpuri", "ltr", "devanagari", True, True, "🇮🇳")
    
    def __init__(self, code: str, native_name: str, english_name: str, 
                 direction: str, script: str, voice_support: bool, chat_support: bool, flag: str):
        self.code = code
        self.native_name = native_name
        self.english_name = english_name
        self.direction = direction  # ltr or rtl
        self.script = script
        self.voice_support = voice_support
        self.chat_support = chat_support
        self.flag = flag
        self.iso_code = code.split('-')[0]  # e.g., 'hi' from 'hi-IN'
        self.country_code = code.split('-')[1] if '-' in code else None

class LanguageManager:
    """Manages language settings and translations"""
    
    def __init__(self, locales_path: str = "src/voice_assistant/i18n/locales"):
        self.locales_path = Path(locales_path)
        self.current_language = SupportedLanguage.ENGLISH
        self.fallback_language = SupportedLanguage.ENGLISH
        self._translations_cache: Dict[str, Dict[str, any]] = {}
        self._load_all_translations()
    
    def _load_all_translations(self):
        """Load all translation files into cache"""
        for language in SupportedLanguage:
            self._load_language_translations(language)
    
    def _load_language_translations(self, language: SupportedLanguage):
        """Load translations for a specific language"""
        lang_dir = self.locales_path / language.code
        if not lang_dir.exists():
            logger.warning(f"Translation directory not found for {language.english_name}: {lang_dir}")
            return
        
        translations = {}
        for json_file in lang_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    namespace = json_file.stem
                    translations[namespace] = json.load(f)
                    logger.debug(f"Loaded {namespace} translations for {language.english_name}")
            except Exception as e:
                logger.error(f"Error loading translation file {json_file}: {e}")
        
        self._translations_cache[language.code] = translations
        logger.info(f"Loaded translations for {language.english_name}")
    
    def set_language(self, language_code: str) -> bool:
        """Set the current language"""
        language = self.get_language_by_code(language_code)
        if language:
            old_language = self.current_language
            self.current_language = language
            logger.info(f"Language changed from {old_language.english_name} to {language.english_name}")
            return True
        logger.warning(f"Language code not supported: {language_code}")
        return False
    
    def get_language_by_code(self, code: str) -> Optional[SupportedLanguage]:
        """Get language enum by code"""
        for lang in SupportedLanguage:
            if lang.code == code or lang.iso_code == code:
                return lang
        return None
    
    def get_translation(self, key: str, namespace: str = "common", 
                       language: Optional[SupportedLanguage] = None, 
                       **kwargs) -> str:
        """Get translation for a key"""
        if language is None:
            language = self.current_language
        
        # Try current language
        translation = self._get_translation_from_cache(key, namespace, language)
        
        # Fallback to English if not found
        if translation is None and language != self.fallback_language:
            translation = self._get_translation_from_cache(key, namespace, self.fallback_language)
            logger.debug(f"Using fallback translation for key: {key}")
        
        # Final fallback to key itself
        if translation is None:
            translation = key
            logger.warning(f"Translation not found for key: {key} in namespace: {namespace}")
        
        # Format with kwargs if provided
        if kwargs:
            try:
                translation = translation.format(**kwargs)
            except (KeyError, ValueError) as e:
                logger.warning(f"Error formatting translation for key {key}: {e}")
        
        return translation
    
    def _get_translation_from_cache(self, key: str, namespace: str, 
                                   language: SupportedLanguage) -> Optional[str]:
        """Get translation from cache"""
        lang_translations = self._translations_cache.get(language.code, {})
        namespace_translations = lang_translations.get(namespace, {})
        
        # Support nested keys like "errors.validation.required"
        keys = key.split('.')
        value = namespace_translations
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return None
        
        return value if isinstance(value, str) else None
    
    def get_supported_languages(self, voice_only: bool = False, 
                               chat_only: bool = False) -> List[SupportedLanguage]:
        """Get list of supported languages"""
        languages = []
        for lang in SupportedLanguage:
            if voice_only and not lang.voice_support:
                continue
            if chat_only and not lang.chat_support:
                continue
            languages.append(lang)
        return languages
    
    def detect_language_from_text(self, text: str) -> Optional[SupportedLanguage]:
        """Detect language from text (basic implementation)"""
        if not text.strip():
            return None
        
        # Check for specific script patterns
        if any('\\u0900' <= char <= '\\u097F' for char in text):  # Devanagari
            # Could be Hindi, Marathi, or Bhojpuri, check for specific words
            bhojpuri_words = ['बा', 'बानी', 'बाटे', 'करेला', 'होखे', 'रहल', 'जाला', 'रउआ', 'हमार', 'तोहार']
            marathi_words = ['आहे', 'आहेत', 'चा', 'ची', 'चे', 'मध्ये', 'पासून', 'ला', 'आणि']
            hindi_words = ['है', 'हैं', 'का', 'की', 'के', 'में', 'से', 'को', 'और']
            
            if any(word in text for word in bhojpuri_words):
                return SupportedLanguage.BHOJPURI
            elif any(word in text for word in marathi_words):
                return SupportedLanguage.MARATHI
            return SupportedLanguage.HINDI
            
        elif any('\\u0980' <= char <= '\\u09FF' for char in text):  # Bengali
            return SupportedLanguage.BENGALI
        elif any('\\u0C00' <= char <= '\\u0C7F' for char in text):  # Telugu
            return SupportedLanguage.TELUGU
        elif any('\\u0B80' <= char <= '\\u0BFF' for char in text):  # Tamil
            return SupportedLanguage.TAMIL
        elif any('\\u0A80' <= char <= '\\u0AFF' for char in text):  # Gujarati
            return SupportedLanguage.GUJARATI
        elif any('\\u0600' <= char <= '\\u06FF' for char in text):  # Arabic (Urdu)
            return SupportedLanguage.URDU
        elif any('\\u0C80' <= char <= '\\u0CFF' for char in text):  # Kannada
            return SupportedLanguage.KANNADA
        elif any('\\u0B00' <= char <= '\\u0B7F' for char in text):  # Odia
            return SupportedLanguage.ODIA
        elif any('\\u0D00' <= char <= '\\u0D7F' for char in text):  # Malayalam
            return SupportedLanguage.MALAYALAM

        else:
            return SupportedLanguage.ENGLISH
    
    def get_language_info(self, language: Optional[SupportedLanguage] = None) -> Dict[str, any]:
        """Get comprehensive language information"""
        if language is None:
            language = self.current_language
        
        return {
            "code": language.code,
            "iso_code": language.iso_code,
            "country_code": language.country_code,
            "native_name": language.native_name,
            "english_name": language.english_name,
            "direction": language.direction,
            "script": language.script,
            "voice_support": language.voice_support,
            "chat_support": language.chat_support,
            "is_rtl": language.direction == "rtl",
            "flag": language.flag
        }
    
    def get_npcl_greeting(self, language: Optional[SupportedLanguage] = None) -> str:
        """Get NPCL-specific greeting in the specified language"""
        return self.get_translation("npcl_greeting", "npcl_specific", language)
    
    def get_voice_prompts(self, prompt_type: str, language: Optional[SupportedLanguage] = None) -> str:
        """Get voice-specific prompts"""
        return self.get_translation(prompt_type, "voice_prompts", language)
    
    def is_language_supported(self, language_code: str, voice: bool = False, chat: bool = False) -> bool:
        """Check if a language is supported for specific features"""
        language = self.get_language_by_code(language_code)
        if not language:
            return False
        
        if voice and not language.voice_support:
            return False
        if chat and not language.chat_support:
            return False
        
        return True
    
    def get_language_statistics(self) -> Dict[str, any]:
        """Get statistics about language support"""
        total_languages = len(SupportedLanguage)
        voice_supported = len([lang for lang in SupportedLanguage if lang.voice_support])
        chat_supported = len([lang for lang in SupportedLanguage if lang.chat_support])
        rtl_languages = len([lang for lang in SupportedLanguage if lang.direction == "rtl"])
        
        scripts = set(lang.script for lang in SupportedLanguage)
        
        return {
            "total_languages": total_languages,
            "voice_supported": voice_supported,
            "chat_supported": chat_supported,
            "rtl_languages": rtl_languages,
            "scripts_supported": list(scripts),
            "current_language": self.get_language_info()
        }