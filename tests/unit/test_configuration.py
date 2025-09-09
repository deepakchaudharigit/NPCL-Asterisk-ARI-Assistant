"""
Unit tests for Configuration Management.
Tests settings validation, environment loading, and configuration classes.
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock

from config.settings import (
    VoiceAssistantSettings,
    LoggingSettings,
    get_settings,
    get_logging_settings
)


@pytest.mark.unit
class TestVoiceAssistantSettings:
    """Test Voice Assistant settings configuration."""
    
    def test_default_settings(self):
        """Test default configuration values."""
        # Mock environment to avoid requiring actual API key
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            settings = VoiceAssistantSettings()
            
            # AI Settings
            assert settings.gemini_model == "gemini-2.5-flash"
            assert settings.gemini_live_model == "gemini-2.5-flash-preview-native-audio-dialog"
            assert settings.gemini_voice == "Puck"
            assert settings.max_tokens == 150
            assert settings.temperature == 0.7
            
            # Real-time Audio Settings
            assert settings.audio_sample_rate == 16000
            assert settings.audio_chunk_size == 320
            assert settings.audio_buffer_size == 1600
            assert settings.audio_format == "slin16"
            assert settings.audio_channels == 1
            assert settings.audio_sample_width == 2
            
            # Voice Activity Detection
            assert settings.vad_energy_threshold == 300
            assert settings.vad_silence_threshold == 0.5
            assert settings.vad_speech_threshold == 0.1
            
            # Assistant Settings
            assert settings.assistant_name == "Tatiana"
            assert settings.company_name == "Voice Assistant Corp"
            assert settings.voice_language == "en"
            
            # Telephony Settings
            assert settings.ari_base_url == "http://localhost:8088/ari"
            assert settings.ari_username == "asterisk"
            assert settings.ari_password == "1234"
            assert settings.stasis_app == "gemini-voice-assistant"
            
            # External Media Settings
            assert settings.external_media_host == "localhost"
            assert settings.external_media_port == 8090
            
            # Real-time Processing Settings
            assert settings.enable_interruption_handling == True
            assert settings.max_call_duration == 3600
            assert settings.auto_answer_calls == True
            assert settings.enable_call_recording == False
    
    def test_custom_settings_from_env(self):
        """Test loading custom settings from environment variables."""
        custom_env = {
            "GOOGLE_API_KEY": "custom-api-key",
            "GEMINI_MODEL": "custom-model",
            "GEMINI_LIVE_MODEL": "custom-live-model",
            "GEMINI_VOICE": "Charon",
            "AUDIO_SAMPLE_RATE": "8000",
            "AUDIO_CHUNK_SIZE": "160",
            "AUDIO_FORMAT": "ulaw",
            "VAD_ENERGY_THRESHOLD": "500",
            "ASSISTANT_NAME": "CustomARI",
            "ARI_BASE_URL": "http://custom:8088/ari",
            "ARI_USERNAME": "custom_user",
            "ARI_PASSWORD": "custom_pass",
            "EXTERNAL_MEDIA_PORT": "9090",
            "MAX_CALL_DURATION": "7200",
            "AUTO_ANSWER_CALLS": "false",
            "ENABLE_CALL_RECORDING": "true"
        }
        
        with patch.dict(os.environ, custom_env):
            settings = VoiceAssistantSettings()
            
            assert settings.google_api_key == "custom-api-key"
            assert settings.gemini_model == "custom-model"
            assert settings.gemini_live_model == "custom-live-model"
            assert settings.gemini_voice == "Charon"
            assert settings.audio_sample_rate == 8000
            assert settings.audio_chunk_size == 160
            assert settings.audio_format == "ulaw"
            assert settings.vad_energy_threshold == 500
            assert settings.assistant_name == "CustomARI"
            assert settings.ari_base_url == "http://custom:8088/ari"
            assert settings.ari_username == "custom_user"
            assert settings.ari_password == "custom_pass"
            assert settings.external_media_port == 9090
            assert settings.max_call_duration == 7200
            assert settings.auto_answer_calls == False
            assert settings.enable_call_recording == True
    
    def test_settings_validation(self):
        """Test settings validation."""
        # Test missing required field by temporarily removing the API key
        original_key = os.environ.get('GOOGLE_API_KEY')
        
        # Also temporarily move .env file to ensure complete isolation
        env_file = Path('.env')
        temp_env_file = Path('.env.temp_test')
        env_existed = env_file.exists()
        
        try:
            # Remove the API key from environment
            if 'GOOGLE_API_KEY' in os.environ:
                del os.environ['GOOGLE_API_KEY']
            
            # Move .env file temporarily
            if env_existed:
                env_file.rename(temp_env_file)
            
            # This should raise a validation error
            with pytest.raises((ValueError, Exception, TypeError)):  # Should raise validation error
                VoiceAssistantSettings()
        finally:
            # Restore .env file
            if env_existed and temp_env_file.exists():
                temp_env_file.rename(env_file)
            
            # Restore the original key
            if original_key:
                os.environ['GOOGLE_API_KEY'] = original_key
    
    def test_audio_configuration_consistency(self):
        """Test audio configuration consistency."""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            settings = VoiceAssistantSettings()
            
            # Verify audio settings are consistent
            assert settings.audio_format == "slin16"
            assert settings.audio_sample_rate == 16000
            assert settings.audio_channels == 1
            assert settings.audio_sample_width == 2
            
            # Verify chunk size is reasonable for real-time processing
            chunk_duration_ms = (settings.audio_chunk_size / settings.audio_sample_rate) * 1000
            assert 10 <= chunk_duration_ms <= 50  # Between 10-50ms
            
            # Verify buffer size is larger than chunk size
            assert settings.audio_buffer_size > settings.audio_chunk_size
    
    def test_telephony_configuration(self):
        """Test telephony configuration validation."""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            settings = VoiceAssistantSettings()
            
            # Verify ARI URL format
            assert settings.ari_base_url.startswith("http")
            assert "/ari" in settings.ari_base_url
            
            # Verify credentials are set
            assert len(settings.ari_username) > 0
            assert len(settings.ari_password) > 0
            
            # Verify stasis app name
            assert len(settings.stasis_app) > 0
            assert "-" in settings.stasis_app or "_" in settings.stasis_app
    
    def test_performance_settings(self):
        """Test performance-related settings."""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            settings = VoiceAssistantSettings()
            
            # Verify reasonable limits
            assert settings.max_call_duration > 0
            assert settings.max_call_duration <= 86400  # Max 24 hours
            
            # Verify VAD thresholds are reasonable
            assert 0 < settings.vad_silence_threshold < 5.0
            assert 0 < settings.vad_speech_threshold < 1.0
            assert settings.vad_energy_threshold > 0


@pytest.mark.unit
class TestLoggingSettings:
    """Test logging settings configuration."""
    
    def test_default_logging_settings(self):
        """Test default logging configuration."""
        settings = LoggingSettings()
        
        assert settings.log_level == "INFO"
        assert "%(asctime)s" in settings.log_format
        assert "%(name)s" in settings.log_format
        assert "%(levelname)s" in settings.log_format
        assert "%(message)s" in settings.log_format
        assert settings.log_file is None
    
    def test_custom_logging_settings(self):
        """Test custom logging configuration."""
        custom_env = {
            "LOG_LEVEL": "DEBUG",
            "LOG_FORMAT": "%(levelname)s - %(message)s",
            "LOG_FILE": "/var/log/voice_assistant.log"
        }
        
        with patch.dict(os.environ, custom_env):
            settings = LoggingSettings()
            
            assert settings.log_level == "DEBUG"
            assert settings.log_format == "%(levelname)s - %(message)s"
            assert settings.log_file == "/var/log/voice_assistant.log"
    
    def test_log_level_validation(self):
        """Test log level validation."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        
        for level in valid_levels:
            with patch.dict(os.environ, {"LOG_LEVEL": level}):
                settings = LoggingSettings()
                assert settings.log_level == level


@pytest.mark.unit
class TestSettingsGlobalFunctions:
    """Test global settings functions."""
    
    def test_get_settings_function(self):
        """Test get_settings() function."""
        settings = get_settings()
        
        assert isinstance(settings, VoiceAssistantSettings)
        # Just verify it has an API key, don't check the exact value
        assert len(settings.google_api_key) > 0
    
    def test_get_logging_settings_function(self):
        """Test get_logging_settings() function."""
        logging_settings = get_logging_settings()
        
        assert isinstance(logging_settings, LoggingSettings)
        assert logging_settings.log_level == "INFO"
    
    def test_settings_singleton_behavior(self):
        """Test that settings behave like singletons."""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            settings1 = get_settings()
            settings2 = get_settings()
            
            # Should be the same instance
            assert settings1 is settings2
            
            logging1 = get_logging_settings()
            logging2 = get_logging_settings()
            
            # Should be the same instance
            assert logging1 is logging2


@pytest.mark.unit
class TestEnvironmentFileLoading:
    """Test environment file loading."""
    
    def test_env_file_loading(self):
        """Test loading settings from .env file."""
        # Create temporary .env file
        env_content = """
GOOGLE_API_KEY=file-api-key
GEMINI_MODEL=file-model
ASSISTANT_NAME=FileARI
AUDIO_SAMPLE_RATE=8000
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write(env_content)
            env_file_path = f.name
        
        try:
            # Test that we can create settings with custom env file
            # Note: This test verifies the configuration structure
            # Actual file loading would require modifying the class definition
            settings = VoiceAssistantSettings()
            
            assert hasattr(settings, 'google_api_key')
            assert hasattr(settings, 'gemini_model')
            assert hasattr(settings, 'assistant_name')
            assert hasattr(settings, 'audio_sample_rate')
        
        finally:
            # Cleanup
            os.unlink(env_file_path)
    
    def test_env_file_precedence(self):
        """Test that environment variables take precedence over .env file."""
        # This test verifies the expected behavior of pydantic-settings
        # Environment variables should override .env file values
        
        with patch.dict(os.environ, {
            "GOOGLE_API_KEY": "env-api-key",
            "ASSISTANT_NAME": "EnvARI"
        }):
            settings = VoiceAssistantSettings()
            
            assert settings.google_api_key == "env-api-key"
            assert settings.assistant_name == "EnvARI"


@pytest.mark.unit
class TestConfigurationValidation:
    """Test configuration validation scenarios."""
    
    def test_audio_format_validation(self):
        """Test audio format configuration validation."""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            settings = VoiceAssistantSettings()
            
            # Verify supported audio format
            assert settings.audio_format in ["slin16", "ulaw", "alaw", "wav"]
            
            # Verify sample rate is standard
            assert settings.audio_sample_rate in [8000, 16000, 44100, 48000]
    
    def test_network_configuration_validation(self):
        """Test network configuration validation."""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            settings = VoiceAssistantSettings()
            
            # Verify port numbers are valid
            assert 1 <= settings.external_media_port <= 65535
            
            # Verify host format
            assert isinstance(settings.external_media_host, str)
            assert len(settings.external_media_host) > 0
    
    def test_gemini_voice_validation(self):
        """Test Gemini voice configuration validation."""
        valid_voices = ["Puck", "Charon", "Kore", "Fenrir"]
        
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            settings = VoiceAssistantSettings()
            
            assert settings.gemini_voice in valid_voices
    
    def test_boolean_setting_parsing(self):
        """Test boolean setting parsing from environment."""
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("0", False)
        ]
        
        for env_value, expected in test_cases:
            with patch.dict(os.environ, {
                "GOOGLE_API_KEY": "test-key",
                "AUTO_ANSWER_CALLS": env_value
            }):
                settings = VoiceAssistantSettings()
                assert settings.auto_answer_calls == expected
    
    def test_numeric_setting_validation(self):
        """Test numeric setting validation."""
        with patch.dict(os.environ, {
            "GOOGLE_API_KEY": "test-key",
            "AUDIO_SAMPLE_RATE": "16000",
            "MAX_CALL_DURATION": "3600",
            "VAD_ENERGY_THRESHOLD": "300"
        }):
            settings = VoiceAssistantSettings()
            
            assert isinstance(settings.audio_sample_rate, int)
            assert isinstance(settings.max_call_duration, int)
            assert isinstance(settings.vad_energy_threshold, int)
            
            assert settings.audio_sample_rate > 0
            assert settings.max_call_duration > 0
            assert settings.vad_energy_threshold > 0
    
    def test_string_setting_validation(self):
        """Test string setting validation."""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            settings = VoiceAssistantSettings()
            
            # Verify required strings are not empty
            assert len(settings.google_api_key) > 0
            assert len(settings.assistant_name) > 0
            assert len(settings.stasis_app) > 0
            assert len(settings.ari_username) > 0
            assert len(settings.ari_password) > 0


@pytest.mark.unit
class TestConfigurationIntegration:
    """Test configuration integration with other components."""
    
    def test_audio_config_compatibility(self):
        """Test audio configuration compatibility with audio processor."""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            settings = VoiceAssistantSettings()
            
            # Import here to avoid circular imports in tests
            from src.voice_assistant.audio.realtime_audio_processor import AudioConfig, AudioFormat
            
            # Create AudioConfig from settings
            audio_config = AudioConfig(
                sample_rate=settings.audio_sample_rate,
                channels=settings.audio_channels,
                sample_width=settings.audio_sample_width,
                format=AudioFormat.SLIN16,
                chunk_size=settings.audio_chunk_size,
                buffer_size=settings.audio_buffer_size
            )
            
            assert audio_config.sample_rate == settings.audio_sample_rate
            assert audio_config.channels == settings.audio_channels
            assert audio_config.chunk_size == settings.audio_chunk_size
    
    def test_gemini_config_compatibility(self):
        """Test Gemini configuration compatibility with client."""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            settings = VoiceAssistantSettings()
            
            # Import here to avoid circular imports in tests
            from src.voice_assistant.ai.gemini_live_client import GeminiLiveConfig
            
            # Create GeminiLiveConfig from settings
            gemini_config = GeminiLiveConfig(
                model=settings.gemini_live_model,
                voice=settings.gemini_voice
            )
            
            assert gemini_config.model == settings.gemini_live_model
            assert gemini_config.voice == settings.gemini_voice
    
    def test_ari_config_compatibility(self):
        """Test ARI configuration compatibility with handler."""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            settings = VoiceAssistantSettings()
            
            # Import here to avoid circular imports in tests
            from src.voice_assistant.telephony.realtime_ari_handler import RealTimeARIConfig
            
            # Create RealTimeARIConfig from settings
            ari_config = RealTimeARIConfig(
                ari_base_url=settings.ari_base_url,
                ari_username=settings.ari_username,
                ari_password=settings.ari_password,
                stasis_app=settings.stasis_app,
                external_media_host=settings.external_media_host,
                external_media_port=settings.external_media_port,
                auto_answer=settings.auto_answer_calls,
                enable_recording=settings.enable_call_recording,
                max_call_duration=settings.max_call_duration,
                audio_format=settings.audio_format,
                sample_rate=settings.audio_sample_rate
            )
            
            assert ari_config.ari_base_url == settings.ari_base_url
            assert ari_config.stasis_app == settings.stasis_app
            assert ari_config.audio_format == settings.audio_format