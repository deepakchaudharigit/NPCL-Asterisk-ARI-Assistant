"""
Unit tests for Real-time ARI Handler.
Tests ARI event handling, call management, and component integration.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
import requests

from src.voice_assistant.telephony.realtime_ari_handler import (
    RealTimeARIHandler,
    RealTimeARIConfig,
    ARIEvent
)
from src.voice_assistant.core.session_manager import SessionState, CallDirection
from tests.mocks.mock_asterisk import MockAsteriskARIServer


@pytest.mark.unit
class TestRealTimeARIConfig:
    """Test Real-time ARI configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = RealTimeARIConfig(
            ari_base_url="http://localhost:8088/ari",
            ari_username="asterisk",
            ari_password="1234"
        )
        
        assert config.ari_base_url == "http://localhost:8088/ari"
        assert config.ari_username == "asterisk"
        assert config.ari_password == "1234"
        assert config.stasis_app == "gemini-voice-assistant"
        assert config.external_media_host == "localhost"
        assert config.external_media_port == 8090
        assert config.auto_answer == True
        assert config.enable_recording == False
        assert config.max_call_duration == 3600
        assert config.audio_format == "slin16"
        assert config.sample_rate == 16000
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = RealTimeARIConfig(
            ari_base_url="http://custom:8088/ari",
            ari_username="custom_user",
            ari_password="custom_pass",
            stasis_app="custom-app",
            external_media_host="custom-host",
            external_media_port=9090,
            auto_answer=False,
            enable_recording=True,
            max_call_duration=7200,
            audio_format="ulaw",
            sample_rate=8000
        )
        
        assert config.ari_base_url == "http://custom:8088/ari"
        assert config.ari_username == "custom_user"
        assert config.ari_password == "custom_pass"
        assert config.stasis_app == "custom-app"
        assert config.external_media_host == "custom-host"
        assert config.external_media_port == 9090
        assert config.auto_answer == False
        assert config.enable_recording == True
        assert config.max_call_duration == 7200
        assert config.audio_format == "ulaw"
        assert config.sample_rate == 8000


@pytest.mark.unit
class TestARIEvent:
    """Test ARI event model."""
    
    def test_ari_event_creation(self, sample_ari_events):
        """Test ARI event creation from data."""
        stasis_start_data = sample_ari_events["stasis_start"]
        
        event = ARIEvent(**stasis_start_data)
        
        assert event.type == "StasisStart"
        assert event.application == "gemini-voice-assistant"
        assert event.timestamp == "2024-01-01T12:00:00.000Z"
        assert event.channel is not None
        assert event.channel["id"] == "test-channel-123"
        assert event.channel["caller"]["number"] == "1234567890"
    
    def test_ari_event_optional_fields(self):
        """Test ARI event with minimal data."""
        minimal_data = {
            "type": "TestEvent",
            "application": "test-app",
            "timestamp": "2024-01-01T12:00:00.000Z"
        }
        
        event = ARIEvent(**minimal_data)
        
        assert event.type == "TestEvent"
        assert event.application == "test-app"
        assert event.timestamp == "2024-01-01T12:00:00.000Z"
        assert event.channel is None
        assert event.bridge is None
        assert event.recording is None
        assert event.playback is None


@pytest.mark.unit
class TestRealTimeARIHandler:
    """Test Real-time ARI handler functionality."""
    
    @pytest.mark.asyncio
    async def test_handler_initialization(self, test_settings):
        """Test handler initialization."""
        config = RealTimeARIConfig(
            ari_base_url=test_settings.ari_base_url,
            ari_username=test_settings.ari_username,
            ari_password=test_settings.ari_password
        )
        
        handler = RealTimeARIHandler(config)
        
        assert handler.config == config
        assert handler.session_manager is not None
        assert handler.gemini_client is not None
        assert handler.external_media_handler is not None
        assert len(handler.active_calls) == 0
        assert not handler.is_running
        assert len(handler.event_handlers) > 0
        
        # Cleanup
        await handler.session_manager.stop_cleanup_task()
    
    @pytest.mark.asyncio
    async def test_start_stop_handler(self, test_settings):
        """Test starting and stopping the handler."""
        config = RealTimeARIConfig(
            ari_base_url=test_settings.ari_base_url,
            ari_username=test_settings.ari_username,
            ari_password=test_settings.ari_password
        )
        
        handler = RealTimeARIHandler(config)
        
        # Mock external dependencies
        handler.gemini_client.connect = AsyncMock(return_value=True)
        handler.external_media_handler.start_server = AsyncMock(return_value=True)
        handler.external_media_handler.stop_server = AsyncMock()
        handler.gemini_client.disconnect = AsyncMock()
        
        # Start handler
        success = await handler.start()
        assert success
        assert handler.is_running
        
        # Stop handler
        await handler.stop()
        assert not handler.is_running
        
        # Verify cleanup calls
        handler.external_media_handler.stop_server.assert_called_once()
        handler.gemini_client.disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_handler_failure(self, test_settings):
        """Test handler start failure scenarios."""
        config = RealTimeARIConfig(
            ari_base_url=test_settings.ari_base_url,
            ari_username=test_settings.ari_username,
            ari_password=test_settings.ari_password
        )
        
        handler = RealTimeARIHandler(config)
        
        # Mock Gemini connection failure
        handler.gemini_client.connect = AsyncMock(return_value=False)
        handler.external_media_handler.start_server = AsyncMock(return_value=True)
        
        success = await handler.start()
        assert not success
        assert not handler.is_running
    
    @pytest.mark.asyncio
    async def test_handle_stasis_start(self, test_settings, sample_ari_events):
        """Test handling StasisStart event."""
        config = RealTimeARIConfig(
            ari_base_url=test_settings.ari_base_url,
            ari_username=test_settings.ari_username,
            ari_password=test_settings.ari_password
        )
        
        handler = RealTimeARIHandler(config)
        
        # Mock dependencies
        handler._answer_call = AsyncMock(return_value=True)
        handler._start_external_media = AsyncMock(return_value=True)
        handler.gemini_client.start_conversation = AsyncMock(return_value="session-123")
        
        # Track events
        events = []
        
        async def event_tracker(data):
            events.append(data)
        
        handler.register_event_handler("call_started", event_tracker)
        
        # Handle StasisStart event
        result = await handler.handle_ari_event(sample_ari_events["stasis_start"])
        
        assert result["status"] == "handled"
        assert result["action"] == "call_started"
        assert "session_id" in result
        
        # Verify call was tracked
        channel_id = sample_ari_events["stasis_start"]["channel"]["id"]
        assert channel_id in handler.active_calls
        
        # Verify event was triggered
        assert len(events) == 1
        assert events[0]["channel_id"] == channel_id
        
        # Verify methods were called
        handler._answer_call.assert_called_once_with(channel_id)
        handler._start_external_media.assert_called_once_with(channel_id)
        handler.gemini_client.start_conversation.assert_called_once()
        
        await handler.session_manager.stop_cleanup_task()
    
    @pytest.mark.asyncio
    async def test_handle_stasis_end(self, test_settings, sample_ari_events):
        """Test handling StasisEnd event."""
        config = RealTimeARIConfig(
            ari_base_url=test_settings.ari_base_url,
            ari_username=test_settings.ari_username,
            ari_password=test_settings.ari_password
        )
        
        handler = RealTimeARIHandler(config)
        
        # Setup active call
        channel_id = sample_ari_events["stasis_end"]["channel"]["id"]
        handler.active_calls[channel_id] = {
            "session_id": "test-session",
            "start_time": 123456.789,
            "state": "active"
        }
        
        # Mock _end_call method
        handler._end_call = AsyncMock()
        
        # Handle StasisEnd event
        result = await handler.handle_ari_event(sample_ari_events["stasis_end"])
        
        assert result["status"] == "handled"
        assert result["action"] == "call_ended"
        
        # Verify _end_call was called
        handler._end_call.assert_called_once_with(channel_id)
        
        await handler.session_manager.stop_cleanup_task()
    
    @pytest.mark.asyncio
    async def test_handle_channel_state_change(self, test_settings, sample_ari_events):
        """Test handling ChannelStateChange event."""
        config = RealTimeARIConfig(
            ari_base_url=test_settings.ari_base_url,
            ari_username=test_settings.ari_username,
            ari_password=test_settings.ari_password
        )
        
        handler = RealTimeARIHandler(config)
        
        # Setup active call
        channel_id = sample_ari_events["channel_state_change"]["channel"]["id"]
        handler.active_calls[channel_id] = {
            "session_id": "test-session",
            "start_time": 123456.789,
            "state": "initializing"
        }
        
        # Handle ChannelStateChange event
        result = await handler.handle_ari_event(sample_ari_events["channel_state_change"])
        
        assert result["status"] == "handled"
        assert result["action"] == "state_updated"
        
        # Verify state was updated
        assert handler.active_calls[channel_id]["state"] == "up"
        
        await handler.session_manager.stop_cleanup_task()
    
    @pytest.mark.asyncio
    async def test_handle_hangup_request(self, test_settings):
        """Test handling hangup request."""
        config = RealTimeARIConfig(
            ari_base_url=test_settings.ari_base_url,
            ari_username=test_settings.ari_username,
            ari_password=test_settings.ari_password
        )
        
        handler = RealTimeARIHandler(config)
        
        # Mock _end_call method
        handler._end_call = AsyncMock()
        
        hangup_event = {
            "type": "ChannelHangupRequest",
            "application": "gemini-voice-assistant",
            "timestamp": "2024-01-01T12:05:00.000Z",
            "channel": {
                "id": "test-channel-123",
                "name": "SIP/test-00000001"
            }
        }
        
        result = await handler.handle_ari_event(hangup_event)
        
        assert result["status"] == "handled"
        assert result["action"] == "hangup_processed"
        
        handler._end_call.assert_called_once_with("test-channel-123")
        
        await handler.session_manager.stop_cleanup_task()
    
    @pytest.mark.asyncio
    async def test_handle_unknown_event(self, test_settings):
        """Test handling unknown event type."""
        config = RealTimeARIConfig(
            ari_base_url=test_settings.ari_base_url,
            ari_username=test_settings.ari_username,
            ari_password=test_settings.ari_password
        )
        
        handler = RealTimeARIHandler(config)
        
        unknown_event = {
            "type": "UnknownEvent",
            "application": "gemini-voice-assistant",
            "timestamp": "2024-01-01T12:00:00.000Z"
        }
        
        result = await handler.handle_ari_event(unknown_event)
        
        assert result["status"] == "ignored"
        assert result["event_type"] == "UnknownEvent"
        
        await handler.session_manager.stop_cleanup_task()
    
    @pytest.mark.asyncio
    @patch('requests.post')
    async def test_answer_call(self, mock_post, test_settings):
        """Test answering a call."""
        config = RealTimeARIConfig(
            ari_base_url=test_settings.ari_base_url,
            ari_username=test_settings.ari_username,
            ari_password=test_settings.ari_password
        )
        
        handler = RealTimeARIHandler(config)
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        success = await handler._answer_call("test-channel-123")
        
        assert success
        mock_post.assert_called_once()
        
        # Verify correct URL and auth
        call_args = mock_post.call_args
        assert "test-channel-123/answer" in call_args[0][0]  # First positional argument is URL
        assert call_args[1]["auth"] == (config.ari_username, config.ari_password)
        
        await handler.session_manager.stop_cleanup_task()
    
    @pytest.mark.asyncio
    @patch('requests.post')
    async def test_start_external_media(self, mock_post, test_settings):
        """Test starting external media."""
        config = RealTimeARIConfig(
            ari_base_url=test_settings.ari_base_url,
            ari_username=test_settings.ari_username,
            ari_password=test_settings.ari_password
        )
        
        handler = RealTimeARIHandler(config)
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        success = await handler._start_external_media("test-channel-123")
        
        assert success
        mock_post.assert_called_once()
        
        # Verify correct URL and data
        call_args = mock_post.call_args
        assert "test-channel-123/externalMedia" in call_args[0][0]  # First positional argument is URL
        assert "json" in call_args[1]
        
        json_data = call_args[1]["json"]
        assert json_data["app"] == config.stasis_app
        assert json_data["format"] == config.audio_format
        assert json_data["direction"] == "both"
        
        await handler.session_manager.stop_cleanup_task()
    
    @pytest.mark.asyncio
    async def test_end_call(self, test_settings):
        """Test ending a call."""
        config = RealTimeARIConfig(
            ari_base_url=test_settings.ari_base_url,
            ari_username=test_settings.ari_username,
            ari_password=test_settings.ari_password
        )
        
        handler = RealTimeARIHandler(config)
        
        # Setup active call
        channel_id = "test-channel-123"
        session_id = "test-session-456"
        
        handler.active_calls[channel_id] = {
            "session_id": session_id,
            "start_time": 123456.789,
            "state": "active"
        }
        
        # Track events
        events = []
        
        async def event_tracker(data):
            events.append(data)
        
        handler.register_event_handler("call_ended", event_tracker)
        
        # End call
        await handler._end_call(channel_id)
        
        # Verify call was removed
        assert channel_id not in handler.active_calls
        
        # Verify event was triggered
        assert len(events) == 1
        assert events[0]["channel_id"] == channel_id
        assert events[0]["session_id"] == session_id
        
        await handler.session_manager.stop_cleanup_task()
    
    @pytest.mark.asyncio
    async def test_gemini_audio_response_handling(self, test_settings):
        """Test handling Gemini audio response."""
        config = RealTimeARIConfig(
            ari_base_url=test_settings.ari_base_url,
            ari_username=test_settings.ari_username,
            ari_password=test_settings.ari_password
        )
        
        handler = RealTimeARIHandler(config)
        
        # Setup active call
        handler.active_calls["test-channel"] = {
            "session_id": "test-session",
            "start_time": 123456.789,
            "state": "active"
        }
        
        # Mock external media handler
        handler.external_media_handler.send_audio_to_channel = AsyncMock(return_value=True)
        
        # Track events
        events = []
        
        async def event_tracker(data):
            events.append(data)
        
        handler.register_event_handler("response_generated", event_tracker)
        
        # Simulate Gemini audio response
        test_audio = b"test_audio_data"
        await handler._handle_gemini_audio_response({
            "audio_data": test_audio,
            "is_delta": True
        })
        
        # Verify audio was sent to channel
        handler.external_media_handler.send_audio_to_channel.assert_called_once_with(
            "test-channel", test_audio
        )
        
        # Verify event was triggered
        assert len(events) == 1
        assert events[0]["audio_size"] == len(test_audio)
        assert events[0]["is_delta"] == True
        
        await handler.session_manager.stop_cleanup_task()
    
    @pytest.mark.asyncio
    async def test_user_speech_events(self, test_settings):
        """Test handling user speech start/stop events."""
        config = RealTimeARIConfig(
            ari_base_url=test_settings.ari_base_url,
            ari_username=test_settings.ari_username,
            ari_password=test_settings.ari_password
        )
        
        handler = RealTimeARIHandler(config)
        
        # Setup active call
        session_id = "test-session"
        handler.active_calls["test-channel"] = {
            "session_id": session_id,
            "start_time": 123456.789,
            "state": "active"
        }
        
        # Mock Gemini client methods
        handler.gemini_client.commit_audio_buffer = AsyncMock()
        handler.gemini_client.create_response = AsyncMock()
        
        # Track events
        events = []
        
        async def event_tracker(data):
            events.append(data)
        
        handler.register_event_handler("speech_detected", event_tracker)
        
        # Test speech started
        await handler._handle_user_speech_started({"type": "started"})
        
        # Test speech stopped
        await handler._handle_user_speech_stopped({"type": "stopped"})
        
        # Verify Gemini methods were called
        handler.gemini_client.commit_audio_buffer.assert_called_once()
        handler.gemini_client.create_response.assert_called_once()
        
        # Verify events were triggered
        assert len(events) == 2
        assert events[0]["type"] == "started"
        assert events[1]["type"] == "stopped"
        
        await handler.session_manager.stop_cleanup_task()
    
    def test_get_system_status(self, test_settings):
        """Test getting system status."""
        config = RealTimeARIConfig(
            ari_base_url=test_settings.ari_base_url,
            ari_username=test_settings.ari_username,
            ari_password=test_settings.ari_password
        )
        
        handler = RealTimeARIHandler(config)
        
        # Add some active calls
        handler.active_calls["channel1"] = {"session_id": "session1"}
        handler.active_calls["channel2"] = {"session_id": "session2"}
        
        # Mock component status
        handler.session_manager.get_session_stats = Mock(return_value={"total": 2})
        handler.gemini_client.get_connection_status = Mock(return_value={"connected": True})
        handler.external_media_handler.get_server_stats = Mock(return_value={"running": True})
        
        status = handler.get_system_status()
        
        assert status["is_running"] == False  # Not started
        assert status["active_calls"] == 2
        assert "channel1" in status["calls"]
        assert "channel2" in status["calls"]
        assert "session_stats" in status
        assert "gemini_status" in status
        assert "external_media_stats" in status
        assert "config" in status
        
        # Verify config values
        config_data = status["config"]
        assert config_data["stasis_app"] == config.stasis_app
        assert config_data["audio_format"] == config.audio_format
    
    def test_get_call_info(self, test_settings):
        """Test getting call information."""
        config = RealTimeARIConfig(
            ari_base_url=test_settings.ari_base_url,
            ari_username=test_settings.ari_username,
            ari_password=test_settings.ari_password
        )
        
        handler = RealTimeARIHandler(config)
        
        # Setup call and session
        channel_id = "test-channel"
        session_id = "test-session"
        
        handler.active_calls[channel_id] = {
            "session_id": session_id,
            "start_time": 123456.789,
            "state": "active"
        }
        
        # Mock session and external media info
        mock_session = Mock()
        mock_session.get_session_summary.return_value = {"summary": "data"}
        handler.session_manager.get_session = Mock(return_value=mock_session)
        handler.external_media_handler.get_connection_info = Mock(return_value={"connection": "info"})
        
        call_info = handler.get_call_info(channel_id)
        
        assert call_info is not None
        assert "call_info" in call_info
        assert "session_summary" in call_info
        assert "external_media" in call_info
        
        # Test non-existent call
        non_existent_info = handler.get_call_info("non-existent")
        assert non_existent_info is None
    
    def test_event_handler_registration(self, test_settings):
        """Test event handler registration."""
        config = RealTimeARIConfig(
            ari_base_url=test_settings.ari_base_url,
            ari_username=test_settings.ari_username,
            ari_password=test_settings.ari_password
        )
        
        handler = RealTimeARIHandler(config)
        
        test_handler = Mock()
        handler.register_event_handler("test_event", test_handler)
        
        assert "test_event" in handler.event_handlers
        assert test_handler in handler.event_handlers["test_event"]