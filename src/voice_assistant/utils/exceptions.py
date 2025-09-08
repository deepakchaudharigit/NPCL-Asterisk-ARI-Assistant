"""
Custom exceptions for voice assistant
"""


class VoiceAssistantError(Exception):
    """Base exception for voice assistant"""
    pass


class AudioError(VoiceAssistantError):
    """Audio processing related errors"""
    pass


class SpeechRecognitionError(AudioError):
    """Speech recognition specific errors"""
    pass


class TextToSpeechError(AudioError):
    """Text-to-speech specific errors"""
    pass


class AIError(VoiceAssistantError):
    """AI/LLM related errors"""
    pass


class GeminiError(AIError):
    """Gemini API specific errors"""
    pass


class ConfigurationError(VoiceAssistantError):
    """Configuration related errors"""
    pass


class TelephonyError(VoiceAssistantError):
    """Telephony/ARI related errors"""
    pass


class MicrophoneError(AudioError):
    """Microphone related errors"""
    pass