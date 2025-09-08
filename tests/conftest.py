"""
Global test configuration and fixtures.
"""

import warnings
import pytest
import asyncio
from pathlib import Path
import sys

# Add src to Python path for tests
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Suppress deprecation warnings to keep CI output clean
warnings.filterwarnings(
    "ignore",
    message=".*aifc was removed in Python 3.13.*",
    category=DeprecationWarning,
    module=r"speech_recognition.*",
)

warnings.filterwarnings(
    "ignore",
    message=".*websockets\.legacy is deprecated.*",
    category=DeprecationWarning,
)

warnings.filterwarnings(
    "ignore",
    message=".*WebSocketServerProtocol is deprecated.*",
    category=DeprecationWarning,
)

warnings.filterwarnings(
    "ignore",
    message=".*websockets\.server\.WebSocketServerProtocol is deprecated.*",
    category=DeprecationWarning,
)

warnings.filterwarnings(
    "ignore",
    message=".*Using extra keyword arguments on.*Field.*is deprecated.*",
    category=DeprecationWarning,
)

warnings.filterwarnings(
    "ignore",
    message=".*pydantic.*deprecated.*",
    category=DeprecationWarning,
)

# Audio configuration fixture
@pytest.fixture
def audio_config():
    """Provide audio configuration for tests."""
    from src.voice_assistant.audio.realtime_audio_processor import AudioConfig
    return AudioConfig()

# Sample audio data fixture
@pytest.fixture
def sample_audio_data():
    """Provide sample audio data for tests."""
    from tests.utils.audio_generator import AudioGenerator
    return AudioGenerator.generate_sine_wave(440, 100, amplitude=0.5)

# Silence audio data fixture
@pytest.fixture
def silence_audio_data():
    """Provide silence audio data for tests."""
    from tests.utils.audio_generator import AudioGenerator
    return AudioGenerator.generate_silence(100)

# Performance thresholds fixture
@pytest.fixture
def performance_thresholds():
    """Provide performance thresholds for tests."""
    return {
        "audio_processing_latency_ms": 200.0,  # More realistic for test environment
        "vad_processing_latency_ms": 50.0,     # More realistic for test environment
        "memory_usage_mb": 200.0,              # More realistic for test environment
        "cpu_usage_percent": 80.0              # CPU usage threshold for tests
    }

# Event loop fixture for async tests
@pytest.fixture(scope="function")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

# Test settings fixture
@pytest.fixture
def test_settings():
    """Provide test settings configuration."""
    class TestSettings:
        def __init__(self):
            # ARI Settings
            self.ari_base_url = "http://localhost:8088/ari"
            self.ari_username = "asterisk"
            self.ari_password = "1234"
            self.stasis_app = "gemini-voice-assistant"
            
            # Audio Settings
            self.audio_sample_rate = 16000
            self.audio_chunk_size = 320
            self.audio_buffer_size = 1600
            self.audio_format = "slin16"
            self.audio_channels = 1
            self.audio_sample_width = 2
            
            # External Media Settings
            self.external_media_host = "localhost"
            self.external_media_port = 8090
            
            # AI Settings
            self.google_api_key = "test-api-key"
            self.gemini_model = "gemini-2.5-flash"
            self.gemini_live_model = "gemini-2.0-flash-exp"
            self.gemini_voice = "Puck"
            self.max_tokens = 150
            self.temperature = 0.7
            
            # VAD Settings
            self.vad_energy_threshold = 300
            self.vad_silence_threshold = 0.5
            self.vad_speech_threshold = 0.1
            
            # Voice Settings
            self.voice_language = "en"
            self.speech_rate = 150
            self.voice_volume = 0.9
            
            # Timeout Settings
            self.listen_timeout = 20.0
            self.phrase_time_limit = 15.0
            self.max_retries = 3
            
            # Assistant Settings
            self.assistant_name = "ARI"
            self.company_name = "Voice Assistant Corp"
            
            # Performance Settings
            self.enable_performance_logging = False
            self.session_cleanup_interval = 300
            
            # Directories
            self.sounds_dir = "sounds"
            self.temp_audio_dir = "sounds/temp"
            self.recordings_dir = "recordings"
        
        def __getitem__(self, key):
            """Allow dict-like access for backward compatibility"""
            return getattr(self, key)
        
        def __setitem__(self, key, value):
            """Allow dict-like assignment"""
            setattr(self, key, value)
        
        def __contains__(self, key):
            """Allow 'in' operator"""
            return hasattr(self, key)
        
        def get(self, key, default=None):
            """Dict-like get method"""
            return getattr(self, key, default)
        
        def keys(self):
            """Return all attribute names"""
            return [attr for attr in dir(self) if not attr.startswith('_') and not callable(getattr(self, attr))]
    
    return TestSettings()

# Sample ARI events fixture
@pytest.fixture
def sample_ari_events():
    """Provide sample ARI events for testing."""
    return {
        "stasis_start": {
            "type": "StasisStart",
            "application": "gemini-voice-assistant",
            "timestamp": "2024-01-01T12:00:00.000Z",
            "channel": {
                "id": "test-channel-123",
                "name": "SIP/test-00000001",
                "state": "Ring",
                "caller": {
                    "name": "Test User",
                    "number": "1234567890"
                },
                "connected": {
                    "name": "Assistant",
                    "number": "0987654321"
                },
                "accountcode": "",
                "dialplan": {
                    "context": "default",
                    "exten": "100",
                    "priority": 1
                },
                "creationtime": "2024-01-01T12:00:00.000Z",
                "language": "en"
            },
            "args": []
        },
        "stasis_end": {
            "type": "StasisEnd",
            "application": "gemini-voice-assistant",
            "timestamp": "2024-01-01T12:05:00.000Z",
            "channel": {
                "id": "test-channel-123",
                "name": "SIP/test-00000001",
                "state": "Up"
            }
        },
        "channel_state_change": {
            "type": "ChannelStateChange",
            "application": "gemini-voice-assistant",
            "timestamp": "2024-01-01T12:01:00.000Z",
            "channel": {
                "id": "test-channel-123",
                "name": "SIP/test-00000001",
                "state": "Up"
            }
        }
    }