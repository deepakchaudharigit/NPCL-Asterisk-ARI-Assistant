"""
Internationalization (i18n) module for NPCL Voice Assistant
Provides multi-language support for voice and chat interfaces
"""

from .language_manager import LanguageManager, SupportedLanguage
from .translator import Translator
from .language_detector import LanguageDetector

__all__ = [
    'LanguageManager',
    'SupportedLanguage', 
    'Translator',
    'LanguageDetector'
]