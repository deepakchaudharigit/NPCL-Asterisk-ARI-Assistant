"""
Error simulation and edge case fixtures for testing error handling and recovery.
"""

import pytest
import asyncio
import random
import time
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from unittest.mock import Mock, AsyncMock, patch
from enum import Enum


class ErrorType(Enum):
    """Types of errors that can be simulated."""
    NETWORK_ERROR = "network_error"
    API_ERROR = "api_error"
    AUDIO_ERROR = "audio_error"
    SYSTEM_ERROR = "system_error"
    TIMEOUT_ERROR = "timeout_error"
    VALIDATION_ERROR = "validation_error"
    RESOURCE_ERROR = "resource_error"


class ErrorSeverity(Enum):
    """Severity levels for errors."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorScenario:
    """Definition of an error scenario for testing."""
    name: str
    description: str
    error_type: ErrorType
    severity: ErrorSeverity
    trigger_condition: str
    expected_behavior: str
    recovery_strategy: str
    test_parameters: Dict[str, Any] = field(default_factory=dict)
    error_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorInjectionConfig:
    """Configuration for error injection during tests."""
    enabled: bool = True
    error_rate: float = 0.1  # 10% error rate
    error_types: List[ErrorType] = field(default_factory=list)
    timing: str = "random"  # "random", "periodic", "burst"
    recovery_delay: float = 1.0
    max_consecutive_errors: int = 3


class ErrorSimulator:
    """Simulates various error conditions for testing."""
    
    def __init__(self, config: ErrorInjectionConfig):
        self.config = config
        self.error_count = 0
        self.consecutive_errors = 0
        self.last_error_time = 0
        self.error_history = []
    
    def should_inject_error(self) -> bool:
        """Determine if an error should be injected."""
        if not self.config.enabled:
            return False
        
        # Check consecutive error limit
        if self.consecutive_errors >= self.config.max_consecutive_errors:
            return False
        
        # Check timing
        current_time = time.time()
        if self.config.timing == "periodic":
            return (current_time - self.last_error_time) > (1.0 / self.config.error_rate)
        elif self.config.timing == "burst":
            # Inject errors in bursts
            if self.consecutive_errors == 0:
                return random.random() < self.config.error_rate
            else:
                return random.random() < 0.8  # High probability during burst
        else:  # random
            return random.random() < self.config.error_rate
    
    def inject_error(self, operation: str) -> Optional[Exception]:
        """Inject an error for the specified operation."""
        if not self.should_inject_error():
            self.consecutive_errors = 0
            return None
        
        error_type = random.choice(self.config.error_types or list(ErrorType))
        error = self._create_error(error_type, operation)
        
        self.error_count += 1
        self.consecutive_errors += 1
        self.last_error_time = time.time()
        
        self.error_history.append({
            "timestamp": self.last_error_time,
            "operation": operation,
            "error_type": error_type,
            "error": str(error)
        })
        
        return error
    
    def _create_error(self, error_type: ErrorType, operation: str) -> Exception:
        """Create an appropriate error for the given type."""
        if error_type == ErrorType.NETWORK_ERROR:
            return ConnectionError(f"Network error during {operation}")
        elif error_type == ErrorType.API_ERROR:
            return RuntimeError(f"API error during {operation}")
        elif error_type == ErrorType.AUDIO_ERROR:
            return ValueError(f"Audio processing error during {operation}")
        elif error_type == ErrorType.SYSTEM_ERROR:
            return OSError(f"System error during {operation}")
        elif error_type == ErrorType.TIMEOUT_ERROR:
            return TimeoutError(f"Timeout during {operation}")
        elif error_type == ErrorType.VALIDATION_ERROR:
            return ValueError(f"Validation error during {operation}")
        elif error_type == ErrorType.RESOURCE_ERROR:
            return MemoryError(f"Resource exhaustion during {operation}")
        else:
            return Exception(f"Unknown error during {operation}")
    
    def reset(self):
        """Reset error simulation state."""
        self.error_count = 0
        self.consecutive_errors = 0
        self.last_error_time = 0
        self.error_history.clear()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get error simulation statistics."""
        return {
            "total_errors": self.error_count,
            "consecutive_errors": self.consecutive_errors,
            "error_rate": len(self.error_history) / max(1, time.time() - (self.error_history[0]["timestamp"] if self.error_history else time.time())),
            "error_types": list(set(e["error_type"] for e in self.error_history)),
            "error_history": self.error_history.copy()
        }


class NetworkErrorSimulator:
    """Specialized simulator for network errors."""
    
    @staticmethod
    async def simulate_connection_timeout(delay: float = 5.0):
        """Simulate connection timeout."""
        await asyncio.sleep(delay)
        raise TimeoutError("Connection timeout")
    
    @staticmethod
    async def simulate_connection_refused():
        """Simulate connection refused."""
        raise ConnectionRefusedError("Connection refused")
    
    @staticmethod
    async def simulate_dns_failure():
        """Simulate DNS resolution failure."""
        raise OSError("DNS resolution failed")
    
    @staticmethod
    async def simulate_ssl_error():
        """Simulate SSL handshake failure."""
        raise Exception("SSL handshake failed")
    
    @staticmethod
    async def simulate_intermittent_connection(
        success_probability: float = 0.7,
        operation: Callable = None
    ):
        """Simulate intermittent connection issues."""
        if random.random() > success_probability:
            raise ConnectionError("Intermittent connection failure")
        
        if operation:
            return await operation()
        return True


class APIErrorSimulator:
    """Specialized simulator for API errors."""
    
    @staticmethod
    def simulate_rate_limit():
        """Simulate API rate limiting."""
        return {
            "error": {
                "code": 429,
                "message": "Rate limit exceeded",
                "retry_after": 60
            }
        }
    
    @staticmethod
    def simulate_authentication_error():
        """Simulate authentication failure."""
        return {
            "error": {
                "code": 401,
                "message": "Authentication failed",
                "details": "Invalid API key"
            }
        }
    
    @staticmethod
    def simulate_server_error():
        """Simulate server-side error."""
        return {
            "error": {
                "code": 500,
                "message": "Internal server error",
                "details": "Temporary service unavailability"
            }
        }
    
    @staticmethod
    def simulate_malformed_response():
        """Simulate malformed API response."""
        return "invalid json response"
    
    @staticmethod
    def simulate_partial_response():
        """Simulate incomplete API response."""
        return {
            "partial": True,
            "data": None
            # Missing required fields
        }


class AudioErrorSimulator:
    """Specialized simulator for audio processing errors."""
    
    @staticmethod
    def simulate_corrupted_audio():
        """Generate corrupted audio data."""
        return b'\xff\xfe\xfd\xfc' * 100  # Invalid audio data
    
    @staticmethod
    def simulate_wrong_format():
        """Generate audio in wrong format."""
        return b'RIFF' + b'\x00' * 100  # WAV header but wrong content
    
    @staticmethod
    def simulate_buffer_overflow():
        """Simulate audio buffer overflow."""
        return b'\x00' * (1024 * 1024)  # 1MB of audio data
    
    @staticmethod
    def simulate_sample_rate_mismatch():
        """Generate audio with unexpected sample rate."""
        # Generate 8kHz audio when 16kHz is expected
        import numpy as np
        samples = np.sin(2 * np.pi * 440 * np.linspace(0, 1, 8000))
        return (samples * 32767).astype(np.int16).tobytes()
    
    @staticmethod
    def simulate_channel_mismatch():
        """Generate stereo audio when mono is expected."""
        import numpy as np
        mono_samples = np.sin(2 * np.pi * 440 * np.linspace(0, 1, 16000))
        stereo_samples = np.column_stack([mono_samples, mono_samples])
        return (stereo_samples * 32767).astype(np.int16).tobytes()


@pytest.fixture
def error_scenarios():
    """Collection of error scenarios for testing."""
    return {
        "network_timeout": ErrorScenario(
            name="network_timeout",
            description="Network connection timeout",
            error_type=ErrorType.NETWORK_ERROR,
            severity=ErrorSeverity.HIGH,
            trigger_condition="websocket_connect",
            expected_behavior="retry_with_backoff",
            recovery_strategy="exponential_backoff",
            test_parameters={"timeout": 5.0, "max_retries": 3},
            error_data={"timeout_duration": 5.0}
        ),
        
        "api_rate_limit": ErrorScenario(
            name="api_rate_limit",
            description="API rate limit exceeded",
            error_type=ErrorType.API_ERROR,
            severity=ErrorSeverity.MEDIUM,
            trigger_condition="api_request",
            expected_behavior="wait_and_retry",
            recovery_strategy="respect_retry_after",
            test_parameters={"retry_after": 60},
            error_data=APIErrorSimulator.simulate_rate_limit()
        ),
        
        "audio_corruption": ErrorScenario(
            name="audio_corruption",
            description="Corrupted audio data",
            error_type=ErrorType.AUDIO_ERROR,
            severity=ErrorSeverity.HIGH,
            trigger_condition="audio_processing",
            expected_behavior="discard_and_continue",
            recovery_strategy="request_retransmission",
            test_parameters={"corruption_type": "random_bytes"},
            error_data={"corrupted_audio": AudioErrorSimulator.simulate_corrupted_audio()}
        ),
        
        "memory_exhaustion": ErrorScenario(
            name="memory_exhaustion",
            description="System memory exhaustion",
            error_type=ErrorType.RESOURCE_ERROR,
            severity=ErrorSeverity.CRITICAL,
            trigger_condition="large_audio_buffer",
            expected_behavior="graceful_degradation",
            recovery_strategy="reduce_buffer_size",
            test_parameters={"memory_limit": 100 * 1024 * 1024},  # 100MB
            error_data={"large_buffer": b'\x00' * (50 * 1024 * 1024)}  # 50MB
        ),
        
        "websocket_disconnect": ErrorScenario(
            name="websocket_disconnect",
            description="Unexpected WebSocket disconnection",
            error_type=ErrorType.NETWORK_ERROR,
            severity=ErrorSeverity.HIGH,
            trigger_condition="during_conversation",
            expected_behavior="attempt_reconnection",
            recovery_strategy="reconnect_with_session_recovery",
            test_parameters={"reconnect_attempts": 5, "backoff_factor": 2.0}
        ),
        
        "invalid_audio_format": ErrorScenario(
            name="invalid_audio_format",
            description="Invalid audio format received",
            error_type=ErrorType.VALIDATION_ERROR,
            severity=ErrorSeverity.MEDIUM,
            trigger_condition="audio_validation",
            expected_behavior="reject_and_log",
            recovery_strategy="request_format_correction",
            test_parameters={"expected_format": "pcm16", "received_format": "unknown"},
            error_data={"invalid_audio": AudioErrorSimulator.simulate_wrong_format()}
        )
    }


@pytest.fixture
def error_injection_configs():
    """Different error injection configurations."""
    return {
        "low_error_rate": ErrorInjectionConfig(
            enabled=True,
            error_rate=0.01,  # 1%
            error_types=[ErrorType.NETWORK_ERROR],
            timing="random",
            recovery_delay=0.5,
            max_consecutive_errors=1
        ),
        
        "moderate_error_rate": ErrorInjectionConfig(
            enabled=True,
            error_rate=0.05,  # 5%
            error_types=[ErrorType.NETWORK_ERROR, ErrorType.API_ERROR],
            timing="random",
            recovery_delay=1.0,
            max_consecutive_errors=2
        ),
        
        "high_error_rate": ErrorInjectionConfig(
            enabled=True,
            error_rate=0.15,  # 15%
            error_types=[ErrorType.NETWORK_ERROR, ErrorType.API_ERROR, ErrorType.AUDIO_ERROR],
            timing="burst",
            recovery_delay=2.0,
            max_consecutive_errors=3
        ),
        
        "chaos_testing": ErrorInjectionConfig(
            enabled=True,
            error_rate=0.25,  # 25%
            error_types=list(ErrorType),
            timing="random",
            recovery_delay=0.1,
            max_consecutive_errors=5
        )
    }


@pytest.fixture
def error_simulator_factory(error_injection_configs):
    """Factory for creating error simulators."""
    def _create_simulator(config_name: str) -> ErrorSimulator:
        config = error_injection_configs[config_name]
        return ErrorSimulator(config)
    
    return _create_simulator


@pytest.fixture
def network_error_simulator():
    """Network error simulator."""
    return NetworkErrorSimulator()


@pytest.fixture
def api_error_simulator():
    """API error simulator."""
    return APIErrorSimulator()


@pytest.fixture
def audio_error_simulator():
    """Audio error simulator."""
    return AudioErrorSimulator()


@pytest.fixture
def edge_case_data():
    """Edge case data for testing robustness."""
    return {
        "empty_strings": ["", None, "   ", "\n\t"],
        "invalid_json": [
            "invalid json",
            '{"incomplete": ',
            '{"invalid": "json"',
            '{"nested": {"incomplete": }',
            "null",
            "undefined"
        ],
        "extreme_numbers": [
            0, -1, 2**31 - 1, -2**31, 2**63 - 1, -2**63,
            float('inf'), float('-inf'), float('nan'),
            1e-10, 1e10, 3.14159265359
        ],
        "unicode_strings": [
            "Hello 世界",
            "🎵🎤🎧",
            "Ñoño niño",
            "Здравствуй мир",
            "مرحبا بالعالم",
            "\x00\x01\x02\x03"
        ],
        "large_data": {
            "large_string": "x" * (10 * 1024 * 1024),  # 10MB string
            "large_list": list(range(1000000)),  # 1M items
            "large_dict": {f"key_{i}": f"value_{i}" for i in range(100000)},  # 100K items
            "nested_structure": {"level_" + str(i): {"data": "x" * 1000} for i in range(1000)}
        }
    }


@pytest.fixture
def malformed_messages():
    """Malformed message examples for testing."""
    return {
        "websocket_messages": [
            "",  # Empty message
            "not json",  # Invalid JSON
            '{"type": }',  # Incomplete JSON
            '{"type": "unknown"}',  # Unknown message type
            '{"type": "valid", "data": null}',  # Missing required fields
            b'\xff\xfe\xfd\xfc',  # Binary data
            "x" * (1024 * 1024),  # Very large message
        ],
        
        "ari_events": [
            {},  # Empty event
            {"type": ""},  # Empty type
            {"type": "UnknownEvent"},  # Unknown event type
            {"type": "StasisStart"},  # Missing required fields
            {"type": "StasisStart", "channel": None},  # Null channel
            {"type": "StasisStart", "channel": {"id": ""}},  # Empty channel ID
        ],
        
        "gemini_events": [
            {},  # Empty event
            {"type": ""},  # Empty type
            {"type": "unknown.event"},  # Unknown event type
            {"type": "response.audio.delta"},  # Missing response data
            {"type": "response.audio.delta", "response": {}},  # Missing audio data
            {"type": "response.audio.delta", "response": {"output": {}}},  # Missing audio
        ]
    }


@pytest.fixture
def resource_exhaustion_scenarios():
    """Scenarios for testing resource exhaustion."""
    return {
        "memory_pressure": {
            "description": "Simulate memory pressure",
            "allocate_mb": 500,
            "duration_seconds": 10,
            "expected_behavior": "graceful_degradation"
        },
        
        "cpu_intensive": {
            "description": "Simulate CPU intensive operations",
            "cpu_load_percent": 90,
            "duration_seconds": 5,
            "expected_behavior": "maintain_responsiveness"
        },
        
        "disk_space_exhaustion": {
            "description": "Simulate disk space exhaustion",
            "fill_disk_percent": 95,
            "expected_behavior": "cleanup_old_files"
        },
        
        "file_descriptor_exhaustion": {
            "description": "Simulate file descriptor exhaustion",
            "open_files": 1000,
            "expected_behavior": "close_unused_files"
        },
        
        "network_bandwidth_saturation": {
            "description": "Simulate network bandwidth saturation",
            "bandwidth_limit_kbps": 64,
            "expected_behavior": "adaptive_quality"
        }
    }


@pytest.fixture
def recovery_test_scenarios():
    """Scenarios for testing error recovery."""
    return {
        "connection_recovery": {
            "description": "Test connection recovery after network failure",
            "failure_duration": 5.0,
            "expected_recovery_time": 10.0,
            "recovery_strategy": "exponential_backoff"
        },
        
        "session_recovery": {
            "description": "Test session recovery after disconnection",
            "session_data": {"conversation_history": ["Hello", "Hi there"]},
            "expected_behavior": "restore_context"
        },
        
        "audio_stream_recovery": {
            "description": "Test audio stream recovery after corruption",
            "corruption_type": "packet_loss",
            "expected_behavior": "request_retransmission"
        },
        
        "api_recovery": {
            "description": "Test API recovery after rate limiting",
            "rate_limit_duration": 60,
            "expected_behavior": "queue_requests"
        }
    }


@pytest.fixture
def fault_injection_decorator():
    """Decorator for injecting faults into functions."""
    def _fault_injector(
        error_rate: float = 0.1,
        error_types: List[Exception] = None,
        delay_range: Tuple[float, float] = (0.0, 1.0)
    ):
        if error_types is None:
            error_types = [ConnectionError, TimeoutError, ValueError]
        
        def decorator(func):
            async def async_wrapper(*args, **kwargs):
                # Inject delay
                delay = random.uniform(*delay_range)
                await asyncio.sleep(delay)
                
                # Inject error
                if random.random() < error_rate:
                    error_type = random.choice(error_types)
                    raise error_type(f"Injected error in {func.__name__}")
                
                return await func(*args, **kwargs)
            
            def sync_wrapper(*args, **kwargs):
                # Inject delay
                delay = random.uniform(*delay_range)
                time.sleep(delay)
                
                # Inject error
                if random.random() < error_rate:
                    error_type = random.choice(error_types)
                    raise error_type(f"Injected error in {func.__name__}")
                
                return func(*args, **kwargs)
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        
        return decorator
    
    return _fault_injector