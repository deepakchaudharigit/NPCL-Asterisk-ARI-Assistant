"""
Asterisk REST Interface (ARI) handler for telephony integration
"""

import logging
import json
import time
import requests
from typing import Dict, Any, Optional, Callable
from fastapi import FastAPI, Request
from pydantic import BaseModel

from ..core.assistant import VoiceAssistant
from ..ai.gemini_client import GeminiClient
from ..audio.text_to_speech import TextToSpeech
from config.settings import get_settings

logger = logging.getLogger(__name__)


class ARIEvent(BaseModel):
    """ARI event model"""
    type: str
    application: str
    timestamp: str
    channel: Optional[Dict[str, Any]] = None
    recording: Optional[Dict[str, Any]] = None


class ARIHandler:
    """Handler for Asterisk REST Interface events"""
    
    def __init__(self):
        """Initialize ARI handler"""
        self.settings = get_settings()
        self.gemini_client = GeminiClient()
        self.tts = TextToSpeech()
        
        # Active calls tracking
        self.active_calls: Dict[str, Dict[str, Any]] = {}
        
        # ARI connection settings
        self.ari_url = self.settings.ari_base_url
        self.ari_auth = (self.settings.ari_username, self.settings.ari_password)
        
        logger.info("ARI Handler initialized")
    
    def handle_ari_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming ARI event
        
        Args:
            event_data: ARI event data
            
        Returns:
            Response data
        """
        try:
            event = ARIEvent(**event_data)
            logger.info(f"Received ARI event: {event.type}")
            
            # Route event to appropriate handler
            if event.type == "StasisStart":
                return self._handle_stasis_start(event)
            elif event.type == "StasisEnd":
                return self._handle_stasis_end(event)
            elif event.type == "ChannelTalkingStarted":
                return self._handle_talking_started(event)
            elif event.type == "ChannelTalkingFinished":
                return self._handle_talking_finished(event)
            elif event.type == "RecordingFinished":
                return self._handle_recording_finished(event)
            else:
                logger.debug(f"Unhandled event type: {event.type}")
                return {"status": "ignored"}
                
        except Exception as e:
            logger.error(f"Error handling ARI event: {e}")
            return {"status": "error", "message": str(e)}
    
    def _handle_stasis_start(self, event: ARIEvent) -> Dict[str, Any]:
        """Handle call start event"""
        if not event.channel:
            return {"status": "error", "message": "No channel in event"}
        
        channel_id = event.channel["id"]
        caller_number = event.channel.get("caller", {}).get("number", "Unknown")
        
        logger.info(f"Call started: {channel_id} from {caller_number}")
        
        # Track active call
        self.active_calls[channel_id] = {
            "caller_number": caller_number,
            "start_time": event.timestamp,
            "conversation_history": []
        }
        
        # Answer the call
        self._answer_call(channel_id)
        
        # Play welcome message
        welcome_message = f"Hello! I'm {self.settings.assistant_name}, your AI assistant. How can I help you today?"
        self._play_message(channel_id, welcome_message)
        
        return {"status": "handled", "action": "call_started"}
    
    def _handle_stasis_end(self, event: ARIEvent) -> Dict[str, Any]:
        """Handle call end event"""
        if not event.channel:
            return {"status": "error", "message": "No channel in event"}
        
        channel_id = event.channel["id"]
        logger.info(f"Call ended: {channel_id}")
        
        # Clean up call data
        if channel_id in self.active_calls:
            call_data = self.active_calls.pop(channel_id)
            logger.info(f"Call duration: {len(call_data['conversation_history'])} exchanges")
        
        return {"status": "handled", "action": "call_ended"}
    
    def _handle_talking_started(self, event: ARIEvent) -> Dict[str, Any]:
        """Handle when caller starts talking"""
        if not event.channel:
            return {"status": "error", "message": "No channel in event"}
        
        channel_id = event.channel["id"]
        logger.debug(f"Caller started talking: {channel_id}")
        
        # Stop any current playback
        self._stop_playback(channel_id)
        
        # Start recording
        self._start_recording(channel_id)
        
        return {"status": "handled", "action": "recording_started"}
    
    def _handle_talking_finished(self, event: ARIEvent) -> Dict[str, Any]:
        """Handle when caller stops talking"""
        if not event.channel:
            return {"status": "error", "message": "No channel in event"}
        
        channel_id = event.channel["id"]
        logger.debug(f"Caller stopped talking: {channel_id}")
        
        # Stop recording
        self._stop_recording(channel_id)
        
        return {"status": "handled", "action": "recording_stopped"}
    
    def _handle_recording_finished(self, event: ARIEvent) -> Dict[str, Any]:
        """Handle recording completion"""
        if not event.recording:
            return {"status": "error", "message": "No recording in event"}
        
        recording_name = event.recording["name"]
        logger.info(f"Recording finished: {recording_name}")
        
        # Process the recording
        self._process_recording(recording_name)
        
        return {"status": "handled", "action": "recording_processed"}
    
    def _answer_call(self, channel_id: str):
        """Answer incoming call"""
        try:
            url = f"{self.ari_url}/channels/{channel_id}/answer"
            response = requests.post(url, auth=self.ari_auth)
            response.raise_for_status()
            logger.debug(f"Call answered: {channel_id}")
        except Exception as e:
            logger.error(f"Failed to answer call {channel_id}: {e}")
    
    def _play_message(self, channel_id: str, message: str):
        """Play text message to caller"""
        try:
            # Generate audio file
            audio_filename = f"response_{channel_id}_{int(time.time())}.mp3"
            audio_path = f"{self.settings.sounds_dir}/{audio_filename}"
            
            if self.tts.create_audio_file(message, audio_path):
                # Play audio file
                url = f"{self.ari_url}/channels/{channel_id}/play"
                data = {"media": f"sound:{audio_filename}"}
                response = requests.post(url, json=data, auth=self.ari_auth)
                response.raise_for_status()
                logger.debug(f"Playing message to {channel_id}")
            else:
                logger.error(f"Failed to create audio file for message")
                
        except Exception as e:
            logger.error(f"Failed to play message to {channel_id}: {e}")
    
    def _start_recording(self, channel_id: str):
        """Start recording caller audio"""
        try:
            recording_name = f"recording_{channel_id}_{int(time.time())}"
            url = f"{self.ari_url}/channels/{channel_id}/record"
            data = {
                "name": recording_name,
                "format": "wav",
                "maxDurationSeconds": 30,
                "maxSilenceSeconds": 3,
                "terminateOn": "none"
            }
            response = requests.post(url, json=data, auth=self.ari_auth)
            response.raise_for_status()
            logger.debug(f"Started recording: {recording_name}")
        except Exception as e:
            logger.error(f"Failed to start recording for {channel_id}: {e}")
    
    def _stop_recording(self, channel_id: str):
        """Stop current recording"""
        try:
            url = f"{self.ari_url}/recordings/live/{channel_id}"
            response = requests.delete(url, auth=self.ari_auth)
            # Don't raise for 404 - recording might not exist
            if response.status_code not in [200, 404]:
                response.raise_for_status()
            logger.debug(f"Stopped recording for {channel_id}")
        except Exception as e:
            logger.error(f"Failed to stop recording for {channel_id}: {e}")
    
    def _stop_playback(self, channel_id: str):
        """Stop current playback"""
        try:
            url = f"{self.ari_url}/channels/{channel_id}/play"
            response = requests.delete(url, auth=self.ari_auth)
            # Don't raise for 404 - playback might not exist
            if response.status_code not in [200, 404]:
                response.raise_for_status()
            logger.debug(f"Stopped playback for {channel_id}")
        except Exception as e:
            logger.error(f"Failed to stop playback for {channel_id}: {e}")
    
    def _process_recording(self, recording_name: str):
        """Process completed recording"""
        try:
            # This would typically involve:
            # 1. Getting the recording file
            # 2. Converting speech to text
            # 3. Generating AI response
            # 4. Playing response back to caller
            
            # For now, just log the event
            logger.info(f"Processing recording: {recording_name}")
            
            # TODO: Implement speech-to-text processing
            # TODO: Generate Gemini response
            # TODO: Play response back
            
        except Exception as e:
            logger.error(f"Failed to process recording {recording_name}: {e}")


def create_ari_app() -> FastAPI:
    """Create FastAPI application for ARI events"""
    app = FastAPI(title="Voice Assistant ARI Handler")
    ari_handler = ARIHandler()
    
    @app.post("/ari/events")
    async def handle_ari_event(request: Request):
        """Handle incoming ARI events"""
        event_data = await request.json()
        return ari_handler.handle_ari_event(event_data)
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {"status": "healthy", "service": "voice-assistant-ari"}
    
    return app