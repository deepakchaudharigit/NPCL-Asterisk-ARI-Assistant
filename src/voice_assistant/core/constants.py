"""
Core constants for the Voice Assistant application.
Centralizes all magic numbers and hardcoded values.
"""

from enum import Enum
from typing import Dict, Any

# Audio Processing Constants
class AudioConstants:
    """Audio processing related constants."""
    
    # Sample rates (Hz)
    SAMPLE_RATE_8KHZ = 8000
    SAMPLE_RATE_16KHZ = 16000
    SAMPLE_RATE_44KHZ = 44100
    SAMPLE_RATE_48KHZ = 48000
    
    # Audio formats
    SAMPLE_WIDTH_16BIT = 2
    CHANNELS_MONO = 1
    CHANNELS_STEREO = 2
    
    # Chunk sizes (in samples)
    CHUNK_SIZE_20MS = 320  # 20ms at 16kHz
    CHUNK_SIZE_40MS = 640  # 40ms at 16kHz
    
    # Buffer sizes
    BUFFER_SIZE_SMALL = 1600   # 100ms at 16kHz
    BUFFER_SIZE_MEDIUM = 8000  # 500ms at 16kHz
    BUFFER_SIZE_LARGE = 16000  # 1s at 16kHz
    
    # Energy thresholds for VAD
    VAD_ENERGY_THRESHOLD_LOW = 300
    VAD_ENERGY_THRESHOLD_MEDIUM = 1000
    VAD_ENERGY_THRESHOLD_HIGH = 4000
    
    # Timing thresholds (seconds)
    VAD_SILENCE_THRESHOLD_FAST = 0.1
    VAD_SILENCE_THRESHOLD_NORMAL = 0.5
    VAD_SILENCE_THRESHOLD_SLOW = 1.0
    
    VAD_SPEECH_THRESHOLD_FAST = 0.02
    VAD_SPEECH_THRESHOLD_NORMAL = 0.1
    VAD_SPEECH_THRESHOLD_SLOW = 0.2
    
    # Audio quality
    AMPLITUDE_MAX = 0.95
    AMPLITUDE_NORMAL = 0.7
    AMPLITUDE_LOW = 0.3

# Network and API Constants
class NetworkConstants:
    """Network and API related constants."""
    
    # Timeouts (seconds)
    HTTP_TIMEOUT_SHORT = 5
    HTTP_TIMEOUT_NORMAL = 30
    HTTP_TIMEOUT_LONG = 60
    
    WEBSOCKET_TIMEOUT = 10
    WEBSOCKET_PING_INTERVAL = 30
    WEBSOCKET_PING_TIMEOUT = 10
    
    # Retry settings
    MAX_RETRIES_DEFAULT = 3
    MAX_RETRIES_CRITICAL = 5
    RETRY_DELAY_BASE = 1.0
    RETRY_DELAY_MAX = 30.0
    
    # Rate limiting
    RATE_LIMIT_REQUESTS_PER_MINUTE = 60
    RATE_LIMIT_REQUESTS_PER_HOUR = 1000

# Application Constants
class AppConstants:
    """Application-level constants."""
    
    # Session management
    SESSION_TIMEOUT_MINUTES = 30
    SESSION_CLEANUP_INTERVAL_SECONDS = 300
    MAX_CONCURRENT_SESSIONS = 100
    
    # Call management
    MAX_CALL_DURATION_SECONDS = 3600  # 1 hour
    CALL_TIMEOUT_SECONDS = 30
    
    # File management
    MAX_FILE_SIZE_MB = 50
    TEMP_FILE_CLEANUP_HOURS = 24
    
    # Logging
    LOG_ROTATION_SIZE_MB = 100
    LOG_RETENTION_DAYS = 30

# AI Model Constants
class AIConstants:
    """AI model related constants."""
    
    # Token limits
    MAX_TOKENS_SHORT = 150
    MAX_TOKENS_MEDIUM = 500
    MAX_TOKENS_LONG = 1000
    
    # Temperature settings
    TEMPERATURE_CREATIVE = 0.9
    TEMPERATURE_BALANCED = 0.7
    TEMPERATURE_FOCUSED = 0.3
    TEMPERATURE_DETERMINISTIC = 0.1
    
    # Context windows
    CONTEXT_WINDOW_SMALL = 1000
    CONTEXT_WINDOW_MEDIUM = 4000
    CONTEXT_WINDOW_LARGE = 8000

# Error Codes
class ErrorCodes(Enum):
    """Standardized error codes."""
    
    # General errors
    UNKNOWN_ERROR = "ERR_UNKNOWN"
    CONFIGURATION_ERROR = "ERR_CONFIG"
    VALIDATION_ERROR = "ERR_VALIDATION"
    
    # Network errors
    CONNECTION_ERROR = "ERR_CONNECTION"
    TIMEOUT_ERROR = "ERR_TIMEOUT"
    RATE_LIMIT_ERROR = "ERR_RATE_LIMIT"
    
    # Audio errors
    AUDIO_PROCESSING_ERROR = "ERR_AUDIO_PROCESSING"
    AUDIO_FORMAT_ERROR = "ERR_AUDIO_FORMAT"
    MICROPHONE_ERROR = "ERR_MICROPHONE"
    SPEAKER_ERROR = "ERR_SPEAKER"
    
    # AI errors
    AI_API_ERROR = "ERR_AI_API"
    AI_QUOTA_ERROR = "ERR_AI_QUOTA"
    AI_MODEL_ERROR = "ERR_AI_MODEL"
    
    # Security errors
    AUTHENTICATION_ERROR = "ERR_AUTH"
    AUTHORIZATION_ERROR = "ERR_AUTHZ"
    API_KEY_ERROR = "ERR_API_KEY"

# Status Codes
class StatusCodes(Enum):
    """Application status codes."""
    
    # General status
    SUCCESS = "SUCCESS"
    PENDING = "PENDING"
    FAILED = "FAILED"
    
    # Connection status
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    
    # Processing status
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    
    # Audio status
    LISTENING = "LISTENING"
    SPEAKING = "SPEAKING"
    SILENT = "SILENT"

# Default configurations
DEFAULT_AUDIO_CONFIG = {
    "sample_rate": AudioConstants.SAMPLE_RATE_16KHZ,
    "channels": AudioConstants.CHANNELS_MONO,
    "sample_width": AudioConstants.SAMPLE_WIDTH_16BIT,
    "chunk_size": AudioConstants.CHUNK_SIZE_20MS,
    "buffer_size": AudioConstants.BUFFER_SIZE_SMALL,
}

DEFAULT_VAD_CONFIG = {
    "energy_threshold": AudioConstants.VAD_ENERGY_THRESHOLD_LOW,
    "silence_threshold": AudioConstants.VAD_SILENCE_THRESHOLD_NORMAL,
    "speech_threshold": AudioConstants.VAD_SPEECH_THRESHOLD_NORMAL,
}

DEFAULT_NETWORK_CONFIG = {
    "timeout": NetworkConstants.HTTP_TIMEOUT_NORMAL,
    "max_retries": NetworkConstants.MAX_RETRIES_DEFAULT,
    "retry_delay": NetworkConstants.RETRY_DELAY_BASE,
}

DEFAULT_AI_CONFIG = {
    "max_tokens": AIConstants.MAX_TOKENS_SHORT,
    "temperature": AIConstants.TEMPERATURE_BALANCED,
    "context_window": AIConstants.CONTEXT_WINDOW_MEDIUM,
}