"""
Base ARI handler providing common functionality for all ARI implementations.
Eliminates code duplication and provides consistent error handling and logging.
"""

import logging
import time
import uuid
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass
from enum import Enum
import requests
from pydantic import BaseModel

from ..utils.dependency_manager import get_dependency_manager, safe_import
from ..utils.error_handler import ErrorHandler, handle_errors
from config.settings import get_settings

logger = logging.getLogger(__name__)


class ARIEventType(Enum):
    """Standard ARI event types"""
    STASIS_START = "StasisStart"
    STASIS_END = "StasisEnd"
    CHANNEL_STATE_CHANGE = "ChannelStateChange"
    CHANNEL_HANGUP_REQUEST = "ChannelHangupRequest"
    CHANNEL_TALKING_STARTED = "ChannelTalkingStarted"
    CHANNEL_TALKING_FINISHED = "ChannelTalkingFinished"
    RECORDING_STARTED = "RecordingStarted"
    RECORDING_FINISHED = "RecordingFinished"
    PLAYBACK_STARTED = "PlaybackStarted"
    PLAYBACK_FINISHED = "PlaybackFinished"


class CallState(Enum):
    """Call state enumeration"""
    INITIALIZING = "initializing"
    RINGING = "ringing"
    ANSWERED = "answered"
    ACTIVE = "active"
    HOLDING = "holding"
    ENDING = "ending"
    ENDED = "ended"
    ERROR = "error"


class ARIEvent(BaseModel):
    """Standardized ARI event model"""
    type: str
    application: Optional[str] = None
    timestamp: str
    channel: Optional[Dict[str, Any]] = None
    bridge: Optional[Dict[str, Any]] = None
    recording: Optional[Dict[str, Any]] = None
    playback: Optional[Dict[str, Any]] = None
    
    @property
    def event_type(self) -> ARIEventType:
        """Get event type as enum"""
        try:
            return ARIEventType(self.type)
        except ValueError:
            logger.warning(f"Unknown ARI event type: {self.type}")
            return None
    
    @property
    def channel_id(self) -> Optional[str]:
        """Get channel ID from event"""
        return self.channel.get("id") if self.channel else None
    
    @property
    def caller_number(self) -> Optional[str]:
        """Get caller number from event"""
        if self.channel and "caller" in self.channel:
            return self.channel["caller"].get("number")
        return None


@dataclass
class CallInfo:
    """Information about an active call"""
    channel_id: str
    session_id: Optional[str] = None
    caller_number: Optional[str] = None
    called_number: Optional[str] = None
    start_time: float = None
    state: CallState = CallState.INITIALIZING
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.start_time is None:
            self.start_time = time.time()
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def duration(self) -> float:
        """Get call duration in seconds"""
        return time.time() - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "channel_id": self.channel_id,
            "session_id": self.session_id,
            "caller_number": self.caller_number,
            "called_number": self.called_number,
            "start_time": self.start_time,
            "duration": self.duration,
            "state": self.state.value,
            "metadata": self.metadata
        }


class BaseARIHandler(ABC):
    """
    Base class for all ARI handlers providing common functionality
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize base ARI handler
        
        Args:
            config: Optional configuration override
        """
        self.settings = get_settings()
        self.config = config or {}
        self.error_handler = ErrorHandler()
        
        # ARI connection settings
        self.ari_base_url = self.config.get("ari_base_url", self.settings.ari_base_url)
        self.ari_username = self.config.get("ari_username", self.settings.ari_username)
        self.ari_password = self.config.get("ari_password", self.settings.ari_password)
        self.ari_auth = (self.ari_username, self.ari_password)
        
        # State tracking
        self.active_calls: Dict[str, CallInfo] = {}
        self.is_running = False
        
        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = {
            "call_started": [],
            "call_ended": [],
            "call_state_changed": [],
            "error": [],
            "recording_finished": [],
            "playback_finished": []
        }
        
        # Statistics
        self.stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "start_time": time.time()
        }
        
        logger.info(f"{self.__class__.__name__} initialized")
    
    @handle_errors(logger)
    def handle_ari_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main event handler - routes events to specific handlers
        
        Args:
            event_data: Raw ARI event data
            
        Returns:
            Response dictionary
        """
        try:
            event = ARIEvent(**event_data)
            logger.debug(f"Handling ARI event: {event.type} for channel {event.channel_id}")
            
            # Route to specific handler
            handler_map = {
                ARIEventType.STASIS_START: self._handle_stasis_start,
                ARIEventType.STASIS_END: self._handle_stasis_end,
                ARIEventType.CHANNEL_STATE_CHANGE: self._handle_channel_state_change,
                ARIEventType.CHANNEL_HANGUP_REQUEST: self._handle_hangup_request,
                ARIEventType.CHANNEL_TALKING_STARTED: self._handle_talking_started,
                ARIEventType.CHANNEL_TALKING_FINISHED: self._handle_talking_finished,
                ARIEventType.RECORDING_FINISHED: self._handle_recording_finished,
                ARIEventType.PLAYBACK_FINISHED: self._handle_playback_finished
            }
            
            if event.event_type in handler_map:
                return handler_map[event.event_type](event)
            else:
                logger.debug(f"Unhandled event type: {event.type}")
                return {"status": "ignored", "event_type": event.type}
                
        except Exception as e:
            self.error_handler.handle_error(e, {"event_data": event_data})
            return {"status": "error", "message": str(e)}
    
    @abstractmethod
    def _handle_stasis_start(self, event: ARIEvent) -> Dict[str, Any]:
        """Handle call start - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    def _handle_stasis_end(self, event: ARIEvent) -> Dict[str, Any]:
        """Handle call end - must be implemented by subclasses"""
        pass
    
    def _handle_channel_state_change(self, event: ARIEvent) -> Dict[str, Any]:
        """Handle channel state change"""
        if not event.channel_id:
            return {"status": "ignored", "reason": "no_channel_id"}
        
        channel_id = event.channel_id
        new_state = event.channel.get("state", "Unknown")
        
        logger.debug(f"Channel {channel_id} state changed to: {new_state}")
        
        # Update call state if we're tracking this call
        if channel_id in self.active_calls:
            call_info = self.active_calls[channel_id]
            
            # Map ARI states to our CallState enum
            state_mapping = {
                "Ring": CallState.RINGING,
                "Up": CallState.ACTIVE,
                "Down": CallState.ENDED,
                "Ringing": CallState.RINGING
            }
            
            if new_state in state_mapping:
                old_state = call_info.state
                call_info.state = state_mapping[new_state]
                
                # Trigger state change event
                self._trigger_event_handlers("call_state_changed", {
                    "channel_id": channel_id,
                    "old_state": old_state.value,
                    "new_state": call_info.state.value,
                    "call_info": call_info.to_dict()
                })
        
        return {"status": "handled", "action": "state_updated", "new_state": new_state}
    
    def _handle_hangup_request(self, event: ARIEvent) -> Dict[str, Any]:
        """Handle hangup request"""
        if not event.channel_id:
            return {"status": "ignored", "reason": "no_channel_id"}
        
        channel_id = event.channel_id
        logger.info(f"Hangup requested for channel: {channel_id}")
        
        # End the call
        self._end_call(channel_id)
        
        return {"status": "handled", "action": "hangup_processed"}
    
    def _handle_talking_started(self, event: ARIEvent) -> Dict[str, Any]:
        """Handle talking started event"""
        if not event.channel_id:
            return {"status": "ignored", "reason": "no_channel_id"}
        
        channel_id = event.channel_id
        logger.debug(f"Talking started on channel: {channel_id}")
        
        # Update call metadata
        if channel_id in self.active_calls:
            self.active_calls[channel_id].metadata["is_talking"] = True
        
        return {"status": "handled", "action": "talking_started"}
    
    def _handle_talking_finished(self, event: ARIEvent) -> Dict[str, Any]:
        """Handle talking finished event"""
        if not event.channel_id:
            return {"status": "ignored", "reason": "no_channel_id"}
        
        channel_id = event.channel_id
        logger.debug(f"Talking finished on channel: {channel_id}")
        
        # Update call metadata
        if channel_id in self.active_calls:
            self.active_calls[channel_id].metadata["is_talking"] = False
        
        return {"status": "handled", "action": "talking_finished"}
    
    def _handle_recording_finished(self, event: ARIEvent) -> Dict[str, Any]:
        """Handle recording finished event"""
        if not event.recording:
            return {"status": "ignored", "reason": "no_recording_info"}
        
        recording_name = event.recording.get("name", "unknown")
        logger.info(f"Recording finished: {recording_name}")
        
        # Trigger recording finished event
        self._trigger_event_handlers("recording_finished", {
            "recording_name": recording_name,
            "recording_info": event.recording
        })
        
        return {"status": "handled", "action": "recording_processed"}
    
    def _handle_playback_finished(self, event: ARIEvent) -> Dict[str, Any]:
        """Handle playback finished event"""
        if not event.playback:
            return {"status": "ignored", "reason": "no_playback_info"}
        
        playback_id = event.playback.get("id", "unknown")
        logger.debug(f"Playback finished: {playback_id}")
        
        # Trigger playback finished event
        self._trigger_event_handlers("playback_finished", {
            "playback_id": playback_id,
            "playback_info": event.playback
        })
        
        return {"status": "handled", "action": "playback_finished"}
    
    @handle_errors(logger)
    def _create_call_info(self, event: ARIEvent) -> CallInfo:
        """Create CallInfo from ARI event"""
        return CallInfo(
            channel_id=event.channel_id,
            caller_number=event.caller_number,
            called_number=event.channel.get("dialplan", {}).get("exten") if event.channel else None,
            start_time=time.time(),
            state=CallState.INITIALIZING
        )
    
    @handle_errors(logger)
    def _end_call(self, channel_id: str):
        """End call and cleanup resources"""
        logger.info(f"Ending call: {channel_id}")
        
        # Get call info before removal
        call_info = self.active_calls.get(channel_id)
        
        if call_info:
            call_info.state = CallState.ENDED
            
            # Update statistics
            if call_info.state != CallState.ERROR:
                self.stats["successful_calls"] += 1
            else:
                self.stats["failed_calls"] += 1
            
            # Trigger call ended event
            self._trigger_event_handlers("call_ended", {
                "channel_id": channel_id,
                "call_info": call_info.to_dict(),
                "duration": call_info.duration
            })
            
            # Remove from active calls
            del self.active_calls[channel_id]
        
        logger.debug(f"Call {channel_id} cleanup completed")
    
    # ARI API Helper Methods
    
    @handle_errors(logger)
    def answer_call(self, channel_id: str) -> bool:
        """Answer incoming call"""
        try:
            url = f"{self.ari_base_url}/channels/{channel_id}/answer"
            response = requests.post(url, auth=self.ari_auth, timeout=10)
            response.raise_for_status()
            
            logger.info(f"Answered call: {channel_id}")
            
            # Update call state
            if channel_id in self.active_calls:
                self.active_calls[channel_id].state = CallState.ANSWERED
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to answer call {channel_id}: {e}")
            return False
    
    @handle_errors(logger)
    def hangup_call(self, channel_id: str) -> bool:
        """Hangup call"""
        try:
            url = f"{self.ari_base_url}/channels/{channel_id}"
            response = requests.delete(url, auth=self.ari_auth, timeout=10)
            response.raise_for_status()
            
            logger.info(f"Hung up call: {channel_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to hangup call {channel_id}: {e}")
            return False
    
    @handle_errors(logger)
    def start_recording(self, channel_id: str, recording_name: Optional[str] = None) -> Optional[str]:
        """Start recording on channel"""
        if recording_name is None:
            recording_name = f"recording_{channel_id}_{int(time.time())}"
        
        try:
            url = f"{self.ari_base_url}/channels/{channel_id}/record"
            data = {
                "name": recording_name,
                "format": "wav",
                "maxDurationSeconds": 30,
                "maxSilenceSeconds": 3,
                "terminateOn": "none"
            }
            response = requests.post(url, json=data, auth=self.ari_auth, timeout=10)
            response.raise_for_status()
            
            logger.debug(f"Started recording: {recording_name}")
            return recording_name
            
        except Exception as e:
            logger.error(f"Failed to start recording for {channel_id}: {e}")
            return None
    
    @handle_errors(logger)
    def stop_recording(self, recording_name: str) -> bool:
        """Stop recording"""
        try:
            url = f"{self.ari_base_url}/recordings/live/{recording_name}"
            response = requests.delete(url, auth=self.ari_auth, timeout=10)
            
            # Don't raise for 404 - recording might not exist
            if response.status_code not in [200, 404]:
                response.raise_for_status()
            
            logger.debug(f"Stopped recording: {recording_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop recording {recording_name}: {e}")
            return False
    
    @handle_errors(logger)
    def play_audio(self, channel_id: str, media: str, playback_id: Optional[str] = None) -> Optional[str]:
        """Play audio on channel"""
        if playback_id is None:
            playback_id = f"playback_{channel_id}_{int(time.time())}"
        
        try:
            url = f"{self.ari_base_url}/channels/{channel_id}/play/{playback_id}"
            data = {"media": media}
            response = requests.post(url, json=data, auth=self.ari_auth, timeout=10)
            response.raise_for_status()
            
            logger.debug(f"Started playback {playback_id} on channel {channel_id}")
            return playback_id
            
        except Exception as e:
            logger.error(f"Failed to play audio on {channel_id}: {e}")
            return None
    
    @handle_errors(logger)
    def stop_playback(self, playback_id: str) -> bool:
        """Stop playback"""
        try:
            url = f"{self.ari_base_url}/playbacks/{playback_id}"
            response = requests.delete(url, auth=self.ari_auth, timeout=10)
            
            # Don't raise for 404 - playback might not exist
            if response.status_code not in [200, 404]:
                response.raise_for_status()
            
            logger.debug(f"Stopped playback: {playback_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop playback {playback_id}: {e}")
            return False
    
    # Event Management
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """Register event handler"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
        logger.debug(f"Registered handler for event: {event_type}")
    
    def _trigger_event_handlers(self, event_type: str, event_data: Dict[str, Any]):
        """Trigger registered event handlers"""
        handlers = self.event_handlers.get(event_type, [])
        
        for handler in handlers:
            try:
                handler(event_data)
            except Exception as e:
                logger.error(f"Error in event handler for {event_type}: {e}")
                self._trigger_event_handlers("error", {
                    "source": "event_handler",
                    "event_type": event_type,
                    "error": str(e),
                    "event_data": event_data
                })
    
    # Status and Information
    
    def get_call_info(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get information about specific call"""
        call_info = self.active_calls.get(channel_id)
        return call_info.to_dict() if call_info else None
    
    def get_active_calls(self) -> List[Dict[str, Any]]:
        """Get list of all active calls"""
        return [call_info.to_dict() for call_info in self.active_calls.values()]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get handler statistics"""
        uptime = time.time() - self.stats["start_time"]
        
        return {
            **self.stats,
            "uptime_seconds": uptime,
            "active_calls": len(self.active_calls),
            "calls_per_hour": (self.stats["total_calls"] / uptime * 3600) if uptime > 0 else 0,
            "success_rate": (
                self.stats["successful_calls"] / self.stats["total_calls"] * 100
                if self.stats["total_calls"] > 0 else 0
            )
        }
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            "handler_type": self.__class__.__name__,
            "is_running": self.is_running,
            "statistics": self.get_statistics(),
            "active_calls": self.get_active_calls(),
            "config": {
                "ari_base_url": self.ari_base_url,
                "ari_username": self.ari_username
            }
        }