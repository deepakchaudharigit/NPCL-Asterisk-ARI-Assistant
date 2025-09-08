"""
Unit tests for Session Manager.
Tests session lifecycle, conversation tracking, and metrics.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock

from src.voice_assistant.core.session_manager import (
    SessionManager,
    ConversationSession,
    SessionState,
    CallDirection,
    CallInfo,
    ConversationTurn,
    SessionMetrics
)


@pytest.mark.unit
class TestCallInfo:
    """Test CallInfo data class."""
    
    def test_call_info_creation(self):
        """Test CallInfo creation and basic properties."""
        start_time = time.time()
        call_info = CallInfo(
            channel_id="test-channel-123",
            caller_number="1234567890",
            called_number="1000",
            direction=CallDirection.INBOUND,
            start_time=start_time
        )
        
        assert call_info.channel_id == "test-channel-123"
        assert call_info.caller_number == "1234567890"
        assert call_info.called_number == "1000"
        assert call_info.direction == CallDirection.INBOUND
        assert call_info.start_time == start_time
        assert call_info.end_time is None
        assert call_info.duration is None
    
    def test_call_duration_calculation(self):
        """Test call duration calculation."""
        start_time = time.time()
        call_info = CallInfo(
            channel_id="test-channel",
            caller_number="123",
            called_number="456",
            direction=CallDirection.INBOUND,
            start_time=start_time
        )
        
        # Simulate call end after 5 seconds
        call_info.end_time = start_time + 5.0
        duration = call_info.calculate_duration()
        
        assert duration == 5.0
        assert call_info.duration == 5.0
    
    def test_call_duration_without_end_time(self):
        """Test duration calculation when call is still active."""
        start_time = time.time() - 3.0  # Started 3 seconds ago
        call_info = CallInfo(
            channel_id="test-channel",
            caller_number="123",
            called_number="456",
            direction=CallDirection.INBOUND,
            start_time=start_time
        )
        
        duration = call_info.calculate_duration()
        
        # Should calculate duration from start to now
        assert duration >= 3.0
        assert duration < 4.0  # Should be close to 3 seconds


@pytest.mark.unit
class TestConversationTurn:
    """Test ConversationTurn data class."""
    
    def test_turn_creation(self):
        """Test conversation turn creation."""
        timestamp = time.time()
        turn = ConversationTurn(
            turn_id="turn-123",
            timestamp=timestamp,
            speaker="user",
            content_type="audio",
            content={"audio_data": b"test", "transcription": "hello"},
            duration=2.5,
            confidence=0.95
        )
        
        assert turn.turn_id == "turn-123"
        assert turn.timestamp == timestamp
        assert turn.speaker == "user"
        assert turn.content_type == "audio"
        assert turn.content["transcription"] == "hello"
        assert turn.duration == 2.5
        assert turn.confidence == 0.95
    
    def test_turn_to_dict(self):
        """Test conversation turn serialization."""
        turn = ConversationTurn(
            turn_id="turn-123",
            timestamp=123456.789,
            speaker="assistant",
            content_type="text",
            content={"text": "Hello there!"}
        )
        
        turn_dict = turn.to_dict()
        
        assert turn_dict["turn_id"] == "turn-123"
        assert turn_dict["timestamp"] == 123456.789
        assert turn_dict["speaker"] == "assistant"
        assert turn_dict["content_type"] == "text"
        assert turn_dict["content"]["text"] == "Hello there!"


@pytest.mark.unit
class TestSessionMetrics:
    """Test SessionMetrics data class."""
    
    def test_metrics_initialization(self):
        """Test metrics initialization with default values."""
        metrics = SessionMetrics()
        
        assert metrics.total_turns == 0
        assert metrics.user_turns == 0
        assert metrics.assistant_turns == 0
        assert metrics.total_audio_duration == 0.0
        assert metrics.total_processing_time == 0.0
        assert metrics.average_response_time == 0.0
        assert metrics.interruptions == 0
        assert metrics.errors == 0
    
    def test_response_time_update(self):
        """Test response time calculation."""
        metrics = SessionMetrics()
        
        # Add first response time
        metrics.update_response_time(1.0)
        assert metrics.assistant_turns == 1
        assert metrics.average_response_time == 1.0
        
        # Add second response time
        metrics.update_response_time(3.0)
        assert metrics.assistant_turns == 2
        assert metrics.average_response_time == 2.0  # (1.0 + 3.0) / 2
        
        # Add third response time
        metrics.update_response_time(2.0)
        assert metrics.assistant_turns == 3
        assert metrics.average_response_time == 2.0  # (1.0 + 3.0 + 2.0) / 3


@pytest.mark.unit
class TestConversationSession:
    """Test ConversationSession functionality."""
    
    def test_session_creation(self):
        """Test session creation with required parameters."""
        call_info = CallInfo(
            channel_id="test-channel",
            caller_number="123",
            called_number="456",
            direction=CallDirection.INBOUND,
            start_time=time.time()
        )
        
        session = ConversationSession(
            session_id="session-123",
            call_info=call_info
        )
        
        assert session.session_id == "session-123"
        assert session.call_info == call_info
        assert session.state == SessionState.INITIALIZING
        assert len(session.turns) == 0
        assert session.current_turn is None
        assert not session.is_user_speaking
        assert not session.is_assistant_speaking
        assert not session.is_processing
        assert isinstance(session.metrics, SessionMetrics)
    
    def test_session_state_update(self):
        """Test session state updates."""
        call_info = CallInfo("ch", "123", "456", CallDirection.INBOUND, time.time())
        session = ConversationSession("sess", call_info)
        
        initial_time = session.updated_at
        
        # Update state
        session.update_state(SessionState.ACTIVE)
        
        assert session.state == SessionState.ACTIVE
        assert session.updated_at > initial_time
    
    def test_add_conversation_turn(self):
        """Test adding conversation turns."""
        call_info = CallInfo("ch", "123", "456", CallDirection.INBOUND, time.time())
        session = ConversationSession("sess", call_info)
        
        # Add user turn
        user_turn = ConversationTurn(
            turn_id="turn-1",
            timestamp=time.time(),
            speaker="user",
            content_type="audio",
            content={"transcription": "Hello"},
            duration=1.5
        )
        
        session.add_turn(user_turn)
        
        assert len(session.turns) == 1
        assert session.metrics.total_turns == 1
        assert session.metrics.user_turns == 1
        assert session.metrics.assistant_turns == 0
        assert session.metrics.total_audio_duration == 1.5
        
        # Add assistant turn
        assistant_turn = ConversationTurn(
            turn_id="turn-2",
            timestamp=time.time(),
            speaker="assistant",
            content_type="audio",
            content={"text": "Hi there!"},
            duration=2.0
        )
        
        session.add_turn(assistant_turn)
        
        assert len(session.turns) == 2
        assert session.metrics.total_turns == 2
        assert session.metrics.user_turns == 1
        assert session.metrics.assistant_turns == 1
        assert session.metrics.total_audio_duration == 3.5
    
    def test_conversation_history(self):
        """Test conversation history retrieval."""
        call_info = CallInfo("ch", "123", "456", CallDirection.INBOUND, time.time())
        session = ConversationSession("sess", call_info)
        
        # Add multiple turns
        for i in range(5):
            turn = ConversationTurn(
                turn_id=f"turn-{i}",
                timestamp=time.time(),
                speaker="user" if i % 2 == 0 else "assistant",
                content_type="text",
                content={"text": f"Message {i}"}
            )
            session.add_turn(turn)
        
        # Get all history
        all_history = session.get_conversation_history()
        assert len(all_history) == 5
        
        # Get limited history
        limited_history = session.get_conversation_history(limit=3)
        assert len(limited_history) == 3
        
        # Should get the last 3 turns
        assert limited_history[0]["turn_id"] == "turn-2"
        assert limited_history[1]["turn_id"] == "turn-3"
        assert limited_history[2]["turn_id"] == "turn-4"
    
    def test_session_summary(self):
        """Test session summary generation."""
        start_time = time.time()
        call_info = CallInfo("ch", "123", "456", CallDirection.INBOUND, start_time)
        session = ConversationSession("sess", call_info)
        
        # Add some turns and metrics
        session.add_turn(ConversationTurn("t1", time.time(), "user", "audio", {}, 1.0))
        session.add_turn(ConversationTurn("t2", time.time(), "assistant", "audio", {}, 2.0))
        session.metrics.interruptions = 1
        session.metrics.errors = 0
        
        summary = session.get_session_summary()
        
        assert summary["session_id"] == "sess"
        assert summary["state"] == SessionState.INITIALIZING.value
        assert "duration" in summary
        assert summary["call_info"]["channel_id"] == "ch"
        assert summary["call_info"]["caller_number"] == "123"
        assert summary["call_info"]["direction"] == CallDirection.INBOUND.value
        assert summary["metrics"]["total_turns"] == 2
        assert summary["metrics"]["user_turns"] == 1
        assert summary["metrics"]["assistant_turns"] == 1
        assert summary["metrics"]["interruptions"] == 1
        assert summary["current_state"]["is_user_speaking"] == False


@pytest.mark.unit
class TestSessionManager:
    """Test SessionManager functionality."""
    
    @pytest.mark.asyncio
    async def test_session_manager_initialization(self):
        """Test session manager initialization."""
        manager = SessionManager()
        
        assert len(manager.sessions) == 0
        assert len(manager.channel_to_session) == 0
        assert "session_created" in manager.event_handlers
        assert "session_ended" in manager.event_handlers
        assert manager.cleanup_task is None
        
        await manager.stop_cleanup_task()  # Cleanup
    
    @pytest.mark.asyncio
    async def test_create_session(self):
        """Test session creation."""
        manager = SessionManager()
        
        # Track events
        events = []
        async def event_handler(data):
            events.append(data)
        
        manager.register_event_handler("session_created", event_handler)
        
        # Create session
        session_id = await manager.create_session(
            channel_id="test-channel",
            caller_number="1234567890",
            called_number="1000",
            direction=CallDirection.INBOUND,
            config={"test": "config"}
        )
        
        assert session_id is not None
        assert session_id in manager.sessions
        assert "test-channel" in manager.channel_to_session
        assert manager.channel_to_session["test-channel"] == session_id
        
        # Check session properties
        session = manager.sessions[session_id]
        assert session.session_id == session_id
        assert session.call_info.channel_id == "test-channel"
        assert session.call_info.caller_number == "1234567890"
        assert session.call_info.called_number == "1000"
        assert session.call_info.direction == CallDirection.INBOUND
        assert session.config["test"] == "config"
        
        # Check event was triggered
        assert len(events) == 1
        assert events[0]["session_id"] == session_id
        
        await manager.stop_cleanup_task()
    
    @pytest.mark.asyncio
    async def test_end_session(self):
        """Test session ending."""
        manager = SessionManager()
        
        # Track events
        events = []
        async def event_handler(data):
            events.append(data)
        
        manager.register_event_handler("session_ended", event_handler)
        
        # Create and end session
        session_id = await manager.create_session(
            "test-channel", "123", "456", CallDirection.INBOUND
        )
        
        success = await manager.end_session(session_id)
        
        assert success
        assert session_id in manager.sessions  # Session still exists but marked as ended
        assert "test-channel" not in manager.channel_to_session  # Removed from mapping
        
        # Check session state
        session = manager.sessions[session_id]
        assert session.state == SessionState.ENDED
        assert session.call_info.end_time is not None
        assert session.call_info.duration is not None
        
        # Check event was triggered
        ended_events = [e for e in events if "summary" in e]
        assert len(ended_events) == 1
        
        await manager.stop_cleanup_task()
    
    @pytest.mark.asyncio
    async def test_get_session_methods(self):
        """Test session retrieval methods."""
        manager = SessionManager()
        
        # Create session
        session_id = await manager.create_session(
            "test-channel", "123", "456", CallDirection.INBOUND
        )
        
        # Test get_session
        session = manager.get_session(session_id)
        assert session is not None
        assert session.session_id == session_id
        
        # Test get_session_by_channel
        session_by_channel = manager.get_session_by_channel("test-channel")
        assert session_by_channel is not None
        assert session_by_channel.session_id == session_id
        
        # Test non-existent session
        assert manager.get_session("non-existent") is None
        assert manager.get_session_by_channel("non-existent") is None
        
        await manager.stop_cleanup_task()
    
    @pytest.mark.asyncio
    async def test_update_session_state(self):
        """Test session state updates."""
        manager = SessionManager()
        
        # Track events
        events = []
        async def event_handler(data):
            events.append(data)
        
        manager.register_event_handler("state_changed", event_handler)
        
        # Create session and update state
        session_id = await manager.create_session(
            "test-channel", "123", "456", CallDirection.INBOUND
        )
        
        success = await manager.update_session_state(session_id, SessionState.ACTIVE)
        
        assert success
        
        session = manager.get_session(session_id)
        assert session.state == SessionState.ACTIVE
        
        # Check event was triggered
        state_events = [e for e in events if "old_state" in e]
        assert len(state_events) == 1
        assert state_events[0]["old_state"] == SessionState.INITIALIZING.value
        assert state_events[0]["new_state"] == SessionState.ACTIVE.value
        
        await manager.stop_cleanup_task()
    
    @pytest.mark.asyncio
    async def test_add_conversation_turn(self):
        """Test adding conversation turns."""
        manager = SessionManager()
        
        # Track events
        events = []
        async def event_handler(data):
            events.append(data)
        
        manager.register_event_handler("turn_added", event_handler)
        
        # Create session
        session_id = await manager.create_session(
            "test-channel", "123", "456", CallDirection.INBOUND
        )
        
        # Add conversation turn
        turn_id = await manager.add_conversation_turn(
            session_id=session_id,
            speaker="user",
            content_type="audio",
            content={"transcription": "Hello"},
            duration=2.5,
            confidence=0.95
        )
        
        assert turn_id is not None
        
        # Check session was updated
        session = manager.get_session(session_id)
        assert len(session.turns) == 1
        assert session.turns[0].turn_id == turn_id
        assert session.turns[0].speaker == "user"
        assert session.turns[0].content["transcription"] == "Hello"
        assert session.turns[0].duration == 2.5
        assert session.turns[0].confidence == 0.95
        
        # Check event was triggered
        turn_events = [e for e in events if "turn" in e]
        assert len(turn_events) == 1
        
        await manager.stop_cleanup_task()
    
    @pytest.mark.asyncio
    async def test_update_session_audio_state(self):
        """Test updating session audio state."""
        manager = SessionManager()
        
        session_id = await manager.create_session(
            "test-channel", "123", "456", CallDirection.INBOUND
        )
        
        # Update audio state
        success = await manager.update_session_audio_state(
            session_id=session_id,
            is_user_speaking=True,
            is_assistant_speaking=False,
            is_processing=True,
            audio_buffer_size=1024
        )
        
        assert success
        
        # Check session was updated
        session = manager.get_session(session_id)
        assert session.is_user_speaking == True
        assert session.is_assistant_speaking == False
        assert session.is_processing == True
        assert session.audio_buffer_size == 1024
        assert session.last_audio_timestamp > 0
        
        await manager.stop_cleanup_task()
    
    @pytest.mark.asyncio
    async def test_record_interruption_and_error(self):
        """Test recording interruptions and errors."""
        manager = SessionManager()
        
        # Track error events
        events = []
        async def event_handler(data):
            events.append(data)
        
        manager.register_event_handler("error", event_handler)
        
        session_id = await manager.create_session(
            "test-channel", "123", "456", CallDirection.INBOUND
        )
        
        # Record interruption
        success = await manager.record_interruption(session_id)
        assert success
        
        session = manager.get_session(session_id)
        assert session.metrics.interruptions == 1
        
        # Record error
        error_info = {"type": "test_error", "message": "Test error"}
        success = await manager.record_error(session_id, error_info)
        assert success
        
        session = manager.get_session(session_id)
        assert session.metrics.errors == 1
        
        # Check error event was triggered
        error_events = [e for e in events if "error_info" in e]
        assert len(error_events) == 1
        assert error_events[0]["error_info"] == error_info
        
        await manager.stop_cleanup_task()
    
    @pytest.mark.asyncio
    async def test_get_active_sessions(self):
        """Test getting active sessions."""
        manager = SessionManager()
        
        # Create multiple sessions with different states
        session1_id = await manager.create_session("ch1", "123", "456", CallDirection.INBOUND)
        session2_id = await manager.create_session("ch2", "789", "456", CallDirection.INBOUND)
        session3_id = await manager.create_session("ch3", "111", "456", CallDirection.INBOUND)
        
        # Update states
        await manager.update_session_state(session1_id, SessionState.ACTIVE)
        await manager.update_session_state(session2_id, SessionState.PROCESSING_AUDIO)
        await manager.end_session(session3_id)  # This one should not be active
        
        active_sessions = manager.get_active_sessions()
        
        assert len(active_sessions) == 2
        assert session1_id in active_sessions
        assert session2_id in active_sessions
        assert session3_id not in active_sessions
        
        await manager.stop_cleanup_task()
    
    @pytest.mark.asyncio
    async def test_session_stats(self):
        """Test session statistics."""
        manager = SessionManager()
        
        # Create sessions and add some data
        session1_id = await manager.create_session("ch1", "123", "456", CallDirection.INBOUND)
        session2_id = await manager.create_session("ch2", "789", "456", CallDirection.INBOUND)
        
        # Add turns and errors
        await manager.add_conversation_turn(session1_id, "user", "audio", {"text": "hi"})
        await manager.add_conversation_turn(session1_id, "assistant", "audio", {"text": "hello"})
        await manager.record_error(session1_id, {"type": "test"})
        
        await manager.update_session_state(session1_id, SessionState.ACTIVE)
        await manager.end_session(session2_id)
        
        stats = manager.get_session_stats()
        
        assert stats["total_sessions"] == 2
        assert stats["active_sessions"] == 1
        assert stats["total_turns"] == 2
        assert stats["total_errors"] == 1
        assert stats["sessions_by_state"][SessionState.ACTIVE.value] == 1
        assert stats["sessions_by_state"][SessionState.ENDED.value] == 1
        
        await manager.stop_cleanup_task()
    
    @pytest.mark.asyncio
    async def test_cleanup_task(self):
        """Test cleanup task functionality."""
        manager = SessionManager()
        
        # Start cleanup task
        await manager.start_cleanup_task()
        assert manager.cleanup_task is not None
        assert not manager.cleanup_task.done()
        
        # Stop cleanup task
        await manager.stop_cleanup_task()
        assert manager.cleanup_task.done()
    
    @pytest.mark.asyncio
    async def test_export_session_data(self):
        """Test session data export."""
        manager = SessionManager()
        
        # Create session with data
        session_id = await manager.create_session(
            "test-channel", "123", "456", CallDirection.INBOUND,
            config={"test": "config"}
        )
        
        await manager.add_conversation_turn(
            session_id, "user", "audio", {"transcription": "hello"}
        )
        
        # Export session data
        exported_data = await manager.export_session_data(session_id)
        
        assert exported_data is not None
        assert "session_info" in exported_data
        assert "conversation_history" in exported_data
        assert "config" in exported_data
        assert "exported_at" in exported_data
        
        # Check session info
        session_info = exported_data["session_info"]
        assert session_info["session_id"] == session_id
        
        # Check conversation history
        conversation_history = exported_data["conversation_history"]
        assert len(conversation_history) == 1
        assert conversation_history[0]["speaker"] == "user"
        
        # Check config
        assert exported_data["config"]["test"] == "config"
        
        # Test non-existent session
        exported_none = await manager.export_session_data("non-existent")
        assert exported_none is None
        
        await manager.stop_cleanup_task()
    
    @pytest.mark.asyncio
    async def test_event_handler_registration(self):
        """Test event handler registration and removal."""
        manager = SessionManager()
        
        events = []
        
        async def handler1(data):
            events.append("handler1")
        
        async def handler2(data):
            events.append("handler2")
        
        # Register handlers
        manager.register_event_handler("session_created", handler1)
        manager.register_event_handler("session_created", handler2)
        
        # Create session to trigger events
        await manager.create_session("test", "123", "456", CallDirection.INBOUND)
        
        # Both handlers should be called
        assert "handler1" in events
        assert "handler2" in events
        
        await manager.stop_cleanup_task()
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in session manager."""
        manager = SessionManager()
        
        # Test operations on non-existent session
        assert not await manager.update_session_state("non-existent", SessionState.ACTIVE)
        assert not await manager.update_session_audio_state("non-existent")
        assert not await manager.record_interruption("non-existent")
        assert not await manager.record_error("non-existent", {})
        assert not await manager.end_session("non-existent")
        
        # Test adding turn to non-existent session
        with pytest.raises(ValueError):
            await manager.add_conversation_turn("non-existent", "user", "audio", {})
        
        await manager.stop_cleanup_task()