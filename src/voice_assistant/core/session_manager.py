"""
Session manager for handling conversation state and call management
in the Gemini Voice Assistant with Asterisk ARI integration.
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger(__name__)


class SessionState(Enum):
    """Session state enumeration"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    WAITING_FOR_INPUT = "waiting_for_input"
    PROCESSING_AUDIO = "processing_audio"
    GENERATING_RESPONSE = "generating_response"
    PLAYING_RESPONSE = "playing_response"
    PAUSED = "paused"
    ENDING = "ending"
    ENDED = "ended"
    ERROR = "error"


class CallDirection(Enum):
    """Call direction enumeration"""
    INBOUND = "inbound"
    OUTBOUND = "outbound"


@dataclass
class CallInfo:
    """Information about the call"""
    channel_id: str
    caller_number: str
    called_number: str
    direction: CallDirection
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    
    def calculate_duration(self) -> float:
        """Calculate call duration"""
        end = self.end_time or time.time()
        self.duration = end - self.start_time
        return self.duration


@dataclass
class ConversationTurn:
    """A single turn in the conversation"""
    turn_id: str
    timestamp: float
    speaker: str  # "user" or "assistant"
    content_type: str  # "audio", "text", "mixed"
    content: Dict[str, Any]  # Contains audio data, transcription, etc.
    duration: Optional[float] = None
    confidence: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "turn_id": self.turn_id,
            "timestamp": self.timestamp,
            "speaker": self.speaker,
            "content_type": self.content_type,
            "content": self.content,
            "duration": self.duration,
            "confidence": self.confidence
        }


@dataclass
class SessionMetrics:
    """Session performance metrics"""
    total_turns: int = 0
    user_turns: int = 0
    assistant_turns: int = 0
    total_audio_duration: float = 0.0
    total_processing_time: float = 0.0
    average_response_time: float = 0.0
    interruptions: int = 0
    errors: int = 0
    
    def update_response_time(self, response_time: float):
        """Update average response time"""
        total_time = self.average_response_time * self.assistant_turns
        self.assistant_turns += 1
        self.average_response_time = (total_time + response_time) / self.assistant_turns


@dataclass
class ConversationSession:
    """Manages a single conversation session"""
    session_id: str
    call_info: CallInfo
    state: SessionState = SessionState.INITIALIZING
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    
    # Conversation data
    turns: List[ConversationTurn] = field(default_factory=list)
    current_turn: Optional[ConversationTurn] = None
    
    # Session state
    is_user_speaking: bool = False
    is_assistant_speaking: bool = False
    is_processing: bool = False
    
    # Audio state
    audio_buffer_size: int = 0
    last_audio_timestamp: float = 0.0
    
    # Metrics
    metrics: SessionMetrics = field(default_factory=SessionMetrics)
    
    # Configuration
    config: Dict[str, Any] = field(default_factory=dict)
    
    def update_state(self, new_state: SessionState):
        """Update session state"""
        old_state = self.state
        self.state = new_state
        self.updated_at = time.time()
        logger.debug(f"Session {self.session_id} state: {old_state.value} -> {new_state.value}")
    
    def add_turn(self, turn: ConversationTurn):
        """Add a conversation turn"""
        self.turns.append(turn)
        self.metrics.total_turns += 1
        
        if turn.speaker == "user":
            self.metrics.user_turns += 1
        elif turn.speaker == "assistant":
            self.metrics.assistant_turns += 1
        
        if turn.duration:
            self.metrics.total_audio_duration += turn.duration
        
        self.updated_at = time.time()
        logger.debug(f"Added turn {turn.turn_id} from {turn.speaker}")
    
    def get_conversation_history(self, limit: int = None) -> List[Dict[str, Any]]:
        """Get conversation history"""
        turns = self.turns[-limit:] if limit else self.turns
        return [turn.to_dict() for turn in turns]
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get session summary"""
        duration = time.time() - self.created_at
        
        return {
            "session_id": self.session_id,
            "state": self.state.value,
            "duration": duration,
            "call_info": {
                "channel_id": self.call_info.channel_id,
                "caller_number": self.call_info.caller_number,
                "called_number": self.call_info.called_number,
                "direction": self.call_info.direction.value,
                "call_duration": self.call_info.calculate_duration()
            },
            "metrics": {
                "total_turns": self.metrics.total_turns,
                "user_turns": self.metrics.user_turns,
                "assistant_turns": self.metrics.assistant_turns,
                "total_audio_duration": self.metrics.total_audio_duration,
                "average_response_time": self.metrics.average_response_time,
                "interruptions": self.metrics.interruptions,
                "errors": self.metrics.errors
            },
            "current_state": {
                "is_user_speaking": self.is_user_speaking,
                "is_assistant_speaking": self.is_assistant_speaking,
                "is_processing": self.is_processing,
                "audio_buffer_size": self.audio_buffer_size
            }
        }


class SessionManager:
    """Manages multiple conversation sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, ConversationSession] = {}
        self.channel_to_session: Dict[str, str] = {}  # Map channel_id to session_id
        
        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = {
            "session_created": [],
            "session_ended": [],
            "state_changed": [],
            "turn_added": [],
            "error": []
        }
        
        # Cleanup task
        self.cleanup_task: Optional[asyncio.Task] = None
        self.cleanup_interval = 300  # 5 minutes
        
        logger.info("Session Manager initialized")
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """Register event handler"""
        if event_type in self.event_handlers:
            self.event_handlers[event_type].append(handler)
            logger.debug(f"Registered handler for event: {event_type}")
    
    async def create_session(self, channel_id: str, caller_number: str, 
                           called_number: str, direction: CallDirection,
                           config: Dict[str, Any] = None) -> str:
        """Create a new conversation session"""
        try:
            session_id = str(uuid.uuid4())
            
            call_info = CallInfo(
                channel_id=channel_id,
                caller_number=caller_number,
                called_number=called_number,
                direction=direction,
                start_time=time.time()
            )
            
            session = ConversationSession(
                session_id=session_id,
                call_info=call_info,
                config=config or {}
            )
            
            self.sessions[session_id] = session
            self.channel_to_session[channel_id] = session_id
            
            # Trigger event handlers
            await self._trigger_event_handlers("session_created", {
                "session_id": session_id,
                "session": session
            })
            
            logger.info(f"Created session {session_id} for channel {channel_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            raise
    
    async def end_session(self, session_id: str) -> bool:
        """End a conversation session"""
        try:
            session = self.sessions.get(session_id)
            if not session:
                logger.warning(f"Session {session_id} not found")
                return False
            
            # Update session state
            session.update_state(SessionState.ENDING)
            session.call_info.end_time = time.time()
            session.call_info.calculate_duration()
            
            # Remove from channel mapping
            if session.call_info.channel_id in self.channel_to_session:
                del self.channel_to_session[session.call_info.channel_id]
            
            # Update final state
            session.update_state(SessionState.ENDED)
            
            # Trigger event handlers
            await self._trigger_event_handlers("session_ended", {
                "session_id": session_id,
                "session": session,
                "summary": session.get_session_summary()
            })
            
            logger.info(f"Ended session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error ending session {session_id}: {e}")
            return False
    
    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """Get session by ID"""
        return self.sessions.get(session_id)
    
    def get_session_by_channel(self, channel_id: str) -> Optional[ConversationSession]:
        """Get session by channel ID"""
        session_id = self.channel_to_session.get(channel_id)
        return self.sessions.get(session_id) if session_id else None
    
    async def update_session_state(self, session_id: str, new_state: SessionState) -> bool:
        """Update session state"""
        try:
            session = self.sessions.get(session_id)
            if not session:
                return False
            
            old_state = session.state
            session.update_state(new_state)
            
            # Trigger event handlers
            await self._trigger_event_handlers("state_changed", {
                "session_id": session_id,
                "old_state": old_state.value,
                "new_state": new_state.value,
                "session": session
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating session state: {e}")
            return False
    
    async def add_conversation_turn(self, session_id: str, speaker: str, 
                                 content_type: str, content: Dict[str, Any],
                                 duration: float = None, confidence: float = None) -> str:
        """Add a conversation turn to session"""
        try:
            session = self.sessions.get(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")
            
            turn_id = str(uuid.uuid4())
            turn = ConversationTurn(
                turn_id=turn_id,
                timestamp=time.time(),
                speaker=speaker,
                content_type=content_type,
                content=content,
                duration=duration,
                confidence=confidence
            )
            
            session.add_turn(turn)
            
            # Trigger event handlers
            await self._trigger_event_handlers("turn_added", {
                "session_id": session_id,
                "turn": turn,
                "session": session
            })
            
            return turn_id
            
        except Exception as e:
            logger.error(f"Error adding conversation turn: {e}")
            raise
    
    async def update_session_audio_state(self, session_id: str, 
                                       is_user_speaking: bool = None,
                                       is_assistant_speaking: bool = None,
                                       is_processing: bool = None,
                                       audio_buffer_size: int = None) -> bool:
        """Update session audio state"""
        try:
            session = self.sessions.get(session_id)
            if not session:
                return False
            
            if is_user_speaking is not None:
                session.is_user_speaking = is_user_speaking
            
            if is_assistant_speaking is not None:
                session.is_assistant_speaking = is_assistant_speaking
            
            if is_processing is not None:
                session.is_processing = is_processing
            
            if audio_buffer_size is not None:
                session.audio_buffer_size = audio_buffer_size
            
            session.last_audio_timestamp = time.time()
            session.updated_at = time.time()
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating session audio state: {e}")
            return False
    
    async def record_interruption(self, session_id: str) -> bool:
        """Record an interruption event"""
        try:
            session = self.sessions.get(session_id)
            if not session:
                return False
            
            session.metrics.interruptions += 1
            session.updated_at = time.time()
            
            logger.debug(f"Recorded interruption for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error recording interruption: {e}")
            return False
    
    async def record_error(self, session_id: str, error_info: Dict[str, Any]) -> bool:
        """Record an error event"""
        try:
            session = self.sessions.get(session_id)
            if not session:
                return False
            
            session.metrics.errors += 1
            session.updated_at = time.time()
            
            # Trigger error event handlers
            await self._trigger_event_handlers("error", {
                "session_id": session_id,
                "error_info": error_info,
                "session": session
            })
            
            logger.debug(f"Recorded error for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error recording error: {e}")
            return False
    
    def get_active_sessions(self) -> List[str]:
        """Get list of active session IDs"""
        return [
            session_id for session_id, session in self.sessions.items()
            if session.state in [SessionState.ACTIVE, SessionState.WAITING_FOR_INPUT,
                               SessionState.PROCESSING_AUDIO, SessionState.GENERATING_RESPONSE,
                               SessionState.PLAYING_RESPONSE]
        ]
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get overall session statistics"""
        total_sessions = len(self.sessions)
        active_sessions = len(self.get_active_sessions())
        
        # Calculate aggregate metrics
        total_turns = sum(session.metrics.total_turns for session in self.sessions.values())
        total_duration = sum(
            time.time() - session.created_at if session.state != SessionState.ENDED
            else session.call_info.duration or 0
            for session in self.sessions.values()
        )
        total_errors = sum(session.metrics.errors for session in self.sessions.values())
        
        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "total_turns": total_turns,
            "total_duration": total_duration,
            "total_errors": total_errors,
            "average_session_duration": total_duration / total_sessions if total_sessions > 0 else 0,
            "sessions_by_state": {
                state.value: len([s for s in self.sessions.values() if s.state == state])
                for state in SessionState
            }
        }
    
    async def start_cleanup_task(self):
        """Start background cleanup task"""
        if self.cleanup_task is None or self.cleanup_task.done():
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Started session cleanup task")
    
    async def stop_cleanup_task(self):
        """Stop background cleanup task"""
        if self.cleanup_task and not self.cleanup_task.done():
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped session cleanup task")
    
    async def _cleanup_loop(self):
        """Background cleanup loop"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_old_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    async def _cleanup_old_sessions(self):
        """Clean up old ended sessions"""
        try:
            current_time = time.time()
            cleanup_threshold = 3600  # 1 hour
            
            sessions_to_remove = []
            
            for session_id, session in self.sessions.items():
                if (session.state == SessionState.ENDED and 
                    current_time - session.updated_at > cleanup_threshold):
                    sessions_to_remove.append(session_id)
            
            for session_id in sessions_to_remove:
                del self.sessions[session_id]
                logger.debug(f"Cleaned up old session: {session_id}")
            
            if sessions_to_remove:
                logger.info(f"Cleaned up {len(sessions_to_remove)} old sessions")
                
        except Exception as e:
            logger.error(f"Error cleaning up sessions: {e}")
    
    async def _trigger_event_handlers(self, event_type: str, event_data: Dict[str, Any]):
        """Trigger registered event handlers"""
        handlers = self.event_handlers.get(event_type, [])
        
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event_data)
                else:
                    handler(event_data)
            except Exception as e:
                logger.error(f"Error in event handler for {event_type}: {e}")
    
    async def export_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Export complete session data"""
        try:
            session = self.sessions.get(session_id)
            if not session:
                return None
            
            return {
                "session_info": session.get_session_summary(),
                "conversation_history": session.get_conversation_history(),
                "config": session.config,
                "exported_at": time.time()
            }
            
        except Exception as e:
            logger.error(f"Error exporting session data: {e}")
            return None