"""
Advanced Asterisk REST Interface (ARI) handler with full feature support
"""

import logging
import json
import time
import asyncio
import websockets
import requests
from typing import Dict, Any, Optional, List, Callable
from fastapi import FastAPI, Request, WebSocket
from pydantic import BaseModel
from enum import Enum

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from config.settings import get_settings

logger = logging.getLogger(__name__)


class ChannelState(Enum):
    """Channel state enumeration"""
    DOWN = "Down"
    RESERVED = "Rsrvd"
    OFFHOOK = "OffHook"
    DIALING = "Dialing"
    RING = "Ring"
    RINGING = "Ringing"
    UP = "Up"
    BUSY = "Busy"
    DIALING_OFFHOOK = "Dialing Offhook"
    PRE_RING = "Pre-ring"
    UNKNOWN = "Unknown"


class BridgeType(Enum):
    """Bridge type enumeration"""
    MIXING = "mixing"
    HOLDING = "holding"
    DTMF_EVENTS = "dtmf_events"
    PROXY_MEDIA = "proxy_media"


class ARIEventType(Enum):
    """ARI event types"""
    STASIS_START = "StasisStart"
    STASIS_END = "StasisEnd"
    CHANNEL_CREATED = "ChannelCreated"
    CHANNEL_DESTROYED = "ChannelDestroyed"
    CHANNEL_STATE_CHANGE = "ChannelStateChange"
    CHANNEL_DTMF_RECEIVED = "ChannelDtmfReceived"
    CHANNEL_TALKING_STARTED = "ChannelTalkingStarted"
    CHANNEL_TALKING_FINISHED = "ChannelTalkingFinished"
    BRIDGE_CREATED = "BridgeCreated"
    BRIDGE_DESTROYED = "BridgeDestroyed"
    CHANNEL_ENTERED_BRIDGE = "ChannelEnteredBridge"
    CHANNEL_LEFT_BRIDGE = "ChannelLeftBridge"
    RECORDING_STARTED = "RecordingStarted"
    RECORDING_FINISHED = "RecordingFinished"
    PLAYBACK_STARTED = "PlaybackStarted"
    PLAYBACK_FINISHED = "PlaybackFinished"


class Channel(BaseModel):
    """Channel model"""
    id: str
    name: str
    state: str
    caller: Optional[Dict[str, Any]] = None
    connected: Optional[Dict[str, Any]] = None
    accountcode: Optional[str] = None
    dialplan: Optional[Dict[str, Any]] = None
    creationtime: Optional[str] = None


class Bridge(BaseModel):
    """Bridge model"""
    id: str
    technology: str
    bridge_type: str
    bridge_class: str
    creator: Optional[str] = None
    name: Optional[str] = None
    channels: List[str] = []


class Recording(BaseModel):
    """Recording model"""
    name: str
    format: str
    state: str
    duration: Optional[int] = None
    talking_duration: Optional[int] = None
    silence_duration: Optional[int] = None


class AdvancedARIHandler:
    """Advanced ARI handler with full feature support"""
    
    def __init__(self):
        """Initialize advanced ARI handler"""
        self.settings = get_settings()
        
        # ARI connection settings
        self.ari_url = self.settings.ari_base_url
        self.ari_auth = (self.settings.ari_username, self.settings.ari_password)
        self.ws_url = self.ari_url.replace("http", "ws") + "/events"
        
        # State tracking
        self.channels: Dict[str, Channel] = {}
        self.bridges: Dict[str, Bridge] = {}
        self.recordings: Dict[str, Recording] = {}
        self.active_calls: Dict[str, Dict[str, Any]] = {}
        
        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = {}
        
        # WebSocket connection
        self.websocket = None
        self.websocket_task = None
        
        logger.info("Advanced ARI Handler initialized")
    
    # ==================== Event Handling ====================
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """Register an event handler for specific event type"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    async def handle_ari_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming ARI event"""
        try:
            event_type = event_data.get("type")
            logger.debug(f"Received ARI event: {event_type}")
            
            # Update internal state
            await self._update_state(event_data)
            
            # Call registered handlers
            if event_type in self.event_handlers:
                for handler in self.event_handlers[event_type]:
                    try:
                        await handler(event_data)
                    except Exception as e:
                        logger.error(f"Event handler error: {e}")
            
            # Built-in event handling
            return await self._handle_builtin_events(event_data)
            
        except Exception as e:
            logger.error(f"Error handling ARI event: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _update_state(self, event_data: Dict[str, Any]):
        """Update internal state based on event"""
        event_type = event_data.get("type")
        
        if event_type == "ChannelCreated":
            channel_data = event_data.get("channel", {})
            self.channels[channel_data["id"]] = Channel(**channel_data)
        
        elif event_type == "ChannelDestroyed":
            channel_data = event_data.get("channel", {})
            channel_id = channel_data["id"]
            if channel_id in self.channels:
                del self.channels[channel_id]
            if channel_id in self.active_calls:
                del self.active_calls[channel_id]
        
        elif event_type == "BridgeCreated":
            bridge_data = event_data.get("bridge", {})
            self.bridges[bridge_data["id"]] = Bridge(**bridge_data)
        
        elif event_type == "BridgeDestroyed":
            bridge_data = event_data.get("bridge", {})
            bridge_id = bridge_data["id"]
            if bridge_id in self.bridges:
                del self.bridges[bridge_id]
    
    async def _handle_builtin_events(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle built-in events"""
        event_type = event_data.get("type")
        
        if event_type == "StasisStart":
            return await self._handle_stasis_start(event_data)
        elif event_type == "StasisEnd":
            return await self._handle_stasis_end(event_data)
        elif event_type == "ChannelDtmfReceived":
            return await self._handle_dtmf(event_data)
        elif event_type == "ChannelTalkingStarted":
            return await self._handle_talking_started(event_data)
        elif event_type == "ChannelTalkingFinished":
            return await self._handle_talking_finished(event_data)
        else:
            return {"status": "ignored", "event_type": event_type}
    
    # ==================== Channel Management ====================
    
    async def create_channel(self, endpoint: str, extension: str = None, 
                           context: str = "default", priority: int = 1) -> Optional[str]:
        """Create a new channel"""
        try:
            url = f"{self.ari_url}/channels/create"
            data = {
                "endpoint": endpoint,
                "extension": extension,
                "context": context,
                "priority": priority
            }
            response = requests.post(url, json=data, auth=self.ari_auth)
            response.raise_for_status()
            
            channel_data = response.json()
            channel_id = channel_data["id"]
            self.channels[channel_id] = Channel(**channel_data)
            
            logger.info(f"Created channel: {channel_id}")
            return channel_id
            
        except Exception as e:
            logger.error(f"Failed to create channel: {e}")
            return None
    
    async def answer_channel(self, channel_id: str) -> bool:
        """Answer a channel"""
        try:
            url = f"{self.ari_url}/channels/{channel_id}/answer"
            response = requests.post(url, auth=self.ari_auth)
            response.raise_for_status()
            
            logger.info(f"Answered channel: {channel_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to answer channel {channel_id}: {e}")
            return False
    
    async def hangup_channel(self, channel_id: str, reason: str = "normal") -> bool:
        """Hangup a channel"""
        try:
            url = f"{self.ari_url}/channels/{channel_id}"
            params = {"reason": reason}
            response = requests.delete(url, params=params, auth=self.ari_auth)
            response.raise_for_status()
            
            logger.info(f"Hung up channel: {channel_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to hangup channel {channel_id}: {e}")
            return False
    
    async def hold_channel(self, channel_id: str) -> bool:
        """Put channel on hold"""
        try:
            url = f"{self.ari_url}/channels/{channel_id}/hold"
            response = requests.post(url, auth=self.ari_auth)
            response.raise_for_status()
            
            logger.info(f"Put channel on hold: {channel_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to hold channel {channel_id}: {e}")
            return False
    
    async def unhold_channel(self, channel_id: str) -> bool:
        """Remove channel from hold"""
        try:
            url = f"{self.ari_url}/channels/{channel_id}/hold"
            response = requests.delete(url, auth=self.ari_auth)
            response.raise_for_status()
            
            logger.info(f"Removed channel from hold: {channel_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unhold channel {channel_id}: {e}")
            return False
    
    async def mute_channel(self, channel_id: str, direction: str = "both") -> bool:
        """Mute a channel"""
        try:
            url = f"{self.ari_url}/channels/{channel_id}/mute"
            params = {"direction": direction}
            response = requests.post(url, params=params, auth=self.ari_auth)
            response.raise_for_status()
            
            logger.info(f"Muted channel: {channel_id} ({direction})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to mute channel {channel_id}: {e}")
            return False
    
    async def unmute_channel(self, channel_id: str, direction: str = "both") -> bool:
        """Unmute a channel"""
        try:
            url = f"{self.ari_url}/channels/{channel_id}/mute"
            params = {"direction": direction}
            response = requests.delete(url, params=params, auth=self.ari_auth)
            response.raise_for_status()
            
            logger.info(f"Unmuted channel: {channel_id} ({direction})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unmute channel {channel_id}: {e}")
            return False
    
    # ==================== Bridge Management ====================
    
    async def create_bridge(self, bridge_type: str = "mixing", name: str = None) -> Optional[str]:
        """Create a new bridge"""
        try:
            url = f"{self.ari_url}/bridges"
            data = {"type": bridge_type}
            if name:
                data["name"] = name
            
            response = requests.post(url, json=data, auth=self.ari_auth)
            response.raise_for_status()
            
            bridge_data = response.json()
            bridge_id = bridge_data["id"]
            self.bridges[bridge_id] = Bridge(**bridge_data)
            
            logger.info(f"Created bridge: {bridge_id} ({bridge_type})")
            return bridge_id
            
        except Exception as e:
            logger.error(f"Failed to create bridge: {e}")
            return None
    
    async def add_channel_to_bridge(self, bridge_id: str, channel_id: str, role: str = "participant") -> bool:
        """Add channel to bridge"""
        try:
            url = f"{self.ari_url}/bridges/{bridge_id}/addChannel"
            data = {"channel": channel_id, "role": role}
            response = requests.post(url, json=data, auth=self.ari_auth)
            response.raise_for_status()
            
            logger.info(f"Added channel {channel_id} to bridge {bridge_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add channel to bridge: {e}")
            return False
    
    async def remove_channel_from_bridge(self, bridge_id: str, channel_id: str) -> bool:
        """Remove channel from bridge"""
        try:
            url = f"{self.ari_url}/bridges/{bridge_id}/removeChannel"
            data = {"channel": channel_id}
            response = requests.post(url, json=data, auth=self.ari_auth)
            response.raise_for_status()
            
            logger.info(f"Removed channel {channel_id} from bridge {bridge_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove channel from bridge: {e}")
            return False
    
    async def destroy_bridge(self, bridge_id: str) -> bool:
        """Destroy a bridge"""
        try:
            url = f"{self.ari_url}/bridges/{bridge_id}"
            response = requests.delete(url, auth=self.ari_auth)
            response.raise_for_status()
            
            logger.info(f"Destroyed bridge: {bridge_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to destroy bridge {bridge_id}: {e}")
            return False
    
    # ==================== Audio Operations ====================
    
    async def play_media(self, channel_id: str, media: str, lang: str = "en", 
                        offsetms: int = 0, skipms: int = 3000) -> Optional[str]:
        """Play media to channel"""
        try:
            url = f"{self.ari_url}/channels/{channel_id}/play"
            data = {
                "media": media,
                "lang": lang,
                "offsetms": offsetms,
                "skipms": skipms
            }
            response = requests.post(url, json=data, auth=self.ari_auth)
            response.raise_for_status()
            
            playback_data = response.json()
            playback_id = playback_data["id"]
            
            logger.info(f"Started playback {playback_id} on channel {channel_id}")
            return playback_id
            
        except Exception as e:
            logger.error(f"Failed to play media on channel {channel_id}: {e}")
            return None
    
    async def stop_playback(self, playback_id: str) -> bool:
        """Stop playback"""
        try:
            url = f"{self.ari_url}/playbacks/{playback_id}"
            response = requests.delete(url, auth=self.ari_auth)
            response.raise_for_status()
            
            logger.info(f"Stopped playback: {playback_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop playback {playback_id}: {e}")
            return False
    
    async def start_recording(self, channel_id: str, name: str, format: str = "wav",
                            max_duration: int = 0, max_silence: int = 0,
                            terminate_on: str = "none", if_exists: str = "fail") -> Optional[str]:
        """Start recording on channel"""
        try:
            url = f"{self.ari_url}/channels/{channel_id}/record"
            data = {
                "name": name,
                "format": format,
                "maxDurationSeconds": max_duration,
                "maxSilenceSeconds": max_silence,
                "terminateOn": terminate_on,
                "ifExists": if_exists
            }
            response = requests.post(url, json=data, auth=self.ari_auth)
            response.raise_for_status()
            
            recording_data = response.json()
            recording_name = recording_data["name"]
            self.recordings[recording_name] = Recording(**recording_data)
            
            logger.info(f"Started recording {recording_name} on channel {channel_id}")
            return recording_name
            
        except Exception as e:
            logger.error(f"Failed to start recording on channel {channel_id}: {e}")
            return None
    
    async def stop_recording(self, recording_name: str) -> bool:
        """Stop recording"""
        try:
            url = f"{self.ari_url}/recordings/live/{recording_name}"
            response = requests.delete(url, auth=self.ari_auth)
            response.raise_for_status()
            
            logger.info(f"Stopped recording: {recording_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop recording {recording_name}: {e}")
            return False
    
    # ==================== DTMF Operations ====================
    
    async def send_dtmf(self, channel_id: str, dtmf: str, before: int = 0, 
                       between: int = 100, duration: int = 100, after: int = 0) -> bool:
        """Send DTMF to channel"""
        try:
            url = f"{self.ari_url}/channels/{channel_id}/dtmf"
            data = {
                "dtmf": dtmf,
                "before": before,
                "between": between,
                "duration": duration,
                "after": after
            }
            response = requests.post(url, json=data, auth=self.ari_auth)
            response.raise_for_status()
            
            logger.info(f"Sent DTMF '{dtmf}' to channel {channel_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send DTMF to channel {channel_id}: {e}")
            return False
    
    # ==================== WebSocket Support ====================
    
    async def start_websocket_connection(self):
        """Start WebSocket connection for real-time events"""
        try:
            self.websocket_task = asyncio.create_task(self._websocket_handler())
            logger.info("Started WebSocket connection for ARI events")
        except Exception as e:
            logger.error(f"Failed to start WebSocket connection: {e}")
    
    async def _websocket_handler(self):
        """Handle WebSocket connection"""
        while True:
            try:
                async with websockets.connect(
                    f"{self.ws_url}?app=voice-assistant",
                    extra_headers={"Authorization": f"Basic {self.ari_auth}"}
                ) as websocket:
                    self.websocket = websocket
                    logger.info("WebSocket connected")
                    
                    async for message in websocket:
                        try:
                            event_data = json.loads(message)
                            await self.handle_ari_event(event_data)
                        except Exception as e:
                            logger.error(f"Error processing WebSocket message: {e}")
                            
            except Exception as e:
                logger.error(f"WebSocket connection error: {e}")
                await asyncio.sleep(5)  # Reconnect after 5 seconds
    
    # ==================== Event Handlers ====================
    
    async def _handle_stasis_start(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Stasis start event"""
        channel = event_data.get("channel", {})
        channel_id = channel.get("id")
        
        if not channel_id:
            return {"status": "error", "message": "No channel ID"}
        
        # Track the call
        self.active_calls[channel_id] = {
            "start_time": time.time(),
            "caller": channel.get("caller", {}),
            "state": "active"
        }
        
        # Answer the call
        await self.answer_channel(channel_id)
        
        logger.info(f"Stasis started for channel: {channel_id}")
        return {"status": "handled", "action": "stasis_start"}
    
    async def _handle_stasis_end(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Stasis end event"""
        channel = event_data.get("channel", {})
        channel_id = channel.get("id")
        
        if channel_id in self.active_calls:
            call_duration = time.time() - self.active_calls[channel_id]["start_time"]
            logger.info(f"Call ended: {channel_id}, duration: {call_duration:.2f}s")
            del self.active_calls[channel_id]
        
        return {"status": "handled", "action": "stasis_end"}
    
    async def _handle_dtmf(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle DTMF event"""
        channel = event_data.get("channel", {})
        digit = event_data.get("digit")
        
        logger.info(f"DTMF received: {digit} on channel {channel.get('id')}")
        
        # You can implement DTMF-based menu navigation here
        return {"status": "handled", "action": "dtmf_received", "digit": digit}
    
    async def _handle_talking_started(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle talking started event"""
        channel = event_data.get("channel", {})
        channel_id = channel.get("id")
        
        logger.debug(f"Talking started on channel: {channel_id}")
        return {"status": "handled", "action": "talking_started"}
    
    async def _handle_talking_finished(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle talking finished event"""
        channel = event_data.get("channel", {})
        channel_id = channel.get("id")
        
        logger.debug(f"Talking finished on channel: {channel_id}")
        return {"status": "handled", "action": "talking_finished"}
    
    # ==================== Status and Information ====================
    
    def get_channel_info(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get channel information"""
        if channel_id in self.channels:
            return self.channels[channel_id].dict()
        return None
    
    def get_bridge_info(self, bridge_id: str) -> Optional[Dict[str, Any]]:
        """Get bridge information"""
        if bridge_id in self.bridges:
            return self.bridges[bridge_id].dict()
        return None
    
    def get_active_calls(self) -> Dict[str, Dict[str, Any]]:
        """Get all active calls"""
        return self.active_calls.copy()
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get system status"""
        return {
            "active_channels": len(self.channels),
            "active_bridges": len(self.bridges),
            "active_calls": len(self.active_calls),
            "active_recordings": len(self.recordings),
            "websocket_connected": self.websocket is not None
        }


def create_advanced_ari_app() -> FastAPI:
    """Create FastAPI application with advanced ARI features"""
    app = FastAPI(title="Advanced Voice Assistant ARI Handler")
    ari_handler = AdvancedARIHandler()
    
    @app.post("/ari/events")
    async def handle_ari_event(request: Request):
        """Handle incoming ARI events"""
        event_data = await request.json()
        return await ari_handler.handle_ari_event(event_data)
    
    @app.websocket("/ari/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket endpoint for real-time events"""
        await websocket.accept()
        # Add WebSocket client management here
    
    @app.get("/ari/channels")
    async def get_channels():
        """Get all active channels"""
        return list(ari_handler.channels.values())
    
    @app.get("/ari/bridges")
    async def get_bridges():
        """Get all active bridges"""
        return list(ari_handler.bridges.values())
    
    @app.get("/ari/status")
    async def get_status():
        """Get system status"""
        return ari_handler.get_system_status()
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {"status": "healthy", "service": "advanced-voice-assistant-ari"}
    
    return app