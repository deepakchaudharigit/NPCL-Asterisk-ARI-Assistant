"""
Configuration fixtures for different testing scenarios.
Provides various configurations for testing different environments and conditions.
"""

import pytest
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

from src.voice_assistant.ai.gemini_live_client import GeminiLiveConfig
from src.voice_assistant.telephony.realtime_ari_handler import RealTimeARIConfig


@dataclass
class TestEnvironmentConfig:
    """Configuration for different test environments."""
    name: str
    description: str
    ari_config: Dict[str, Any]
    gemini_config: Dict[str, Any]
    audio_config: Dict[str, Any]
    network_config: Dict[str, Any]
    performance_config: Dict[str, Any]
    features: Dict[str, bool] = field(default_factory=dict)


class ConfigurationFixtures:
    """Factory for creating various test configurations."""
    
    @staticmethod
    def create_development_config() -> TestEnvironmentConfig:
        """Configuration for development environment testing."""
        return TestEnvironmentConfig(
            name="development",
            description="Local development environment with mocks",
            ari_config={
                "ari_base_url": "http://localhost:8088/ari",
                "ari_username": "dev_user",
                "ari_password": "dev_pass",
                "stasis_app": "dev-voice-assistant",
                "external_media_host": "localhost",
                "external_media_port": 8090,
                "auto_answer": True,
                "enable_recording": False,
                "max_call_duration": 1800,  # 30 minutes
                "audio_format": "slin16",
                "sample_rate": 16000
            },
            gemini_config={
                "model": "gemini-2.0-flash-exp",
                "voice": "Puck",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": True,
                "output_audio_transcription": True,
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500
                }
            },
            audio_config={
                "sample_rate": 16000,
                "chunk_size": 320,  # 20ms chunks
                "format": "slin16",
                "channels": 1,
                "sample_width": 2,
                "vad_threshold": 0.01,
                "silence_threshold": 0.005,
                "max_silence_duration": 2.0,
                "enable_noise_reduction": True,
                "enable_echo_cancellation": True,
                "enable_automatic_gain_control": True
            },
            network_config={
                "websocket_timeout": 10.0,
                "http_timeout": 5.0,
                "retry_attempts": 3,
                "retry_delay": 1.0,
                "max_reconnect_attempts": 5,
                "heartbeat_interval": 30.0
            },
            performance_config={
                "max_memory_mb": 256,
                "max_cpu_percent": 50,
                "max_response_time_ms": 2000,
                "max_audio_latency_ms": 100,
                "audio_buffer_size": 4096,
                "max_concurrent_calls": 5
            },
            features={
                "enable_mocks": True,
                "enable_logging": True,
                "enable_metrics": True,
                "enable_debugging": True,
                "strict_validation": True
            }
        )
    
    @staticmethod
    def create_integration_config() -> TestEnvironmentConfig:
        """Configuration for integration testing."""
        return TestEnvironmentConfig(
            name="integration",
            description="Integration testing with real services",
            ari_config={
                "ari_base_url": "http://test-asterisk:8088/ari",
                "ari_username": "integration_user",
                "ari_password": "integration_pass",
                "stasis_app": "integration-voice-assistant",
                "external_media_host": "test-media-server",
                "external_media_port": 8090,
                "auto_answer": True,
                "enable_recording": True,
                "max_call_duration": 3600,  # 1 hour
                "audio_format": "slin16",
                "sample_rate": 16000
            },
            gemini_config={
                "model": "gemini-2.0-flash-exp",
                "voice": "Puck",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": True,
                "output_audio_transcription": True,
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.4,
                    "prefix_padding_ms": 400,
                    "silence_duration_ms": 700
                }
            },
            audio_config={
                "sample_rate": 16000,
                "chunk_size": 320,
                "format": "slin16",
                "channels": 1,
                "sample_width": 2,
                "vad_threshold": 0.015,
                "silence_threshold": 0.008,
                "max_silence_duration": 3.0,
                "enable_noise_reduction": True,
                "enable_echo_cancellation": True,
                "enable_automatic_gain_control": True
            },
            network_config={
                "websocket_timeout": 15.0,
                "http_timeout": 10.0,
                "retry_attempts": 5,
                "retry_delay": 2.0,
                "max_reconnect_attempts": 10,
                "heartbeat_interval": 60.0
            },
            performance_config={
                "max_memory_mb": 512,
                "max_cpu_percent": 70,
                "max_response_time_ms": 3000,
                "max_audio_latency_ms": 150,
                "audio_buffer_size": 8192,
                "max_concurrent_calls": 20
            },
            features={
                "enable_mocks": False,
                "enable_logging": True,
                "enable_metrics": True,
                "enable_debugging": False,
                "strict_validation": True
            }
        )
    
    @staticmethod
    def create_performance_config() -> TestEnvironmentConfig:
        """Configuration for performance testing."""
        return TestEnvironmentConfig(
            name="performance",
            description="High-load performance testing configuration",
            ari_config={
                "ari_base_url": "http://perf-asterisk:8088/ari",
                "ari_username": "perf_user",
                "ari_password": "perf_pass",
                "stasis_app": "perf-voice-assistant",
                "external_media_host": "perf-media-server",
                "external_media_port": 8090,
                "auto_answer": True,
                "enable_recording": False,  # Disable for performance
                "max_call_duration": 7200,  # 2 hours
                "audio_format": "slin16",
                "sample_rate": 16000
            },
            gemini_config={
                "model": "gemini-2.0-flash-exp",
                "voice": "Puck",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": False,  # Disable for performance
                "output_audio_transcription": False,
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.3,
                    "prefix_padding_ms": 200,
                    "silence_duration_ms": 400
                }
            },
            audio_config={
                "sample_rate": 16000,
                "chunk_size": 640,  # Larger chunks for performance
                "format": "slin16",
                "channels": 1,
                "sample_width": 2,
                "vad_threshold": 0.02,
                "silence_threshold": 0.01,
                "max_silence_duration": 1.5,
                "enable_noise_reduction": False,  # Disable for performance
                "enable_echo_cancellation": False,
                "enable_automatic_gain_control": False
            },
            network_config={
                "websocket_timeout": 30.0,
                "http_timeout": 15.0,
                "retry_attempts": 3,
                "retry_delay": 0.5,
                "max_reconnect_attempts": 3,
                "heartbeat_interval": 120.0
            },
            performance_config={
                "max_memory_mb": 2048,
                "max_cpu_percent": 90,
                "max_response_time_ms": 5000,
                "max_audio_latency_ms": 200,
                "audio_buffer_size": 16384,
                "max_concurrent_calls": 100
            },
            features={
                "enable_mocks": True,  # Use mocks for consistent performance
                "enable_logging": False,  # Disable for performance
                "enable_metrics": True,
                "enable_debugging": False,
                "strict_validation": False
            }
        )
    
    @staticmethod
    def create_error_simulation_config() -> TestEnvironmentConfig:
        """Configuration for error simulation testing."""
        return TestEnvironmentConfig(
            name="error_simulation",
            description="Configuration for testing error scenarios",
            ari_config={
                "ari_base_url": "http://unreliable-asterisk:8088/ari",
                "ari_username": "error_user",
                "ari_password": "error_pass",
                "stasis_app": "error-voice-assistant",
                "external_media_host": "unreliable-media-server",
                "external_media_port": 8090,
                "auto_answer": True,
                "enable_recording": True,
                "max_call_duration": 600,  # 10 minutes
                "audio_format": "slin16",
                "sample_rate": 16000
            },
            gemini_config={
                "model": "gemini-2.0-flash-exp",
                "voice": "Puck",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": True,
                "output_audio_transcription": True,
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.6,  # Higher threshold for noisy conditions
                    "prefix_padding_ms": 500,
                    "silence_duration_ms": 1000
                }
            },
            audio_config={
                "sample_rate": 16000,
                "chunk_size": 320,
                "format": "slin16",
                "channels": 1,
                "sample_width": 2,
                "vad_threshold": 0.03,  # Higher threshold for noisy conditions
                "silence_threshold": 0.015,
                "max_silence_duration": 5.0,
                "enable_noise_reduction": True,
                "enable_echo_cancellation": True,
                "enable_automatic_gain_control": True
            },
            network_config={
                "websocket_timeout": 5.0,  # Short timeout to trigger errors
                "http_timeout": 3.0,
                "retry_attempts": 10,  # More retries for error recovery
                "retry_delay": 0.1,
                "max_reconnect_attempts": 20,
                "heartbeat_interval": 10.0
            },
            performance_config={
                "max_memory_mb": 128,  # Low limit to trigger memory errors
                "max_cpu_percent": 30,
                "max_response_time_ms": 1000,  # Strict timing
                "max_audio_latency_ms": 50,
                "audio_buffer_size": 1024,  # Small buffer
                "max_concurrent_calls": 2
            },
            features={
                "enable_mocks": True,
                "enable_logging": True,
                "enable_metrics": True,
                "enable_debugging": True,
                "strict_validation": True,
                "simulate_network_errors": True,
                "simulate_audio_errors": True,
                "simulate_api_errors": True,
                "simulate_memory_pressure": True
            }
        )


@pytest.fixture
def development_config():
    """Development environment configuration."""
    return ConfigurationFixtures.create_development_config()


@pytest.fixture
def integration_config():
    """Integration testing configuration."""
    return ConfigurationFixtures.create_integration_config()


@pytest.fixture
def performance_config():
    """Performance testing configuration."""
    return ConfigurationFixtures.create_performance_config()


@pytest.fixture
def error_simulation_config():
    """Error simulation testing configuration."""
    return ConfigurationFixtures.create_error_simulation_config()


@pytest.fixture
def custom_config():
    """Factory for creating custom configurations."""
    def _create_custom_config(
        name: str,
        base_config: Optional[TestEnvironmentConfig] = None,
        overrides: Optional[Dict[str, Any]] = None
    ) -> TestEnvironmentConfig:
        """Create a custom configuration based on a base config with overrides."""
        if base_config is None:
            base_config = ConfigurationFixtures.create_development_config()
        
        if overrides is None:
            overrides = {}
        
        # Create a copy of the base config
        config = TestEnvironmentConfig(
            name=name,
            description=f"Custom configuration based on {base_config.name}",
            ari_config=base_config.ari_config.copy(),
            gemini_config=base_config.gemini_config.copy(),
            audio_config=base_config.audio_config.copy(),
            network_config=base_config.network_config.copy(),
            performance_config=base_config.performance_config.copy(),
            features=base_config.features.copy()
        )
        
        # Apply overrides
        for section, values in overrides.items():
            if hasattr(config, section):
                section_config = getattr(config, section)
                if isinstance(section_config, dict):
                    section_config.update(values)
                else:
                    setattr(config, section, values)
        
        return config
    
    return _create_custom_config


@pytest.fixture
def audio_quality_configs():
    """Different audio quality configurations for testing."""
    return {
        "high_quality": {
            "sample_rate": 44100,
            "chunk_size": 882,  # 20ms at 44.1kHz
            "format": "slin16",
            "enable_noise_reduction": True,
            "enable_echo_cancellation": True,
            "enable_automatic_gain_control": True
        },
        "standard_quality": {
            "sample_rate": 16000,
            "chunk_size": 320,  # 20ms at 16kHz
            "format": "slin16",
            "enable_noise_reduction": True,
            "enable_echo_cancellation": True,
            "enable_automatic_gain_control": True
        },
        "low_quality": {
            "sample_rate": 8000,
            "chunk_size": 160,  # 20ms at 8kHz
            "format": "ulaw",
            "enable_noise_reduction": False,
            "enable_echo_cancellation": False,
            "enable_automatic_gain_control": False
        },
        "minimal_quality": {
            "sample_rate": 8000,
            "chunk_size": 80,  # 10ms at 8kHz
            "format": "alaw",
            "enable_noise_reduction": False,
            "enable_echo_cancellation": False,
            "enable_automatic_gain_control": False
        }
    }


@pytest.fixture
def network_condition_configs():
    """Different network condition configurations for testing."""
    return {
        "perfect_network": {
            "latency_ms": 0,
            "jitter_ms": 0,
            "packet_loss_percent": 0,
            "bandwidth_kbps": 1000000,  # Unlimited
            "connection_stability": 1.0
        },
        "good_network": {
            "latency_ms": 50,
            "jitter_ms": 5,
            "packet_loss_percent": 0.1,
            "bandwidth_kbps": 1000,
            "connection_stability": 0.99
        },
        "poor_network": {
            "latency_ms": 200,
            "jitter_ms": 50,
            "packet_loss_percent": 2.0,
            "bandwidth_kbps": 128,
            "connection_stability": 0.95
        },
        "terrible_network": {
            "latency_ms": 500,
            "jitter_ms": 200,
            "packet_loss_percent": 10.0,
            "bandwidth_kbps": 64,
            "connection_stability": 0.80
        },
        "mobile_network": {
            "latency_ms": 150,
            "jitter_ms": 30,
            "packet_loss_percent": 1.0,
            "bandwidth_kbps": 256,
            "connection_stability": 0.90
        }
    }


@pytest.fixture
def deployment_configs():
    """Different deployment environment configurations."""
    return {
        "docker_local": {
            "ari_base_url": "http://asterisk:8088/ari",
            "external_media_host": "media-server",
            "gemini_endpoint": "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent",
            "environment": "docker",
            "scaling": "single_instance"
        },
        "kubernetes": {
            "ari_base_url": "http://asterisk-service:8088/ari",
            "external_media_host": "media-service",
            "gemini_endpoint": "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent",
            "environment": "kubernetes",
            "scaling": "horizontal_pod_autoscaler"
        },
        "cloud_production": {
            "ari_base_url": "https://asterisk.example.com:8088/ari",
            "external_media_host": "media.example.com",
            "gemini_endpoint": "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent",
            "environment": "production",
            "scaling": "auto_scaling_group"
        }
    }