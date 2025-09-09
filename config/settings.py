"""
Configuration settings for Voice Assistant with Gemini 2.5 Flash and Real-time Live API
"""

import os
from typing import Optional
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, model_validator, ValidationError, AliasChoices


class VoiceAssistantSettings(BaseSettings):
    """Main configuration settings"""
    
    def __init__(self, **kwargs):
        """Initialize settings with validation"""
        # Check if API key is provided before calling parent init
        api_key = kwargs.get('google_api_key') or os.environ.get('GOOGLE_API_KEY')
        
        # If no API key in kwargs or env, check .env file
        if not api_key:
            env_file = Path('.env')
            if env_file.exists():
                # Read .env file manually to check for API key
                with open(env_file, 'r') as f:
                    for line in f:
                        if line.strip().startswith('GOOGLE_API_KEY='):
                            api_key = line.split('=', 1)[1].strip()
                            break
        
        # Validate API key before proceeding
        if not api_key or api_key == "your-google-api-key-here" or api_key.strip() == "":
            raise ValueError("Google API key is required and cannot be empty or placeholder")
        
        super().__init__(**kwargs)
    
    # API Keys
    google_api_key: str = Field(..., validation_alias=AliasChoices("GOOGLE_API_KEY"), description="Google API key is required")
    
    @field_validator('google_api_key', mode='before')
    @classmethod
    def validate_google_api_key(cls, v):
        if v is None or v == "" or v == "your-google-api-key-here" or (isinstance(v, str) and len(v.strip()) == 0):
            raise ValueError("Google API key is required and cannot be empty or placeholder")
        return v
    
    # AI Settings
    gemini_model: str = Field(default="gemini-2.5-flash", validation_alias=AliasChoices("GEMINI_MODEL"))
    gemini_live_model: str = Field(default="gemini-2.0-flash-exp", validation_alias=AliasChoices("GEMINI_LIVE_MODEL"))
    gemini_voice: str = Field(default="Puck", validation_alias=AliasChoices("GEMINI_VOICE"))  # Puck, Charon, Kore, Fenrir
    gemini_live_api_endpoint: str = Field(
        default="wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent",
        validation_alias=AliasChoices("GEMINI_LIVE_API_ENDPOINT")
    )
    max_tokens: int = Field(default=150, validation_alias=AliasChoices("MAX_TOKENS"))
    temperature: float = Field(default=0.7, validation_alias=AliasChoices("TEMPERATURE"))
    
    # Real-time Audio Settings
    audio_sample_rate: int = Field(default=16000, validation_alias=AliasChoices("AUDIO_SAMPLE_RATE"))
    audio_chunk_size: int = Field(default=320, validation_alias=AliasChoices("AUDIO_CHUNK_SIZE"))  # 20ms at 16kHz
    audio_buffer_size: int = Field(default=1600, validation_alias=AliasChoices("AUDIO_BUFFER_SIZE"))  # 100ms buffer
    audio_format: str = Field(default="slin16", validation_alias=AliasChoices("AUDIO_FORMAT"))  # slin16 for Asterisk
    audio_channels: int = Field(default=1, validation_alias=AliasChoices("AUDIO_CHANNELS"))  # Mono
    audio_sample_width: int = Field(default=2, validation_alias=AliasChoices("AUDIO_SAMPLE_WIDTH"))  # 16-bit
    
    # Voice Activity Detection
    vad_energy_threshold: int = Field(default=300, validation_alias=AliasChoices("VAD_ENERGY_THRESHOLD"))
    vad_silence_threshold: float = Field(default=0.5, validation_alias=AliasChoices("VAD_SILENCE_THRESHOLD"))
    vad_speech_threshold: float = Field(default=0.1, validation_alias=AliasChoices("VAD_SPEECH_THRESHOLD"))
    
    # Voice Settings
    voice_language: str = Field(default="en", validation_alias=AliasChoices("VOICE_LANGUAGE"))
    speech_rate: int = Field(default=150, validation_alias=AliasChoices("SPEECH_RATE"))
    voice_volume: float = Field(default=0.9, validation_alias=AliasChoices("VOICE_VOLUME"))
    
    # Timeout Settings
    listen_timeout: float = Field(default=20.0, validation_alias=AliasChoices("LISTEN_TIMEOUT"))
    phrase_time_limit: float = Field(default=15.0, validation_alias=AliasChoices("PHRASE_TIME_LIMIT"))
    max_retries: int = Field(default=3, validation_alias=AliasChoices("MAX_RETRIES"))
    
    # Assistant Settings
    assistant_name: str = Field(default="ARI", validation_alias=AliasChoices("ASSISTANT_NAME"))
    company_name: str = Field(default="Voice Assistant Corp", validation_alias=AliasChoices("COMPANY_NAME"))
    
    # Telephony Settings (ARI)
    ari_base_url: str = Field(default="http://localhost:8088/ari", validation_alias=AliasChoices("ARI_BASE_URL"))
    ari_username: str = Field(default="asterisk", validation_alias=AliasChoices("ARI_USERNAME"))
    ari_password: str = Field(default="1234", validation_alias=AliasChoices("ARI_PASSWORD"))
    stasis_app: str = Field(default="gemini-voice-assistant", validation_alias=AliasChoices("STASIS_APP"))
    
    # External Media Settings
    external_media_host: str = Field(default="localhost", validation_alias=AliasChoices("EXTERNAL_MEDIA_HOST"))
    external_media_port: int = Field(default=8090, validation_alias=AliasChoices("EXTERNAL_MEDIA_PORT"))
    
    # Real-time Processing Settings
    enable_interruption_handling: bool = Field(default=True, validation_alias=AliasChoices("ENABLE_INTERRUPTION_HANDLING"))
    max_call_duration: int = Field(default=3600, validation_alias=AliasChoices("MAX_CALL_DURATION"))  # 1 hour
    auto_answer_calls: bool = Field(default=True, validation_alias=AliasChoices("AUTO_ANSWER_CALLS"))
    enable_call_recording: bool = Field(default=False, validation_alias=AliasChoices("ENABLE_CALL_RECORDING"))
    
    # Performance Settings
    enable_performance_logging: bool = Field(default=False, validation_alias=AliasChoices("ENABLE_PERFORMANCE_LOGGING"))
    session_cleanup_interval: int = Field(default=300, validation_alias=AliasChoices("SESSION_CLEANUP_INTERVAL"))  # 5 minutes
    
    # Directories
    sounds_dir: str = Field(default="sounds", validation_alias=AliasChoices("SOUNDS_DIR"))
    temp_audio_dir: str = Field(default="sounds/temp", validation_alias=AliasChoices("TEMP_AUDIO_DIR"))
    recordings_dir: str = Field(default="recordings", validation_alias=AliasChoices("RECORDINGS_DIR"))
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        validate_assignment=True
    )


class LoggingSettings(BaseSettings):
    """Logging configuration"""
    
    log_level: str = Field(default="INFO", validation_alias=AliasChoices("LOG_LEVEL"))
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        validation_alias=AliasChoices("LOG_FORMAT")
    )
    log_file: Optional[str] = Field(default=None, validation_alias=AliasChoices("LOG_FILE"))
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


# Global settings instances (lazy initialization)
_settings = None
_logging_settings = None


def get_settings() -> VoiceAssistantSettings:
    """Get the global settings instance"""
    global _settings
    if _settings is None:
        _settings = VoiceAssistantSettings()
    return _settings


def get_logging_settings() -> LoggingSettings:
    """Get the logging settings instance"""
    global _logging_settings
    if _logging_settings is None:
        _logging_settings = LoggingSettings()
    return _logging_settings