"""
Voice Assistant Audio Package
Contains audio processing modules for speech recognition and text-to-speech.
"""

try:
    from .enhanced_tts import speak_text_enhanced
except ImportError:
    speak_text_enhanced = None

try:
    from .voice_input import VoiceInputHandler
except ImportError:
    VoiceInputHandler = None

__all__ = ['speak_text_enhanced', 'VoiceInputHandler']