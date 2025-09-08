"""
Simplified Advanced ARI handler without WebSocket dependencies
"""

import logging
import json
import time
import asyncio
import requests
from typing import Dict, Any, Optional, List, Callable
from fastapi import FastAPI, Request
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


class SimpleAdvancedARIHandler:
    """Simplified Advanced ARI handler with full features (no WebSocket)"""
    
    def __init__(self):
        """Initialize simplified advanced ARI handler"""
        self.settings = get_settings()
        
        # ARI connection settings
        self.ari_url = self.settings.ari_base_url
        self.ari_auth = (self.settings.ari_username, self.settings.ari_password)
        
        # State tracking
        self.channels: Dict[str, Channel] = {}
        self.bridges: Dict[str, Bridge] = {}
        self.recordings: Dict[str, Recording] = {}
        self.active_calls: Dict[str, Dict[str, Any]] = {}
        
        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = {}
        
        logger.info("Simple Advanced ARI Handler initialized")
    
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
                        if asyncio.iscoroutinefunction(handler):
                            await handler(event_data)
                        else:
                            handler(event_data)
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
    
    # ==================== Audio Operations ====================
    
    async def play_media(self, channel_id: str, media: str, lang: str = "en") -> Optional[str]:
        """Play media to channel"""
        try:
            url = f"{self.ari_url}/channels/{channel_id}/play"
            data = {"media": media, "lang": lang}
            response = requests.post(url, json=data, auth=self.ari_auth)
            response.raise_for_status()
            
            playback_data = response.json()
            playback_id = playback_data["id"]
            
            logger.info(f"Started playback {playback_id} on channel {channel_id}")
            return playback_id
            
        except Exception as e:
            logger.error(f"Failed to play media on channel {channel_id}: {e}")
            return None
    
    async def start_recording(self, channel_id: str, name: str, format: str = "wav") -> Optional[str]:
        """Start recording on channel"""
        try:
            url = f"{self.ari_url}/channels/{channel_id}/record"
            data = {"name": name, "format": format}
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
    
    # ==================== DTMF Operations ====================
    
    async def send_dtmf(self, channel_id: str, dtmf: str) -> bool:
        """Send DTMF to channel"""
        try:
            url = f"{self.ari_url}/channels/{channel_id}/dtmf"
            data = {"dtmf": dtmf}
            response = requests.post(url, json=data, auth=self.ari_auth)
            response.raise_for_status()
            
            logger.info(f"Sent DTMF '{dtmf}' to channel {channel_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send DTMF to channel {channel_id}: {e}")
            return False
    
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
        
        # Play welcome message
        await self.play_media(channel_id, "sound:hello-world")
        
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
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get system status"""
        return {
            "active_channels": len(self.channels),
            "active_bridges": len(self.bridges),
            "active_calls": len(self.active_calls),
            "active_recordings": len(self.recordings),
            "websocket_connected": False  # Not supported in simple version
        }


def create_simple_advanced_ari_app() -> FastAPI:
    """Create FastAPI application with simplified advanced ARI features"""
    app = FastAPI(title="Simple Advanced Voice Assistant ARI Handler")
    ari_handler = SimpleAdvancedARIHandler()
    
    @app.post("/ari/events")
    async def handle_ari_event(request: Request):
        """Handle incoming ARI events"""
        event_data = await request.json()
        return await ari_handler.handle_ari_event(event_data)
    
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
    
    @app.post("/ari/channels/{channel_id}/answer")
    async def answer_channel(channel_id: str):
        """Answer a channel"""
        result = await ari_handler.answer_channel(channel_id)
        return {"success": result}
    
    @app.delete("/ari/channels/{channel_id}")
    async def hangup_channel(channel_id: str):
        """Hangup a channel"""
        result = await ari_handler.hangup_channel(channel_id)
        return {"success": result}
    
    @app.post("/ari/channels/{channel_id}/hold")
    async def hold_channel(channel_id: str):
        """Put channel on hold"""
        result = await ari_handler.hold_channel(channel_id)
        return {"success": result}
    
    @app.delete("/ari/channels/{channel_id}/hold")
    async def unhold_channel(channel_id: str):
        """Remove channel from hold"""
        result = await ari_handler.unhold_channel(channel_id)
        return {"success": result}
    
    @app.post("/ari/bridges")
    async def create_bridge(bridge_type: str = "mixing", name: str = None):
        """Create a new bridge"""
        bridge_id = await ari_handler.create_bridge(bridge_type, name)
        return {"bridge_id": bridge_id, "success": bridge_id is not None}
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {"status": "healthy", "service": "simple-advanced-voice-assistant-ari"}
    
    return app