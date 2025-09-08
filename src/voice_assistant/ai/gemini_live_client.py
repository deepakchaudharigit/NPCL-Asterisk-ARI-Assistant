"""
Gemini Live API client for real-time conversational AI.
Handles WebSocket-based communication with Google's Gemini Live API for
real-time speech-to-speech conversation.
"""

import asyncio
import json
import logging
import time
import base64
import uuid
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, asdict
from enum import Enum
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from config.settings import get_settings
from ..audio.realtime_audio_processor import AudioConfig, RealTimeAudioProcessor

logger = logging.getLogger(__name__)


class GeminiLiveEventType(Enum):
    """Gemini Live API event types"""
    # Setup events
    SETUP = "setup"
    SESSION_UPDATE = "session.update"
    
    # Input events
    INPUT_AUDIO_BUFFER_APPEND = "input_audio_buffer.append"
    INPUT_AUDIO_BUFFER_COMMIT = "input_audio_buffer.commit"
    INPUT_AUDIO_BUFFER_CLEAR = "input_audio_buffer.clear"
    
    # Response events
    RESPONSE_CREATE = "response.create"
    RESPONSE_CANCEL = "response.cancel"
    
    # Server events
    ERROR = "error"
    SESSION_CREATED = "session.created"
    SESSION_UPDATED = "session.updated"
    INPUT_AUDIO_BUFFER_COMMITTED = "input_audio_buffer.committed"
    INPUT_AUDIO_BUFFER_CLEARED = "input_audio_buffer.cleared"
    INPUT_AUDIO_BUFFER_SPEECH_STARTED = "input_audio_buffer.speech_started"
    INPUT_AUDIO_BUFFER_SPEECH_STOPPED = "input_audio_buffer.speech_stopped"
    RESPONSE_CREATED = "response.created"
    RESPONSE_DONE = "response.done"
    RESPONSE_OUTPUT_ITEM_ADDED = "response.output_item.added"
    RESPONSE_OUTPUT_ITEM_DONE = "response.output_item.done"
    RESPONSE_CONTENT_PART_ADDED = "response.content_part.added"
    RESPONSE_CONTENT_PART_DONE = "response.content_part.done"
    RESPONSE_AUDIO_TRANSCRIPT_DELTA = "response.audio_transcript.delta"
    RESPONSE_AUDIO_TRANSCRIPT_DONE = "response.audio_transcript.done"
    RESPONSE_AUDIO_DELTA = "response.audio.delta"
    RESPONSE_AUDIO_DONE = "response.audio.done"
    RESPONSE_TEXT_DELTA = "response.text.delta"
    RESPONSE_TEXT_DONE = "response.text.done"


@dataclass
class GeminiLiveConfig:
    """Configuration for Gemini Live API"""
    model: str = "gemini-2.0-flash-exp"
    voice: str = "Puck"  # Available voices: Puck, Charon, Kore, Fenrir
    turn_detection: Dict[str, Any] = None
    input_audio_format: str = "pcm16"  # pcm16 for 16-bit PCM
    output_audio_format: str = "pcm16"
    input_audio_transcription: bool = True
    output_audio_transcription: bool = True
    
    def __post_init__(self):
        if self.turn_detection is None:
            self.turn_detection = {
                "type": "server_vad",
                "threshold": 0.5,
                "prefix_padding_ms": 300,
                "silence_duration_ms": 500
            }


@dataclass
class ConversationItem:
    """Conversation item for Gemini Live"""
    id: str
    type: str  # "message", "function_call", "function_call_output"
    role: str  # "user", "assistant", "system"
    content: List[Dict[str, Any]]
    status: str = "completed"  # "in_progress", "completed", "incomplete"


class GeminiLiveSession:
    """Manages a Gemini Live conversation session"""
    
    def __init__(self, config: GeminiLiveConfig):
        self.config = config
        self.session_id = str(uuid.uuid4())
        self.conversation: List[ConversationItem] = []
        self.is_active = False
        self.created_at = time.time()
        
        # Audio state
        self.input_audio_buffer = bytearray()
        self.is_user_speaking = False
        self.current_response_id = None
        
        logger.info(f"Created Gemini Live session: {self.session_id}")
    
    def add_conversation_item(self, item: ConversationItem):
        """Add item to conversation history"""
        self.conversation.append(item)
        logger.debug(f"Added conversation item: {item.type} from {item.role}")
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get conversation history as list of dictionaries"""
        return [asdict(item) for item in self.conversation]
    
    def clear_conversation(self):
        """Clear conversation history"""
        self.conversation.clear()
        logger.info("Conversation history cleared")


class GeminiLiveClient:
    """Client for Google Gemini Live API real-time communication"""
    
    def __init__(self, api_key: str = None, config: GeminiLiveConfig = None):
        self.settings = get_settings()
        self.api_key = api_key or self.settings.google_api_key
        self.config = config or GeminiLiveConfig()
        
        # WebSocket connection
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.is_connected = False
        self.connection_task: Optional[asyncio.Task] = None
        
        # Session management
        self.session: Optional[GeminiLiveSession] = None
        
        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = {}
        
        # Audio processing
        self.audio_processor = RealTimeAudioProcessor()
        
        # State tracking
        self.is_processing_audio = False
        self.last_audio_timestamp = 0
        
        # API endpoint
        self.api_url = f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent?key={self.api_key}"
        
        logger.info("Gemini Live client initialized")
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """Register event handler for specific event type"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
        logger.debug(f"Registered handler for event: {event_type}")
    
    async def connect(self) -> bool:
        """Connect to Gemini Live API"""
        try:
            logger.info("Connecting to Gemini Live API...")
            
            # Create WebSocket connection
            self.websocket = await websockets.connect(
                self.api_url,
                extra_headers={
                    "User-Agent": "VoiceAssistant/1.0"
                },
                ping_interval=30,
                ping_timeout=10
            )
            
            self.is_connected = True
            
            # Start connection handler
            self.connection_task = asyncio.create_task(self._connection_handler())
            
            # Setup session
            await self._setup_session()
            
            logger.info("Connected to Gemini Live API")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Gemini Live API: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from Gemini Live API"""
        try:
            self.is_connected = False
            
            if self.connection_task:
                self.connection_task.cancel()
                try:
                    await self.connection_task
                except asyncio.CancelledError:
                    pass
            
            if self.websocket:
                await self.websocket.close()
                self.websocket = None
            
            if self.session:
                self.session.is_active = False
            
            logger.info("Disconnected from Gemini Live API")
            
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
    
    async def start_conversation(self) -> str:
        """Start a new conversation session"""
        if not self.is_connected:
            raise RuntimeError("Not connected to Gemini Live API")
        
        self.session = GeminiLiveSession(self.config)
        self.session.is_active = True
        
        logger.info(f"Started conversation session: {self.session.session_id}")
        return self.session.session_id
    
    async def end_conversation(self):
        """End current conversation session"""
        if self.session:
            self.session.is_active = False
            logger.info(f"Ended conversation session: {self.session.session_id}")
    
    async def send_audio_chunk(self, audio_data: bytes) -> bool:
        """
        Send audio chunk to Gemini Live API
        
        Args:
            audio_data: Raw audio data in PCM16 format
            
        Returns:
            Success status
        """
        if not self.is_connected or not self.websocket:
            logger.warning("Cannot send audio: not connected")
            return False
        
        try:
            # Encode audio data as base64
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # Create input audio buffer append event
            event = {
                "type": GeminiLiveEventType.INPUT_AUDIO_BUFFER_APPEND.value,
                "input_audio_buffer": {
                    "audio": audio_base64
                }
            }
            
            await self._send_event(event)
            
            # Update session state
            if self.session:
                self.session.input_audio_buffer.extend(audio_data)
            
            self.last_audio_timestamp = time.time()
            return True
            
        except Exception as e:
            logger.error(f"Error sending audio chunk: {e}")
            return False
    
    async def commit_audio_buffer(self) -> bool:
        """Commit the current audio buffer for processing"""
        if not self.is_connected or not self.websocket:
            return False
        
        try:
            event = {
                "type": GeminiLiveEventType.INPUT_AUDIO_BUFFER_COMMIT.value
            }
            
            await self._send_event(event)
            logger.debug("Audio buffer committed")
            return True
            
        except Exception as e:
            logger.error(f"Error committing audio buffer: {e}")
            return False
    
    async def clear_audio_buffer(self) -> bool:
        """Clear the current audio buffer"""
        if not self.is_connected or not self.websocket:
            return False
        
        try:
            event = {
                "type": GeminiLiveEventType.INPUT_AUDIO_BUFFER_CLEAR.value
            }
            
            await self._send_event(event)
            
            if self.session:
                self.session.input_audio_buffer.clear()
            
            logger.debug("Audio buffer cleared")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing audio buffer: {e}")
            return False
    
    async def create_response(self) -> bool:
        """Request Gemini to create a response"""
        if not self.is_connected or not self.websocket:
            return False
        
        try:
            response_id = str(uuid.uuid4())
            
            event = {
                "type": GeminiLiveEventType.RESPONSE_CREATE.value,
                "response": {
                    "id": response_id
                }
            }
            
            await self._send_event(event)
            
            if self.session:
                self.session.current_response_id = response_id
            
            logger.debug(f"Response creation requested: {response_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating response: {e}")
            return False
    
    async def cancel_response(self) -> bool:
        """Cancel current response generation"""
        if not self.is_connected or not self.websocket:
            return False
        
        if not self.session or not self.session.current_response_id:
            return False
        
        try:
            event = {
                "type": GeminiLiveEventType.RESPONSE_CANCEL.value,
                "response": {
                    "id": self.session.current_response_id
                }
            }
            
            await self._send_event(event)
            
            self.session.current_response_id = None
            logger.debug("Response cancelled")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling response: {e}")
            return False
    
    async def _setup_session(self):
        """Setup initial session with Gemini Live API"""
        try:
            setup_event = {
                "type": GeminiLiveEventType.SETUP.value,
                "setup": {
                    "model": self.config.model,
                    "generation_config": {
                        "response_modalities": ["AUDIO"],
                        "speech_config": {
                            "voice_config": {
                                "prebuilt_voice_config": {
                                    "voice_name": self.config.voice
                                }
                            }
                        }
                    },
                    "system_instruction": {
                        "parts": [{
                            "text": f"You are {self.settings.assistant_name}, a helpful voice assistant. "
                                   f"Respond naturally and conversationally. Keep responses concise but helpful."
                        }]
                    },
                    "tools": [],  # Add tools if needed
                    "tool_config": {
                        "function_calling_config": {
                            "mode": "AUTO"
                        }
                    },
                    "turn_detection": self.config.turn_detection,
                    "input_audio_config": {
                        "encoding": self.config.input_audio_format,
                        "sample_rate_hertz": 16000
                    },
                    "output_audio_config": {
                        "encoding": self.config.output_audio_format,
                        "sample_rate_hertz": 16000
                    }
                }
            }
            
            await self._send_event(setup_event)
            logger.info("Session setup sent")
            
        except Exception as e:
            logger.error(f"Error setting up session: {e}")
            raise
    
    async def _send_event(self, event: Dict[str, Any]):
        """Send event to Gemini Live API"""
        if not self.websocket:
            raise RuntimeError("WebSocket not connected")
        
        try:
            message = json.dumps(event)
            await self.websocket.send(message)
            logger.debug(f"Sent event: {event.get('type', 'unknown')}")
            
        except Exception as e:
            logger.error(f"Error sending event: {e}")
            raise
    
    async def _connection_handler(self):
        """Handle WebSocket connection and incoming messages"""
        try:
            while self.is_connected and self.websocket:
                try:
                    message = await self.websocket.recv()
                    await self._handle_message(message)
                    
                except ConnectionClosed:
                    logger.warning("WebSocket connection closed")
                    break
                except WebSocketException as e:
                    logger.error(f"WebSocket error: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Connection handler error: {e}")
        finally:
            self.is_connected = False
    
    async def _handle_message(self, message: str):
        """Handle incoming message from Gemini Live API"""
        try:
            event = json.loads(message)
            event_type = event.get("type")
            
            logger.debug(f"Received event: {event_type}")
            
            # Handle specific events
            if event_type == GeminiLiveEventType.SESSION_CREATED.value:
                await self._handle_session_created(event)
            elif event_type == GeminiLiveEventType.RESPONSE_AUDIO_DELTA.value:
                await self._handle_audio_delta(event)
            elif event_type == GeminiLiveEventType.RESPONSE_AUDIO_DONE.value:
                await self._handle_audio_done(event)
            elif event_type == GeminiLiveEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED.value:
                await self._handle_speech_started(event)
            elif event_type == GeminiLiveEventType.INPUT_AUDIO_BUFFER_SPEECH_STOPPED.value:
                await self._handle_speech_stopped(event)
            elif event_type == GeminiLiveEventType.ERROR.value:
                await self._handle_error(event)
            
            # Trigger registered event handlers
            await self._trigger_event_handlers(event_type, event)
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    async def _handle_session_created(self, event: Dict[str, Any]):
        """Handle session created event"""
        session_info = event.get("session", {})
        logger.info(f"Gemini Live session created: {session_info.get('id', 'unknown')}")
    
    async def _handle_audio_delta(self, event: Dict[str, Any]):
        """Handle audio delta (streaming audio response)"""
        try:
            audio_data = event.get("response", {}).get("output", {}).get("audio", "")
            if audio_data:
                # Decode base64 audio data
                audio_bytes = base64.b64decode(audio_data)
                
                # Trigger audio response handler
                await self._trigger_event_handlers("audio_response", {
                    "audio_data": audio_bytes,
                    "is_delta": True
                })
                
        except Exception as e:
            logger.error(f"Error handling audio delta: {e}")
    
    async def _handle_audio_done(self, event: Dict[str, Any]):
        """Handle audio done event"""
        logger.debug("Audio response completed")
        await self._trigger_event_handlers("audio_response_done", event)
    
    async def _handle_speech_started(self, event: Dict[str, Any]):
        """Handle speech started event"""
        if self.session:
            self.session.is_user_speaking = True
        
        logger.debug("User speech started")
        await self._trigger_event_handlers("speech_started", event)
    
    async def _handle_speech_stopped(self, event: Dict[str, Any]):
        """Handle speech stopped event"""
        if self.session:
            self.session.is_user_speaking = False
        
        logger.debug("User speech stopped")
        await self._trigger_event_handlers("speech_stopped", event)
    
    async def _handle_error(self, event: Dict[str, Any]):
        """Handle error event"""
        error_info = event.get("error", {})
        error_message = error_info.get("message", "Unknown error")
        error_code = error_info.get("code", "unknown")
        
        logger.error(f"Gemini Live API error [{error_code}]: {error_message}")
        await self._trigger_event_handlers("error", event)
    
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
    
    def get_session_info(self) -> Optional[Dict[str, Any]]:
        """Get current session information"""
        if not self.session:
            return None
        
        return {
            "session_id": self.session.session_id,
            "is_active": self.session.is_active,
            "created_at": self.session.created_at,
            "conversation_length": len(self.session.conversation),
            "is_user_speaking": self.session.is_user_speaking,
            "current_response_id": self.session.current_response_id,
            "audio_buffer_size": len(self.session.input_audio_buffer)
        }
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get connection status information"""
        return {
            "is_connected": self.is_connected,
            "websocket_state": str(self.websocket.state) if self.websocket else "None",
            "last_audio_timestamp": self.last_audio_timestamp,
            "is_processing_audio": self.is_processing_audio,
            "config": {
                "model": self.config.model,
                "voice": self.config.voice,
                "input_format": self.config.input_audio_format,
                "output_format": self.config.output_audio_format
            }
        }