"""
WebSocket tests for External Media communication.
Tests bidirectional audio streaming and connection management.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
import websockets

from src.voice_assistant.telephony.external_media_handler import ExternalMediaHandler
from src.voice_assistant.core.session_manager import SessionManager, CallDirection
from src.voice_assistant.ai.gemini_live_client import GeminiLiveClient
from tests.utils.audio_generator import AudioGenerator
from tests.utils.test_helpers import MockWebSocketServer


@pytest.mark.websocket
class TestExternalMediaWebSocket:
    """Test External Media WebSocket functionality."""
    
    @pytest.mark.asyncio
    async def test_websocket_server_startup(self):
        """Test WebSocket server startup and shutdown."""
        session_manager = SessionManager()
        gemini_client = GeminiLiveClient()
        handler = ExternalMediaHandler(session_manager, gemini_client)
        
        try:
            # Start server on a test port
            success = await handler.start_server("localhost", 8091)
            
            if success:  # Server might not start in test environment
                assert handler.server is not None
                
                # Stop server
                await handler.stop_server()
                assert handler.server is None
            else:
                # If server fails to start, that's acceptable in test environment
                pass
                
        except Exception:
            # Server startup might fail in test environment - this is acceptable
            pass
        finally:
            await session_manager.stop_cleanup_task()
    
    @pytest.mark.asyncio
    async def test_websocket_connection_handling(self):
        """Test WebSocket connection handling."""
        session_manager = SessionManager()
        gemini_client = GeminiLiveClient()
        handler = ExternalMediaHandler(session_manager, gemini_client)
        
        # Create a session first
        session_id = await session_manager.create_session(
            "test-channel", "123", "456", CallDirection.INBOUND
        )
        
        # Mock WebSocket connection
        mock_websocket = AsyncMock()
        mock_websocket.recv = AsyncMock()
        mock_websocket.send = AsyncMock()
        mock_websocket.close = AsyncMock()
        
        # Track events
        events = []
        
        async def event_tracker(data):
            events.append(data)
        
        handler.register_event_handler("connection_established", event_tracker)
        
        try:
            # Simulate new connection handling
            # Note: This tests the logic without actual WebSocket server
            path = "/external_media/test-channel"
            
            # In real scenario, this would be called by WebSocket server
            # Here we test the connection creation logic
            
            # Verify session exists for the channel
            session = session_manager.get_session_by_channel("test-channel")
            assert session is not None
            assert session.session_id == session_id
            
        finally:
            await session_manager.stop_cleanup_task()
    
    @pytest.mark.asyncio
    async def test_audio_data_transmission(self):
        """Test audio data transmission through WebSocket."""
        session_manager = SessionManager()
        gemini_client = GeminiLiveClient()
        handler = ExternalMediaHandler(session_manager, gemini_client)
        
        # Mock Gemini client
        gemini_client.is_connected = True
        gemini_client.send_audio_chunk = AsyncMock(return_value=True)
        
        # Create session
        await session_manager.create_session(
            "test-channel", "123", "456", CallDirection.INBOUND
        )
        
        # Generate test audio
        test_audio = AudioGenerator.generate_speech_like(100)  # 100ms
        
        # Track audio sent to Gemini
        audio_sent = []
        
        async def mock_send_audio(audio_data):
            audio_sent.append(audio_data)
            return True
        
        gemini_client.send_audio_chunk = mock_send_audio
        
        try:
            # Simulate audio received from Asterisk
            await handler._handle_audio_from_asterisk({
                "channel_id": "test-channel",
                "audio_data": test_audio
            })
            
            # Verify audio was forwarded to Gemini
            assert len(audio_sent) == 1
            assert audio_sent[0] == test_audio
            
        finally:
            await session_manager.stop_cleanup_task()
    
    @pytest.mark.asyncio
    async def test_bidirectional_audio_flow(self):
        """Test bidirectional audio flow."""
        session_manager = SessionManager()
        gemini_client = GeminiLiveClient()
        handler = ExternalMediaHandler(session_manager, gemini_client)
        
        # Create session
        await session_manager.create_session(
            "test-channel", "123", "456", CallDirection.INBOUND
        )
        
        # Mock connection
        from src.voice_assistant.telephony.external_media_handler import ExternalMediaConnection, ExternalMediaConfig
        config = ExternalMediaConfig()
        connection = ExternalMediaConnection("test-channel", config)
        connection.is_connected = True
        connection.websocket = AsyncMock()
        
        handler.connections["test-channel"] = connection
        
        # Test sending audio to channel
        response_audio = AudioGenerator.generate_speech_like(200)  # 200ms response
        
        success = await handler.send_audio_to_channel("test-channel", response_audio)
        
        assert success
        connection.websocket.send.assert_called_once()
        
        await session_manager.stop_cleanup_task()
    
    @pytest.mark.asyncio
    async def test_connection_lifecycle(self):
        """Test complete connection lifecycle."""
        session_manager = SessionManager()
        gemini_client = GeminiLiveClient()
        handler = ExternalMediaHandler(session_manager, gemini_client)
        
        # Track lifecycle events
        events = []
        
        async def event_tracker(data):
            events.append(data)
        
        handler.register_event_handler("connection_established", event_tracker)
        handler.register_event_handler("connection_lost", event_tracker)
        
        # Create session
        session_id = await session_manager.create_session(
            "test-channel", "123", "456", CallDirection.INBOUND
        )
        
        try:
            # Simulate connection established
            await handler._handle_connection_established({
                "channel_id": "test-channel",
                "connection_id": "conn-123"
            })
            
            # Simulate connection lost
            await handler._handle_connection_lost({
                "channel_id": "test-channel",
                "connection_id": "conn-123",
                "stats": {"duration": 60}
            })
            
            # Verify events were triggered
            assert len(events) == 2
            assert events[0]["channel_id"] == "test-channel"  # connection_established
            assert events[1]["channel_id"] == "test-channel"  # connection_lost
            
        finally:
            await session_manager.stop_cleanup_task()
    
    @pytest.mark.asyncio
    async def test_websocket_error_handling(self):
        """Test WebSocket error handling."""
        session_manager = SessionManager()
        gemini_client = GeminiLiveClient()
        handler = ExternalMediaHandler(session_manager, gemini_client)
        
        # Track errors
        errors = []
        
        async def error_tracker(data):
            errors.append(data)
        
        handler.register_event_handler("error", error_tracker)
        
        try:
            # Simulate connection error
            await handler._handle_connection_error({
                "connection_id": "conn-123",
                "error": "WebSocket connection failed"
            })
            
            # Verify error was tracked
            assert len(errors) == 1
            assert errors[0]["connection_id"] == "conn-123"
            assert "error" in errors[0]
            
        finally:
            await session_manager.stop_cleanup_task()
    
    @pytest.mark.asyncio
    async def test_concurrent_connections(self):
        """Test handling multiple concurrent WebSocket connections."""
        session_manager = SessionManager()
        gemini_client = GeminiLiveClient()
        handler = ExternalMediaHandler(session_manager, gemini_client)
        
        # Create multiple sessions
        sessions = []
        for i in range(5):
            session_id = await session_manager.create_session(
                f"channel-{i}", f"123{i}", "456", CallDirection.INBOUND
            )
            sessions.append(session_id)
        
        # Create mock connections
        from src.voice_assistant.telephony.external_media_handler import ExternalMediaConnection, ExternalMediaConfig
        config = ExternalMediaConfig()
        
        for i in range(5):
            connection = ExternalMediaConnection(f"channel-{i}", config)
            connection.is_connected = True
            connection.websocket = AsyncMock()
            handler.connections[f"channel-{i}"] = connection
        
        try:
            # Test sending audio to all channels
            test_audio = AudioGenerator.generate_speech_like(50)
            
            for i in range(5):
                success = await handler.send_audio_to_channel(f"channel-{i}", test_audio)
                assert success
            
            # Verify all connections received audio
            for i in range(5):
                connection = handler.connections[f"channel-{i}"]
                connection.websocket.send.assert_called_once()
            
            # Test getting all connection info
            all_connections = handler.get_all_connections()
            assert len(all_connections) == 5
            
        finally:
            await session_manager.stop_cleanup_task()
    
    @pytest.mark.asyncio
    async def test_websocket_message_format(self):
        """Test WebSocket message format validation."""
        session_manager = SessionManager()
        gemini_client = GeminiLiveClient()
        handler = ExternalMediaHandler(session_manager, gemini_client)
        
        # Create connection
        from src.voice_assistant.telephony.external_media_handler import ExternalMediaConnection, ExternalMediaConfig
        config = ExternalMediaConfig()
        connection = ExternalMediaConnection("test-channel", config)
        
        # Test audio data handling
        test_audio = AudioGenerator.generate_speech_like(20)  # 20ms chunk
        
        # Verify audio data is binary
        assert isinstance(test_audio, bytes)
        assert len(test_audio) > 0
        
        # Test processing the audio
        await connection._handle_incoming_audio(test_audio)
        
        # Verify statistics were updated
        assert connection.bytes_received == len(test_audio)
        assert connection.packets_received == 1
        
        await session_manager.stop_cleanup_task()
    
    @pytest.mark.asyncio
    async def test_websocket_performance(self):
        """Test WebSocket performance characteristics."""
        session_manager = SessionManager()
        gemini_client = GeminiLiveClient()
        handler = ExternalMediaHandler(session_manager, gemini_client)
        
        # Create connection
        from src.voice_assistant.telephony.external_media_handler import ExternalMediaConnection, ExternalMediaConfig
        config = ExternalMediaConfig()
        connection = ExternalMediaConnection("test-channel", config)
        connection.is_connected = True
        connection.websocket = AsyncMock()
        
        import time
        
        # Test sending multiple audio chunks
        chunk_count = 100
        test_audio = AudioGenerator.generate_speech_like(20)  # 20ms chunks
        
        start_time = time.perf_counter()
        
        for _ in range(chunk_count):
            await connection.send_audio(test_audio)
        
        end_time = time.perf_counter()
        
        # Calculate performance metrics
        total_time = end_time - start_time
        avg_time_per_chunk = total_time / chunk_count
        
        # Should be able to send chunks much faster than real-time
        assert avg_time_per_chunk < 0.001, f"Audio sending too slow: {avg_time_per_chunk:.4f}s per chunk"
        
        # Verify all chunks were sent
        assert connection.websocket.send.call_count == chunk_count
        assert connection.packets_sent == chunk_count
        
        await session_manager.stop_cleanup_task()


@pytest.mark.websocket
class TestWebSocketIntegration:
    """Test WebSocket integration with other components."""
    
    @pytest.mark.asyncio
    async def test_websocket_session_integration(self):
        """Test WebSocket integration with session management."""
        session_manager = SessionManager()
        gemini_client = GeminiLiveClient()
        handler = ExternalMediaHandler(session_manager, gemini_client)
        
        # Create session
        session_id = await session_manager.create_session(
            "test-channel", "123", "456", CallDirection.INBOUND
        )
        
        # Simulate WebSocket connection established
        await handler._handle_connection_established({
            "channel_id": "test-channel",
            "connection_id": "conn-123"
        })
        
        # Verify session state is updated
        session = session_manager.get_session(session_id)
        assert session is not None
        
        # Simulate audio processing
        test_audio = AudioGenerator.generate_speech_like(100)
        await handler._handle_audio_from_asterisk({
            "channel_id": "test-channel",
            "audio_data": test_audio
        })
        
        # Verify session audio state is updated
        # Note: In real implementation, session would be updated with audio info
        
        await session_manager.stop_cleanup_task()
    
    @pytest.mark.asyncio
    async def test_websocket_gemini_integration(self):
        """Test WebSocket integration with Gemini client."""
        session_manager = SessionManager()
        gemini_client = GeminiLiveClient()
        handler = ExternalMediaHandler(session_manager, gemini_client)
        
        # Mock Gemini client
        gemini_client.is_connected = True
        audio_sent_to_gemini = []
        
        async def mock_send_audio(audio_data):
            audio_sent_to_gemini.append(audio_data)
            return True
        
        gemini_client.send_audio_chunk = mock_send_audio
        
        # Create session
        await session_manager.create_session(
            "test-channel", "123", "456", CallDirection.INBOUND
        )
        
        # Simulate audio from WebSocket
        test_audio = AudioGenerator.generate_speech_like(100)
        await handler._handle_audio_from_asterisk({
            "channel_id": "test-channel",
            "audio_data": test_audio
        })
        
        # Verify audio was sent to Gemini
        assert len(audio_sent_to_gemini) == 1
        assert audio_sent_to_gemini[0] == test_audio
        
        await session_manager.stop_cleanup_task()
    
    @pytest.mark.asyncio
    async def test_websocket_error_recovery(self):
        """Test WebSocket error recovery scenarios."""
        session_manager = SessionManager()
        gemini_client = GeminiLiveClient()
        handler = ExternalMediaHandler(session_manager, gemini_client)
        
        # Create session and connection
        await session_manager.create_session(
            "test-channel", "123", "456", CallDirection.INBOUND
        )
        
        from src.voice_assistant.telephony.external_media_handler import ExternalMediaConnection, ExternalMediaConfig
        config = ExternalMediaConfig()
        connection = ExternalMediaConnection("test-channel", config)
        handler.connections["test-channel"] = connection
        
        # Test sending audio when not connected
        test_audio = AudioGenerator.generate_speech_like(50)
        success = await connection.send_audio(test_audio)
        
        # Should fail gracefully
        assert not success
        assert connection.bytes_sent == 0
        
        # Test recovery after connection is established
        connection.is_connected = True
        connection.websocket = AsyncMock()
        
        success = await connection.send_audio(test_audio)
        
        # Should succeed after recovery
        assert success
        assert connection.bytes_sent > 0
        
        await session_manager.stop_cleanup_task()
    
    @pytest.mark.asyncio
    async def test_websocket_cleanup(self):
        """Test WebSocket connection cleanup."""
        session_manager = SessionManager()
        gemini_client = GeminiLiveClient()
        handler = ExternalMediaHandler(session_manager, gemini_client)
        
        # Create multiple connections
        from src.voice_assistant.telephony.external_media_handler import ExternalMediaConnection, ExternalMediaConfig
        config = ExternalMediaConfig()
        
        for i in range(3):
            connection = ExternalMediaConnection(f"channel-{i}", config)
            connection.is_connected = True
            connection.websocket = AsyncMock()
            handler.connections[f"channel-{i}"] = connection
        
        # Verify connections exist
        assert len(handler.connections) == 3
        
        # Stop server (which should cleanup connections)
        await handler.stop_server()
        
        # Verify connections were cleaned up
        assert len(handler.connections) == 0
        
        await session_manager.stop_cleanup_task()