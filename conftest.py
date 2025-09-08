"""
Global pytest configuration and fixtures for the Voice Assistant test suite.
"""

import pytest
import asyncio
import os
import tempfile
import time
from typing import Dict, Any
from pathlib import Path

# Import test utilities
from tests.utils.audio_generator import AudioGenerator, AudioTestPatterns
from tests.mocks.mock_asterisk import MockAsteriskARIServer, MockARIClient
from tests.mocks.mock_gemini import MockGeminiLiveAPI, MockGeminiClient

# Import application components for configuration
from src.voice_assistant.ai.gemini_live_client import GeminiLiveConfig
from src.voice_assistant.telephony.realtime_ari_handler import RealTimeARIConfig


@pytest.fixture(scope="session")
def test_settings():
    """Core test settings and configuration."""
    return {
        "ari_base_url": "http://localhost:8088/ari",
        "ari_username": "test_user",
        "ari_password": "test_pass",
        "stasis_app": "test-voice-assistant",
        "external_media_host": "localhost",
        "external_media_port": 8090,
        "sample_rate": 16000,
        "audio_format": "slin16",
        "chunk_size": 320,
        "gemini_api_key": "test-api-key",
        "gemini_model": "gemini-2.0-flash-exp",
        "gemini_voice": "Puck",
        "test_timeout": 30.0,
        "async_timeout": 5.0
    }


@pytest.fixture
def gemini_config(test_settings):
    """Gemini Live API configuration for testing."""
    return GeminiLiveConfig(
        model=test_settings["gemini_model"],
        voice=test_settings["gemini_voice"],
        input_audio_format="pcm16",
        output_audio_format="pcm16",
        input_audio_transcription=True,
        output_audio_transcription=True,
        turn_detection={
            "type": "server_vad",
            "threshold": 0.5,
            "prefix_padding_ms": 300,
            "silence_duration_ms": 500
        }
    )


@pytest.fixture
def sample_audio_data():
    """Basic audio sample for testing."""
    return AudioGenerator.generate_speech_like(1000)


@pytest.fixture
def sample_ari_events():
    """Sample ARI events for testing."""
    channel_id = "test-channel-123"
    base_timestamp = "2024-01-01T12:00:00.000Z"
    
    return {
        "stasis_start": {
            "type": "StasisStart",
            "application": "gemini-voice-assistant",
            "timestamp": base_timestamp,
            "channel": {
                "id": channel_id,
                "name": f"SIP/test-{channel_id}",
                "state": "Ring",
                "caller": {"number": "1234567890", "name": "Test Caller"},
                "connected": {"number": "1000", "name": "Voice Assistant"},
                "dialplan": {"context": "gemini-voice-assistant", "exten": "1000", "priority": 1},
                "creationtime": base_timestamp
            }
        },
        "stasis_end": {
            "type": "StasisEnd",
            "application": "gemini-voice-assistant",
            "timestamp": "2024-01-01T12:05:00.000Z",
            "channel": {"id": channel_id, "name": f"SIP/test-{channel_id}", "state": "Down"}
        },
        "channel_state_change": {
            "type": "ChannelStateChange",
            "timestamp": "2024-01-01T12:00:01.000Z",
            "channel": {"id": channel_id, "name": f"SIP/test-{channel_id}", "state": "Up"}
        }
    }


@pytest.fixture
async def mock_asterisk_server():
    """Mock Asterisk ARI server for testing."""
    server = MockAsteriskARIServer()
    yield server
    server.reset()


@pytest.fixture
def mock_gemini_client():
    """Mock Gemini client for unit testing."""
    return MockGeminiClient()


@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Automatic cleanup after each test."""
    yield
    # Cleanup any remaining async tasks
    try:
        loop = asyncio.get_event_loop()
        pending = asyncio.all_tasks(loop)
        if pending:
            for task in pending:
                if not task.done():
                    task.cancel()
    except RuntimeError:
        pass


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "audio: Audio processing tests")


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()