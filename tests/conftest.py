"""
Global test configuration and fixtures.
"""

import warnings
import pytest
import asyncio
from pathlib import Path
import sys
import logging
from unittest.mock import Mock, AsyncMock

# Add src to Python path for tests
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import test utilities
from tests.utils.audio_generator import AudioGenerator
from tests.mocks.mock_gemini import MockGeminiClient

# Import application modules (with error handling for missing modules)
try:
    from config.settings import get_settings
except ImportError:
    get_settings = None

try:
    from src.voice_assistant.ai.gemini_live_client import GeminiLiveConfig
except ImportError:
    GeminiLiveConfig = None

try:
    from src.voice_assistant.audio.realtime_audio_processor import AudioConfig, AudioFormat
except ImportError:
    AudioConfig = None
    AudioFormat = None

# Removed constants import to avoid circular dependency
AudioConstants = None
DEFAULT_AUDIO_CONFIG = None

try:
    from src.voice_assistant.core.performance import PerformanceMonitor
except ImportError:
    PerformanceMonitor = None

try:
    from src.voice_assistant.core.security import SecurityManager
except ImportError:
    SecurityManager = None

# Suppress deprecation warnings to keep CI output clean
warnings.filterwarnings(
    "ignore",
    message=".*aifc was removed in Python 3.13.*",
    category=DeprecationWarning,
    module=r"speech_recognition.*",
)

warnings.filterwarnings(
    "ignore",
    message=r".*websockets\.legacy is deprecated.*",
    category=DeprecationWarning,
)

warnings.filterwarnings(
    "ignore",
    message=".*WebSocketServerProtocol is deprecated.*",
    category=DeprecationWarning,
)

warnings.filterwarnings(
    "ignore",
    message=r".*websockets\.server\.WebSocketServerProtocol is deprecated.*",
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
    if AudioConfig is None:
        # Fallback configuration for when module is not available
        class MockAudioConfig:
            def __init__(self):
                self.sample_rate = 16000
                self.channels = 1
                self.sample_width = 2
                self.chunk_size = 320
                self.buffer_size = 1600
                self.format = "slin16"
        return MockAudioConfig()
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
    """Provide realistic performance thresholds for test environment."""
    return {
        "audio_processing_latency_ms": 20.0,   # Production requirement: <20ms
        "vad_processing_latency_ms": 10.0,     # Production requirement: <10ms
        "memory_usage_mb": 250.0,              # Test environment: <250MB total process (includes pytest overhead)
        "cpu_usage_percent": 80.0,             # Test environment: <80% average (relaxed for test)
        "ai_response_time_ms": 1000.0,         # Production requirement: <1s
        "session_creation_ms": 100.0,          # Test environment: <100ms (relaxed for mocks)
        "websocket_latency_ms": 100.0,         # Production requirement: <100ms
        "error_rate_percent": 1.0,             # Production requirement: <1% error rate
        "concurrent_calls_limit": 100,         # Production requirement: 100 concurrent calls
        "throughput_calls_per_second": 10.0,   # Production requirement: 10 calls/second
        # Production-specific thresholds (for actual deployment)
        "production_memory_usage_mb": 100.0,   # Production requirement: <100MB per session
        "production_cpu_usage_percent": 70.0   # Production requirement: <70% average
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
            self.gemini_model = "gemini-1.5-flash"
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

# Enhanced ARI events fixture
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

# Enhanced fixtures for improved testing

@pytest.fixture
def gemini_config():
    """Provide Gemini Live configuration for tests."""
    if GeminiLiveConfig is None:
        # Fallback configuration for when module is not available
        class MockGeminiLiveConfig:
            def __init__(self):
                self.model = "gemini-1.5-flash"
                self.voice = "Puck"
                self.input_audio_format = "pcm16"
                self.output_audio_format = "pcm16"
        return MockGeminiLiveConfig()
    return GeminiLiveConfig(
        model="gemini-1.5-flash",
        voice="Puck",
        input_audio_format="pcm16",
        output_audio_format="pcm16"
    )

@pytest.fixture
def mock_performance_monitor():
    """Provide mock performance monitor for tests."""
    if PerformanceMonitor is None:
        # Create a simple mock when module is not available
        monitor = Mock()
    else:
        monitor = Mock(spec=PerformanceMonitor)
    
    monitor.timer = Mock()
    monitor.increment = Mock()
    monitor.gauge = Mock()
    monitor.histogram = Mock()
    monitor.get_performance_summary = Mock(return_value={
        "timestamp": "2024-01-01T12:00:00Z",
        "system": {"cpu_percent": 50.0, "memory_percent": 60.0},
        "application": {"active_sessions": 5, "error_rate": 1.0}
    })
    return monitor

@pytest.fixture
def mock_security_manager():
    """Provide mock security manager for tests."""
    if SecurityManager is None:
        # Create a simple mock when module is not available
        manager = Mock()
    else:
        manager = Mock(spec=SecurityManager)
    
    manager.validate_and_sanitize_input = Mock(side_effect=lambda x, *args, **kwargs: x)
    manager.check_rate_limit = Mock(return_value=True)
    manager.generate_secure_token = Mock(return_value="test-token-123")
    return manager

@pytest.fixture
def mock_gemini_client():
    """Provide mock Gemini client for tests."""
    client = MockGeminiClient()
    return client

@pytest.fixture
def test_audio_files(tmp_path):
    """Create temporary audio files for testing."""
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    
    # Create test audio files
    files = {}
    
    # Short audio file
    short_audio = AudioGenerator.generate_sine_wave(440, 100)  # 100ms
    short_file = audio_dir / "short.wav"
    short_file.write_bytes(short_audio)
    files["short"] = str(short_file)
    
    # Long audio file
    long_audio = AudioGenerator.generate_sine_wave(440, 5000)  # 5 seconds
    long_file = audio_dir / "long.wav"
    long_file.write_bytes(long_audio)
    files["long"] = str(long_file)
    
    # Silence file
    silence = AudioGenerator.generate_silence(1000)  # 1 second
    silence_file = audio_dir / "silence.wav"
    silence_file.write_bytes(silence)
    files["silence"] = str(silence_file)
    
    return files

@pytest.fixture
def test_database_url():
    """Provide test database URL."""
    return "sqlite:///:memory:"

@pytest.fixture
def test_redis_url():
    """Provide test Redis URL."""
    return "redis://localhost:6379/15"  # Use test database

@pytest.fixture(autouse=True)
def setup_test_logging():
    """Set up logging for tests."""
    # Configure logging for tests
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Suppress noisy loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    yield
    
    # Clean up logging handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

@pytest.fixture
def mock_websocket():
    """Provide mock WebSocket for testing."""
    ws = AsyncMock()
    ws.send = AsyncMock()
    ws.recv = AsyncMock()
    ws.close = AsyncMock()
    ws.closed = False
    return ws

@pytest.fixture
def test_session_data():
    """Provide test session data."""
    return {
        "session_id": "test-session-123",
        "user_id": "test-user-456",
        "created_at": "2024-01-01T12:00:00Z",
        "status": "active",
        "mode": "voice",
        "language": "en",
        "metadata": {
            "test_mode": True,
            "environment": "test"
        }
    }

@pytest.fixture
def test_conversation_data():
    """Provide test conversation data."""
    return [
        {
            "role": "user",
            "content": "Hello, I need help with my power connection",
            "timestamp": "2024-01-01T12:00:00Z"
        },
        {
            "role": "assistant",
            "content": "Hello! I'm here to help you with your power connection. Could you please provide your connection details?",
            "timestamp": "2024-01-01T12:00:05Z"
        },
        {
            "role": "user",
            "content": "My connection number is 12345",
            "timestamp": "2024-01-01T12:00:10Z"
        }
    ]

@pytest.fixture
def enhanced_audio_config():
    """Provide enhanced audio configuration with constants."""
    # Always use fallback configuration to avoid circular dependency
    class MockAudioConfig:
        def __init__(self):
            self.sample_rate = 16000
            self.channels = 1
            self.sample_width = 2
            self.format = "slin16"
            self.chunk_size = 320
            self.buffer_size = 1600
    return MockAudioConfig()

@pytest.fixture
def test_error_scenarios():
    """Provide test error scenarios."""
    return {
        "network_error": {
            "type": "ConnectionError",
            "message": "Failed to connect to AI service",
            "code": "NETWORK_ERROR"
        },
        "audio_error": {
            "type": "AudioProcessingError",
            "message": "Invalid audio format",
            "code": "AUDIO_FORMAT_ERROR"
        },
        "validation_error": {
            "type": "ValidationError",
            "message": "Input validation failed",
            "code": "VALIDATION_ERROR"
        },
        "rate_limit_error": {
            "type": "RateLimitError",
            "message": "Rate limit exceeded",
            "code": "RATE_LIMIT_ERROR"
        }
    }

# Async test utilities
@pytest.fixture
def async_test_timeout():
    """Provide timeout for async tests."""
    return 30.0  # 30 seconds

@pytest.fixture
def test_performance_thresholds():
    """Provide realistic performance thresholds for testing."""
    return {
        "response_time_ms": 2000,  # 2 seconds max response time
        "audio_processing_ms": 500,  # 500ms max audio processing
        "memory_usage_mb": 500,  # 500MB max memory usage
        "cpu_usage_percent": 90,  # 90% max CPU usage
        "error_rate_percent": 5,  # 5% max error rate
        "cache_hit_rate_percent": 80  # 80% min cache hit rate
    }