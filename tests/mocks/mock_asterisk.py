"""
Mock Asterisk ARI server for testing.
"""

import asyncio
import json
from typing import Dict, Any, List, Callable, Optional
from unittest.mock import Mock, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient


class MockAsteriskARIServer:
    """Mock Asterisk ARI server for comprehensive testing."""
    
    def __init__(self):
        self.channels: Dict[str, Dict[str, Any]] = {}
        self.bridges: Dict[str, Dict[str, Any]] = {}
        self.recordings: Dict[str, Dict[str, Any]] = {}
        self.playbacks: Dict[str, Dict[str, Any]] = {}
        
        self.event_handlers: List[Callable] = []
        self.is_running = False
        
        # Create FastAPI app for HTTP endpoints
        self.app = FastAPI()
        self._setup_routes()
        
        # Test client for making requests
        self.client = TestClient(self.app)
    
    def _setup_routes(self):
        """Setup ARI HTTP endpoints."""
        
        @self.app.get("/ari/asterisk/info")
        async def get_asterisk_info():
            return {
                "build": {"date": "2024-01-01", "kernel": "test", "machine": "test"},
                "system": {"entity_id": "test-asterisk", "name": "Test Asterisk"},
                "config": {"max_channels": 1000, "max_open_files": 8192}
            }
        
        @self.app.post("/ari/channels/{channel_id}/answer")
        async def answer_channel(channel_id: str):
            if channel_id in self.channels:
                self.channels[channel_id]["state"] = "Up"
                await self._send_event({
                    "type": "ChannelStateChange",
                    "channel": self.channels[channel_id]
                })
            return {"status": "success"}
        
        @self.app.delete("/ari/channels/{channel_id}")
        async def hangup_channel(channel_id: str):
            if channel_id in self.channels:
                self.channels[channel_id]["state"] = "Down"
                await self._send_event({
                    "type": "StasisEnd",
                    "channel": self.channels[channel_id]
                })
                del self.channels[channel_id]
            return {"status": "success"}
        
        @self.app.post("/ari/channels/{channel_id}/externalMedia")
        async def start_external_media(channel_id: str, request_data: dict):
            if channel_id in self.channels:
                # Simulate external media start
                return {"status": "external_media_started"}
            return {"error": "Channel not found"}, 404
        
        @self.app.post("/ari/channels/{channel_id}/play")
        async def play_media(channel_id: str, request_data: dict):
            if channel_id in self.channels:
                playback_id = f"playback-{len(self.playbacks)}"
                self.playbacks[playback_id] = {
                    "id": playback_id,
                    "media_uri": request_data.get("media", ""),
                    "state": "playing",
                    "channel_id": channel_id
                }
                
                await self._send_event({
                    "type": "PlaybackStarted",
                    "playback": self.playbacks[playback_id]
                })
                
                return self.playbacks[playback_id]
            return {"error": "Channel not found"}, 404
        
        @self.app.delete("/ari/playbacks/{playback_id}")
        async def stop_playback(playback_id: str):
            if playback_id in self.playbacks:
                self.playbacks[playback_id]["state"] = "done"
                await self._send_event({
                    "type": "PlaybackFinished",
                    "playback": self.playbacks[playback_id]
                })
                del self.playbacks[playback_id]
            return {"status": "success"}
        
        @self.app.post("/ari/channels/{channel_id}/record")
        async def start_recording(channel_id: str, request_data: dict):
            if channel_id in self.channels:
                recording_name = request_data.get("name", f"recording-{len(self.recordings)}")
                self.recordings[recording_name] = {
                    "name": recording_name,
                    "format": request_data.get("format", "wav"),
                    "state": "recording",
                    "channel_id": channel_id
                }
                
                await self._send_event({
                    "type": "RecordingStarted",
                    "recording": self.recordings[recording_name]
                })
                
                return self.recordings[recording_name]
            return {"error": "Channel not found"}, 404
        
        @self.app.delete("/ari/recordings/live/{recording_name}")
        async def stop_recording(recording_name: str):
            if recording_name in self.recordings:
                self.recordings[recording_name]["state"] = "done"
                await self._send_event({
                    "type": "RecordingFinished",
                    "recording": self.recordings[recording_name]
                })
                del self.recordings[recording_name]
            return {"status": "success"}
    
    async def _send_event(self, event: Dict[str, Any]):
        """Send event to all registered handlers."""
        for handler in self.event_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                print(f"Error in event handler: {e}")
    
    def add_event_handler(self, handler: Callable):
        """Add event handler."""
        self.event_handlers.append(handler)
    
    def remove_event_handler(self, handler: Callable):
        """Remove event handler."""
        if handler in self.event_handlers:
            self.event_handlers.remove(handler)
    
    async def create_channel(
        self,
        channel_id: str,
        caller_number: str = "1234567890",
        called_number: str = "1000",
        state: str = "Ring"
    ) -> Dict[str, Any]:
        """Create a mock channel."""
        channel = {
            "id": channel_id,
            "name": f"SIP/test-{channel_id}",
            "state": state,
            "caller": {
                "number": caller_number,
                "name": "Test Caller"
            },
            "connected": {
                "number": called_number,
                "name": "Voice Assistant"
            },
            "dialplan": {
                "context": "gemini-voice-assistant",
                "exten": called_number,
                "priority": 1
            },
            "creationtime": "2024-01-01T12:00:00.000Z"
        }
        
        self.channels[channel_id] = channel
        return channel
    
    async def simulate_incoming_call(
        self,
        channel_id: str,
        caller_number: str = "1234567890",
        called_number: str = "1000"
    ):
        """Simulate an incoming call flow."""
        # Create channel
        channel = await self.create_channel(channel_id, caller_number, called_number)
        
        # Send StasisStart event
        await self._send_event({
            "type": "StasisStart",
            "application": "gemini-voice-assistant",
            "timestamp": "2024-01-01T12:00:00.000Z",
            "channel": channel
        })
    
    async def simulate_call_answered(self, channel_id: str):
        """Simulate call being answered."""
        if channel_id in self.channels:
            self.channels[channel_id]["state"] = "Up"
            await self._send_event({
                "type": "ChannelStateChange",
                "timestamp": "2024-01-01T12:00:01.000Z",
                "channel": self.channels[channel_id]
            })
    
    async def simulate_call_hangup(self, channel_id: str):
        """Simulate call hangup."""
        if channel_id in self.channels:
            self.channels[channel_id]["state"] = "Down"
            await self._send_event({
                "type": "StasisEnd",
                "application": "gemini-voice-assistant",
                "timestamp": "2024-01-01T12:05:00.000Z",
                "channel": self.channels[channel_id]
            })
            del self.channels[channel_id]
    
    async def simulate_dtmf(self, channel_id: str, digit: str):
        """Simulate DTMF digit received."""
        if channel_id in self.channels:
            await self._send_event({
                "type": "ChannelDtmfReceived",
                "timestamp": "2024-01-01T12:01:00.000Z",
                "channel": self.channels[channel_id],
                "digit": digit,
                "duration_ms": 100
            })
    
    async def simulate_talking_events(self, channel_id: str, duration_ms: int = 2000):
        """Simulate talking started and stopped events."""
        if channel_id in self.channels:
            # Talking started
            await self._send_event({
                "type": "ChannelTalkingStarted",
                "timestamp": "2024-01-01T12:01:00.000Z",
                "channel": self.channels[channel_id]
            })
            
            # Wait for duration
            await asyncio.sleep(duration_ms / 1000.0)
            
            # Talking finished
            await self._send_event({
                "type": "ChannelTalkingFinished",
                "timestamp": "2024-01-01T12:01:02.000Z",
                "channel": self.channels[channel_id]
            })
    
    def get_channel(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get channel by ID."""
        return self.channels.get(channel_id)
    
    def get_all_channels(self) -> Dict[str, Dict[str, Any]]:
        """Get all channels."""
        return self.channels.copy()
    
    def get_recordings(self) -> Dict[str, Dict[str, Any]]:
        """Get all recordings."""
        return self.recordings.copy()
    
    def get_playbacks(self) -> Dict[str, Dict[str, Any]]:
        """Get all playbacks."""
        return self.playbacks.copy()
    
    def reset(self):
        """Reset all state."""
        self.channels.clear()
        self.bridges.clear()
        self.recordings.clear()
        self.playbacks.clear()
        self.event_handlers.clear()


class MockARIClient:
    """Mock ARI client for unit testing."""
    
    def __init__(self):
        self.connected = False
        self.base_url = "http://localhost:8088/ari"
        self.username = "test"
        self.password = "test"
        
        # Mock HTTP methods
        self.get = AsyncMock()
        self.post = AsyncMock()
        self.delete = AsyncMock()
        self.put = AsyncMock()
        
        # Setup default responses
        self._setup_default_responses()
    
    def _setup_default_responses(self):
        """Setup default mock responses."""
        # Successful responses
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {"status": "success"}
        
        self.get.return_value = success_response
        self.post.return_value = success_response
        self.delete.return_value = success_response
        self.put.return_value = success_response
    
    async def connect(self) -> bool:
        """Mock connect method."""
        self.connected = True
        return True
    
    async def disconnect(self):
        """Mock disconnect method."""
        self.connected = False
    
    def is_connected(self) -> bool:
        """Check if connected."""
        return self.connected