"""
Session and conversation fixtures for testing session management and conversation flows.
"""

import pytest
import time
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from src.voice_assistant.core.session_manager import SessionState, CallDirection


class ConversationRole(Enum):
    """Conversation participant roles."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class ConversationTurn:
    """A single turn in a conversation."""
    role: ConversationRole
    content: str
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    audio_data: Optional[bytes] = None
    duration_ms: Optional[int] = None
    confidence: Optional[float] = None


@dataclass
class ConversationScenario:
    """A complete conversation scenario for testing."""
    name: str
    description: str
    turns: List[ConversationTurn]
    expected_outcomes: Dict[str, Any] = field(default_factory=dict)
    test_parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionTestData:
    """Test data for session management testing."""
    session_id: str
    channel_id: str
    caller_number: str
    called_number: str
    start_time: float
    state: SessionState
    direction: CallDirection
    conversation: List[ConversationTurn] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SessionFixtures:
    """Factory for creating session test data."""
    
    @staticmethod
    def create_basic_session(
        session_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        caller_number: str = "1234567890",
        called_number: str = "1000"
    ) -> SessionTestData:
        """Create a basic session for testing."""
        return SessionTestData(
            session_id=session_id or f"session-{uuid.uuid4()}",
            channel_id=channel_id or f"channel-{uuid.uuid4()}",
            caller_number=caller_number,
            called_number=called_number,
            start_time=time.time(),
            state=SessionState.ACTIVE,
            direction=CallDirection.INBOUND,
            metadata={
                "user_agent": "Test Client",
                "call_quality": "good",
                "audio_codec": "slin16",
                "sample_rate": 16000
            }
        )
    
    @staticmethod
    def create_session_with_conversation(
        conversation_turns: List[ConversationTurn],
        session_id: Optional[str] = None
    ) -> SessionTestData:
        """Create a session with predefined conversation."""
        session = SessionFixtures.create_basic_session(session_id=session_id)
        session.conversation = conversation_turns
        return session
    
    @staticmethod
    def create_long_running_session(
        duration_minutes: int = 30,
        turns_per_minute: int = 2
    ) -> SessionTestData:
        """Create a long-running session for performance testing."""
        session = SessionFixtures.create_basic_session()
        session.start_time = time.time() - (duration_minutes * 60)
        
        # Generate conversation turns
        total_turns = duration_minutes * turns_per_minute
        for i in range(total_turns):
            turn_time = session.start_time + (i * 30)  # Every 30 seconds
            role = ConversationRole.USER if i % 2 == 0 else ConversationRole.ASSISTANT
            
            session.conversation.append(ConversationTurn(
                role=role,
                content=f"Turn {i + 1} content",
                timestamp=turn_time,
                metadata={"turn_number": i + 1}
            ))
        
        return session
    
    @staticmethod
    def create_error_session() -> SessionTestData:
        """Create a session that encountered errors."""
        session = SessionFixtures.create_basic_session()
        session.state = SessionState.ERROR
        session.metadata.update({
            "error_type": "connection_lost",
            "error_message": "WebSocket connection lost",
            "error_timestamp": time.time(),
            "recovery_attempts": 3
        })
        return session


class ConversationFixtures:
    """Factory for creating conversation scenarios."""
    
    @staticmethod
    def create_simple_greeting() -> ConversationScenario:
        """Simple greeting conversation."""
        return ConversationScenario(
            name="simple_greeting",
            description="Basic greeting exchange",
            turns=[
                ConversationTurn(
                    role=ConversationRole.USER,
                    content="Hello",
                    timestamp=time.time(),
                    metadata={"intent": "greeting"}
                ),
                ConversationTurn(
                    role=ConversationRole.ASSISTANT,
                    content="Hi! How can I help you today?",
                    timestamp=time.time() + 1,
                    metadata={"intent": "greeting_response"}
                )
            ],
            expected_outcomes={
                "successful_greeting": True,
                "response_time_ms": 1000,
                "sentiment": "positive"
            }
        )
    
    @staticmethod
    def create_multi_turn_conversation() -> ConversationScenario:
        """Multi-turn conversation scenario."""
        base_time = time.time()
        
        return ConversationScenario(
            name="multi_turn_conversation",
            description="Extended conversation with multiple exchanges",
            turns=[
                ConversationTurn(
                    role=ConversationRole.USER,
                    content="What's the weather like?",
                    timestamp=base_time,
                    metadata={"intent": "weather_query"}
                ),
                ConversationTurn(
                    role=ConversationRole.ASSISTANT,
                    content="I'd be happy to help with weather information. Could you tell me your location?",
                    timestamp=base_time + 2,
                    metadata={"intent": "location_request"}
                ),
                ConversationTurn(
                    role=ConversationRole.USER,
                    content="I'm in New York",
                    timestamp=base_time + 5,
                    metadata={"intent": "location_provided", "location": "New York"}
                ),
                ConversationTurn(
                    role=ConversationRole.ASSISTANT,
                    content="I don't have access to real-time weather data, but I can help you find weather information for New York.",
                    timestamp=base_time + 7,
                    metadata={"intent": "weather_response", "limitation": "no_real_time_data"}
                )
            ],
            expected_outcomes={
                "conversation_length": 4,
                "location_extracted": "New York",
                "intent_recognition": True,
                "context_maintained": True
            }
        )
    
    @staticmethod
    def create_interruption_scenario() -> ConversationScenario:
        """Conversation with user interruptions."""
        base_time = time.time()
        
        return ConversationScenario(
            name="interruption_scenario",
            description="Conversation with user interrupting assistant",
            turns=[
                ConversationTurn(
                    role=ConversationRole.USER,
                    content="Can you tell me about",
                    timestamp=base_time,
                    metadata={"intent": "incomplete_query", "interrupted": True}
                ),
                ConversationTurn(
                    role=ConversationRole.USER,
                    content="Actually, never mind",
                    timestamp=base_time + 1,
                    metadata={"intent": "cancellation", "interruption": True}
                ),
                ConversationTurn(
                    role=ConversationRole.ASSISTANT,
                    content="No problem! Is there something else I can help you with?",
                    timestamp=base_time + 3,
                    metadata={"intent": "graceful_recovery"}
                )
            ],
            expected_outcomes={
                "interruption_handled": True,
                "graceful_recovery": True,
                "context_reset": True
            },
            test_parameters={
                "interruption_detection": True,
                "response_adaptation": True
            }
        )
    
    @staticmethod
    def create_error_recovery_scenario() -> ConversationScenario:
        """Conversation with error and recovery."""
        base_time = time.time()
        
        return ConversationScenario(
            name="error_recovery",
            description="Conversation with error and recovery",
            turns=[
                ConversationTurn(
                    role=ConversationRole.USER,
                    content="What's 2+2?",
                    timestamp=base_time,
                    metadata={"intent": "math_query"}
                ),
                ConversationTurn(
                    role=ConversationRole.ASSISTANT,
                    content="I'm sorry, I didn't understand that clearly. Could you repeat your question?",
                    timestamp=base_time + 2,
                    metadata={"intent": "clarification_request", "error": "audio_unclear"}
                ),
                ConversationTurn(
                    role=ConversationRole.USER,
                    content="What is two plus two?",
                    timestamp=base_time + 5,
                    metadata={"intent": "math_query_clarified"}
                ),
                ConversationTurn(
                    role=ConversationRole.ASSISTANT,
                    content="Two plus two equals four.",
                    timestamp=base_time + 7,
                    metadata={"intent": "math_response", "answer": "4"}
                )
            ],
            expected_outcomes={
                "error_recovery": True,
                "clarification_successful": True,
                "correct_answer": "4"
            },
            test_parameters={
                "error_simulation": True,
                "recovery_strategy": "clarification"
            }
        )
    
    @staticmethod
    def create_context_switching_scenario() -> ConversationScenario:
        """Conversation with topic changes."""
        base_time = time.time()
        
        return ConversationScenario(
            name="context_switching",
            description="Conversation with multiple topic changes",
            turns=[
                ConversationTurn(
                    role=ConversationRole.USER,
                    content="Tell me about the weather",
                    timestamp=base_time,
                    metadata={"intent": "weather_query", "topic": "weather"}
                ),
                ConversationTurn(
                    role=ConversationRole.ASSISTANT,
                    content="I'd be happy to help with weather information. What location are you interested in?",
                    timestamp=base_time + 2,
                    metadata={"intent": "location_request", "topic": "weather"}
                ),
                ConversationTurn(
                    role=ConversationRole.USER,
                    content="Actually, what time is it?",
                    timestamp=base_time + 5,
                    metadata={"intent": "time_query", "topic": "time", "context_switch": True}
                ),
                ConversationTurn(
                    role=ConversationRole.ASSISTANT,
                    content="I don't have access to real-time information, but you can check the time on your device.",
                    timestamp=base_time + 7,
                    metadata={"intent": "time_response", "topic": "time", "limitation": "no_real_time_data"}
                )
            ],
            expected_outcomes={
                "context_switch_detected": True,
                "topic_transition": "weather -> time",
                "context_maintained": False
            },
            test_parameters={
                "context_tracking": True,
                "topic_detection": True
            }
        )
    
    @staticmethod
    def create_long_conversation(turns: int = 20) -> ConversationScenario:
        """Create a long conversation for performance testing."""
        conversation_turns = []
        base_time = time.time()
        
        for i in range(turns):
            role = ConversationRole.USER if i % 2 == 0 else ConversationRole.ASSISTANT
            
            if role == ConversationRole.USER:
                content = f"User question {i // 2 + 1}"
                intent = "user_query"
            else:
                content = f"Assistant response {i // 2 + 1}"
                intent = "assistant_response"
            
            conversation_turns.append(ConversationTurn(
                role=role,
                content=content,
                timestamp=base_time + (i * 3),  # 3 seconds between turns
                metadata={
                    "intent": intent,
                    "turn_number": i + 1,
                    "conversation_position": "middle" if 2 < i < turns - 2 else "edge"
                }
            ))
        
        return ConversationScenario(
            name="long_conversation",
            description=f"Long conversation with {turns} turns",
            turns=conversation_turns,
            expected_outcomes={
                "total_turns": turns,
                "conversation_duration": turns * 3,
                "memory_usage_stable": True
            },
            test_parameters={
                "performance_test": True,
                "memory_monitoring": True
            }
        )


@pytest.fixture
def basic_session():
    """Basic session for testing."""
    return SessionFixtures.create_basic_session()


@pytest.fixture
def session_with_conversation():
    """Session with a simple conversation."""
    conversation = ConversationFixtures.create_simple_greeting()
    return SessionFixtures.create_session_with_conversation(conversation.turns)


@pytest.fixture
def long_running_session():
    """Long-running session for performance testing."""
    return SessionFixtures.create_long_running_session(duration_minutes=30)


@pytest.fixture
def error_session():
    """Session that encountered errors."""
    return SessionFixtures.create_error_session()


@pytest.fixture
def conversation_scenarios():
    """Collection of conversation scenarios."""
    return {
        "simple_greeting": ConversationFixtures.create_simple_greeting(),
        "multi_turn": ConversationFixtures.create_multi_turn_conversation(),
        "interruption": ConversationFixtures.create_interruption_scenario(),
        "error_recovery": ConversationFixtures.create_error_recovery_scenario(),
        "context_switching": ConversationFixtures.create_context_switching_scenario(),
        "long_conversation": ConversationFixtures.create_long_conversation(20)
    }


@pytest.fixture
def session_test_data():
    """Collection of session test data."""
    return {
        "basic": SessionFixtures.create_basic_session(),
        "with_conversation": SessionFixtures.create_session_with_conversation(
            ConversationFixtures.create_simple_greeting().turns
        ),
        "long_running": SessionFixtures.create_long_running_session(),
        "error": SessionFixtures.create_error_session()
    }


@pytest.fixture
def conversation_factory():
    """Factory for creating custom conversations."""
    def _create_conversation(
        name: str,
        turns: List[Dict[str, Any]],
        expected_outcomes: Optional[Dict[str, Any]] = None
    ) -> ConversationScenario:
        """Create a custom conversation scenario."""
        conversation_turns = []
        base_time = time.time()
        
        for i, turn_data in enumerate(turns):
            conversation_turns.append(ConversationTurn(
                role=ConversationRole(turn_data["role"]),
                content=turn_data["content"],
                timestamp=base_time + (i * 2),
                metadata=turn_data.get("metadata", {})
            ))
        
        return ConversationScenario(
            name=name,
            description=f"Custom conversation: {name}",
            turns=conversation_turns,
            expected_outcomes=expected_outcomes or {}
        )
    
    return _create_conversation


@pytest.fixture
def session_factory():
    """Factory for creating custom sessions."""
    def _create_session(
        session_id: Optional[str] = None,
        state: SessionState = SessionState.ACTIVE,
        direction: CallDirection = CallDirection.INBOUND,
        **kwargs
    ) -> SessionTestData:
        """Create a custom session."""
        session = SessionFixtures.create_basic_session(session_id=session_id)
        session.state = state
        session.direction = direction
        
        # Apply any additional parameters
        for key, value in kwargs.items():
            if hasattr(session, key):
                setattr(session, key, value)
            else:
                session.metadata[key] = value
        
        return session
    
    return _create_session


@pytest.fixture
def multi_session_scenario():
    """Multiple concurrent sessions for testing."""
    sessions = []
    
    # Create 5 concurrent sessions
    for i in range(5):
        session = SessionFixtures.create_basic_session(
            session_id=f"session-{i}",
            channel_id=f"channel-{i}",
            caller_number=f"123456789{i}",
            called_number="1000"
        )
        
        # Add some conversation to each session
        if i % 2 == 0:
            session.conversation = ConversationFixtures.create_simple_greeting().turns
        else:
            session.conversation = ConversationFixtures.create_multi_turn_conversation().turns
        
        sessions.append(session)
    
    return sessions


@pytest.fixture
def session_lifecycle_data():
    """Data for testing complete session lifecycle."""
    return {
        "initialization": {
            "session_id": "lifecycle-session",
            "channel_id": "lifecycle-channel",
            "caller_number": "9876543210",
            "called_number": "1000",
            "expected_state": SessionState.INITIALIZING
        },
        "activation": {
            "expected_state": SessionState.ACTIVE,
            "activation_time": 2.0,
            "initial_greeting": "Hello! How can I help you today?"
        },
        "conversation": {
            "turns": [
                {"role": "user", "content": "I need help with something"},
                {"role": "assistant", "content": "I'd be happy to help! What do you need assistance with?"},
                {"role": "user", "content": "Thank you, that's all for now"},
                {"role": "assistant", "content": "You're welcome! Have a great day!"}
            ]
        },
        "termination": {
            "expected_state": SessionState.TERMINATED,
            "cleanup_timeout": 5.0,
            "final_message": "Session ended. Thank you for calling!"
        }
    }