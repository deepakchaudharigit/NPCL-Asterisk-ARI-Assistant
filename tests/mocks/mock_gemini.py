"""
Mock Gemini Live API for testing.
"""

import asyncio
import json
import base64
import uuid
from typing import Dict, Any, List, Callable, Optional
from unittest.mock import Mock, AsyncMock


class MockGeminiLiveAPI:
    """Mock Gemini Live API server for comprehensive testing."""
    
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.responses: Dict[str, Dict[str, Any]] = {}
        self.audio_buffer: List[bytes] = []
        
        self.event_handlers: List[Callable] = []
        self.is_connected = False
        self.connection_delay = 0.1  # Simulate connection delay
        
        # Configuration
        self.model = "gemini-2.0-flash-exp"
        self.voice = "Puck"
        self.simulate_errors = False
        self.response_delay = 0.5  # Simulate processing delay
    
    async def connect(self) -> bool:
        """Simulate connection to Gemini Live API."""
        await asyncio.sleep(self.connection_delay)
        
        if self.simulate_errors:
            return False
        
        self.is_connected = True
        
        # Send session created event
        await self._send_event({
            "type": "session.created",
            "session": {
                "id": str(uuid.uuid4()),
                "model": self.model,
                "created_at": "2024-01-01T12:00:00.000Z"
            }
        })
        
        return True
    
    async def disconnect(self):
        """Simulate disconnection."""
        self.is_connected = False
        self.sessions.clear()
        self.responses.clear()
        self.audio_buffer.clear()
    
    def add_event_handler(self, handler: Callable):
        """Add event handler."""
        self.event_handlers.append(handler)
    
    def remove_event_handler(self, handler: Callable):
        """Remove event handler."""
        if handler in self.event_handlers:
            self.event_handlers.remove(handler)
    
    async def _send_event(self, event: Dict[str, Any]):
        """Send event to all registered handlers."""
        for handler in self.event_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                print(f"Error in Gemini event handler: {e}")
    
    async def send_audio_chunk(self, audio_data: bytes) -> bool:
        """Simulate sending audio chunk."""
        if not self.is_connected:
            return False
        
        if self.simulate_errors:
            await self._send_event({
                "type": "error",
                "error": {
                    "code": "AUDIO_ERROR",
                    "message": "Failed to process audio"
                }
            })
            return False
        
        # Add to buffer
        self.audio_buffer.append(audio_data)
        
        # Simulate speech detection based on audio energy
        energy = self._calculate_audio_energy(audio_data)
        
        if energy > 1000:  # Threshold for speech detection
            await self._send_event({
                "type": "input_audio_buffer.speech_started",
                "audio_start_ms": len(self.audio_buffer) * 20  # Assuming 20ms chunks
            })
        elif energy < 100:  # Threshold for silence
            await self._send_event({
                "type": "input_audio_buffer.speech_stopped",
                "audio_end_ms": len(self.audio_buffer) * 20
            })
        
        return True
    
    async def commit_audio_buffer(self) -> bool:
        """Simulate committing audio buffer."""
        if not self.is_connected:
            return False
        
        await self._send_event({
            "type": "input_audio_buffer.committed"
        })
        
        # Simulate processing delay
        await asyncio.sleep(self.response_delay)
        
        # Generate response
        await self._generate_response()
        
        return True
    
    async def clear_audio_buffer(self) -> bool:
        """Simulate clearing audio buffer."""
        if not self.is_connected:
            return False
        
        self.audio_buffer.clear()
        
        await self._send_event({
            "type": "input_audio_buffer.cleared"
        })
        
        return True
    
    async def create_response(self) -> bool:
        """Simulate creating a response."""
        if not self.is_connected:
            return False
        
        response_id = str(uuid.uuid4())
        
        await self._send_event({
            "type": "response.created",
            "response": {
                "id": response_id
            }
        })
        
        # Generate audio response
        await self._generate_audio_response(response_id)
        
        return True
    
    async def cancel_response(self, response_id: str) -> bool:
        """Simulate cancelling a response."""
        if not self.is_connected:
            return False
        
        if response_id in self.responses:
            del self.responses[response_id]
        
        await self._send_event({
            "type": "response.cancelled",
            "response": {
                "id": response_id
            }
        })
        
        return True
    
    async def _generate_response(self):
        """Generate a mock text response."""
        response_id = str(uuid.uuid4())
        
        # Simulate response creation
        await self._send_event({
            "type": "response.created",
            "response": {
                "id": response_id
            }
        })
        
        # Simulate text response
        mock_text = "Hello! I'm a mock Gemini assistant. How can I help you today?"
        
        # Send text in chunks to simulate streaming
        words = mock_text.split()
        for i, word in enumerate(words):
            await self._send_event({
                "type": "response.text.delta",
                "response": {
                    "id": response_id,
                    "delta": word + " "
                }
            })
            await asyncio.sleep(0.1)  # Simulate streaming delay
        
        # Send completion
        await self._send_event({
            "type": "response.text.done",
            "response": {
                "id": response_id,
                "text": mock_text
            }
        })
    
    async def _generate_audio_response(self, response_id: str):
        """Generate a mock audio response."""
        # Generate mock audio data (sine wave)
        import numpy as np
        
        # Generate 2 seconds of 440Hz tone at 16kHz
        duration = 2.0
        sample_rate = 16000
        frequency = 440
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio_samples = 0.3 * np.sin(2 * np.pi * frequency * t)
        audio_data = (audio_samples * 32767).astype(np.int16).tobytes()
        
        # Send audio in chunks
        chunk_size = 320 * 2  # 20ms chunks in bytes
        
        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i:i + chunk_size]
            audio_base64 = base64.b64encode(chunk).decode('utf-8')
            
            await self._send_event({
                "type": "response.audio.delta",
                "response": {
                    "id": response_id,
                    "output": {
                        "audio": audio_base64
                    }
                }
            })
            
            await asyncio.sleep(0.02)  # 20ms delay between chunks
        
        # Send completion
        await self._send_event({
            "type": "response.audio.done",
            "response": {
                "id": response_id
            }
        })
    
    def _calculate_audio_energy(self, audio_data: bytes) -> float:
        """Calculate audio energy for speech detection simulation."""
        if len(audio_data) == 0:
            return 0.0
        
        # Convert bytes to numpy array
        import numpy as np
        samples = np.frombuffer(audio_data, dtype=np.int16)
        
        # Calculate RMS energy
        energy = np.sqrt(np.mean(samples.astype(np.float32) ** 2))
        return float(energy)
    
    def set_error_simulation(self, enabled: bool):
        """Enable/disable error simulation."""
        self.simulate_errors = enabled
    
    def set_response_delay(self, delay: float):
        """Set response delay for testing."""
        self.response_delay = delay
    
    def get_audio_buffer_size(self) -> int:
        """Get current audio buffer size."""
        return len(self.audio_buffer)
    
    def get_session_count(self) -> int:
        """Get number of active sessions."""
        return len(self.sessions)


class MockGeminiClient:
    """Mock Gemini client for unit testing."""
    
    def __init__(self, api_key: str = "test-key", config: Optional[Dict] = None):
        self.api_key = api_key
        self.config = config or {}
        self.is_connected = False
        self.session = None
        
        # Mock methods
        self.connect = AsyncMock(return_value=True)
        self.disconnect = AsyncMock()
        self.start_conversation = AsyncMock(return_value="test-session-123")
        self.end_conversation = AsyncMock()
        self.send_audio_chunk = AsyncMock(return_value=True)
        self.commit_audio_buffer = AsyncMock(return_value=True)
        self.clear_audio_buffer = AsyncMock(return_value=True)
        self.create_response = AsyncMock(return_value=True)
        self.cancel_response = AsyncMock(return_value=True)
        
        # Mock event handlers
        self.event_handlers = {}
        
        # Setup default behavior
        self._setup_default_behavior()
    
    def _setup_default_behavior(self):
        """Setup default mock behavior."""
        async def mock_connect():
            self.is_connected = True
            return True
        
        async def mock_disconnect():
            self.is_connected = False
        
        self.connect.side_effect = mock_connect
        self.disconnect.side_effect = mock_disconnect
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """Register event handler."""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get mock connection status."""
        return {
            "is_connected": self.is_connected,
            "websocket_state": "OPEN" if self.is_connected else "CLOSED",
            "last_audio_timestamp": 0,
            "is_processing_audio": False,
            "config": self.config
        }
    
    def get_session_info(self) -> Optional[Dict[str, Any]]:
        """Get mock session info."""
        if self.session:
            return {
                "session_id": self.session,
                "is_active": True,
                "created_at": 1704110400.0,  # 2024-01-01 12:00:00
                "conversation_length": 0,
                "is_user_speaking": False,
                "current_response_id": None,
                "audio_buffer_size": 0
            }
        return None