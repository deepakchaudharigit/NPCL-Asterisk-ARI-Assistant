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
    model: str = "gemini-1.5-flash"  # Updated to use 1.5 Flash
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
        
        # API endpoint from settings
        self.api_url = f"{self.settings.gemini_live_api_endpoint}?key={self.api_key}"
        
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
            logger.info(f"Connecting to Gemini Live API...")
            logger.info(f"Model: {self.config.model}")
            logger.info(f"Voice: {self.config.voice}")
            logger.debug(f"URL: {self.api_url[:100]}...")
            
            # Create WebSocket connection with timeout
            # Use simple connection without extra_headers for compatibility
            self.websocket = await asyncio.wait_for(
                websockets.connect(
                    self.api_url,
                    ping_interval=30,
                    ping_timeout=10
                ),
                timeout=15.0  # 15 second connection timeout
            )
            
            logger.info("WebSocket connection established")
            self.is_connected = True
            
            # Start connection handler
            self.connection_task = asyncio.create_task(self._connection_handler())
            
            # Setup session with timeout
            await asyncio.wait_for(self._setup_session(), timeout=10.0)
            
            logger.info("Connected to Gemini Live API successfully")
            return True
            
        except asyncio.TimeoutError:
            logger.error("Connection timeout - Live API may not be available")
            self.is_connected = False
            return False
        except websockets.exceptions.InvalidStatusCode as e:
            logger.error(f"Invalid status code: {e.status_code} - Check API key and permissions")
            self.is_connected = False
            return False
        except websockets.exceptions.WebSocketException as e:
            logger.error(f"WebSocket error: {e}")
            self.is_connected = False
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Gemini Live API: {e}")
            logger.debug(f"Full error details:", exc_info=True)
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
            
            # Create realtime input event
            event = {
                "realtimeInput": {
                    "audio": {
                        "data": audio_base64,
                        "mimeType": "audio/pcm;rate=16000"
                    }
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
        """Commit the current audio buffer for processing (automatic in new API)"""
        # In the new Live API, audio is processed automatically
        # This method is kept for compatibility but does nothing
        logger.debug("Audio buffer commit (automatic in Live API)")
        return True
    
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
        """Request Gemini to create a response (automatic in new API)"""
        # In the new Live API, responses are generated automatically
        # This method is kept for compatibility but does nothing
        logger.debug("Response creation (automatic in Live API)")
        return True
    
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
                "setup": {
                    "model": f"models/{self.config.model}",
                    "generationConfig": {
                        "responseModalities": ["AUDIO"],
                        "speechConfig": {
                            "voiceConfig": {
                                "prebuiltVoiceConfig": {
                                    "voiceName": self.config.voice
                                }
                            }
                        }
                    },
                    "systemInstruction": {
                        "parts": [{
                            "text": f"You are {self.settings.assistant_name}, a helpful voice assistant. "
                                   f"Respond naturally and conversationally. Keep responses concise but helpful."
                        }]
                    },
                    "tools": [],  # Add tools if needed
                    "realtimeInputConfig": {
                        "automaticActivityDetection": {
                            "disabled": False,
                            "startOfSpeechSensitivity": "START_SENSITIVITY_HIGH",
                            "endOfSpeechSensitivity": "END_SENSITIVITY_HIGH",
                            "prefixPaddingMs": 300,
                            "silenceDurationMs": 500
                        },
                        "activityHandling": "START_OF_ACTIVITY_INTERRUPTS"
                    }
                }
            }
            
            logger.debug(f"Sending setup event: {json.dumps(setup_event, indent=2)}")
            await self._send_event(setup_event)
            logger.info("Session setup sent, waiting for confirmation...")
            
            # Wait for setup complete (handled by event handlers)
            # The connection will be considered ready when setup_complete event is received
            
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
            
            logger.debug(f"Received event type: {event_type}")
            logger.debug(f"Full event: {json.dumps(event, indent=2)[:500]}...")
            
            # Handle specific events
            if "setupComplete" in event:
                await self._handle_setup_complete(event)
            elif "serverContent" in event:
                await self._handle_server_content(event)
            elif "toolCall" in event:
                await self._handle_tool_call(event)
            elif "error" in event:
                await self._handle_error(event)
            else:
                logger.debug(f"Unhandled event type: {event_type}")
            
            # Trigger registered event handlers
            await self._trigger_event_handlers(event_type or "unknown", event)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON message: {e}")
            logger.debug(f"Raw message: {message[:200]}...")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            logger.debug(f"Message: {message[:200]}...", exc_info=True)
    
    async def _handle_setup_complete(self, event: Dict[str, Any]):
        """Handle setup complete event"""
        logger.info("Gemini Live session setup completed")
        await self._trigger_event_handlers("setup_complete", event)
    
    async def _handle_server_content(self, event: Dict[str, Any]):
        """Handle server content event"""
        try:
            server_content = event.get("serverContent", {})
            
            # Handle audio data
            if "modelTurn" in server_content:
                model_turn = server_content["modelTurn"]
                if "parts" in model_turn:
                    for part in model_turn["parts"]:
                        if "inlineData" in part:
                            inline_data = part["inlineData"]
                            if inline_data.get("mimeType", "").startswith("audio/"):
                                audio_data = inline_data.get("data", "")
                                if audio_data:
                                    # Decode base64 audio data
                                    audio_bytes = base64.b64decode(audio_data)
                                    
                                    # Trigger audio response handler
                                    await self._trigger_event_handlers("audio_response", {
                                        "audio_data": audio_bytes,
                                        "is_delta": True
                                    })
            
            # Handle turn completion
            if server_content.get("turnComplete"):
                await self._trigger_event_handlers("audio_response_done", event)
            
            # Handle interruption
            if server_content.get("interrupted"):
                await self._trigger_event_handlers("interrupted", event)
                
        except Exception as e:
            logger.error(f"Error handling server content: {e}")
    
    async def _handle_tool_call(self, event: Dict[str, Any]):
        """Handle tool call event"""
        logger.debug("Tool call received")
        await self._trigger_event_handlers("tool_call", event)
    
    async def _handle_speech_activity(self, event: Dict[str, Any]):
        """Handle speech activity events"""
        # Speech activity is now handled automatically by the Live API
        # We'll detect it from the server content events
        pass
    
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