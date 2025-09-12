"""
Basic Asterisk REST Interface (ARI) handler for telephony integration.
Provides simple call handling with text-to-speech responses.
"""

import logging
import time
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request

from .base_ari_handler import BaseARIHandler, ARIEvent, CallInfo, CallState
from ..utils.dependency_manager import safe_import
from ..utils.error_handler import handle_errors
from ..ai.gemini_client import GeminiClient
from ..audio.text_to_speech import TextToSpeech
from config.settings import get_settings

logger = logging.getLogger(__name__)


class ARIHandler(BaseARIHandler):
    """Basic ARI handler with text-to-speech capabilities"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize basic ARI handler"""
        super().__init__(config)
        
        # Initialize AI and TTS components
        self.gemini_client = GeminiClient()
        self.tts = TextToSpeech()
        
        logger.info("Basic ARI Handler initialized")
    
    # Implement required abstract methods from BaseARIHandler
    
    @handle_errors(logger)
    def _handle_stasis_start(self, event: ARIEvent) -> Dict[str, Any]:
        """Handle call start event"""
        if not event.channel_id:
            return {"status": "error", "message": "No channel in event"}
        
        channel_id = event.channel_id
        
        # Create call info
        call_info = self._create_call_info(event)
        self.active_calls[channel_id] = call_info
        
        # Update statistics
        self.stats["total_calls"] += 1
        
        logger.info(f"Call started: {channel_id} from {call_info.caller_number}")
        
        # Answer the call
        if self.answer_call(channel_id):
            call_info.state = CallState.ANSWERED
            
            # Play welcome message
            welcome_message = f"Hello! I'm {self.settings.assistant_name}, your AI assistant. How can I help you today?"
            self._play_message(channel_id, welcome_message)
        
        # Trigger call started event
        self._trigger_event_handlers("call_started", {
            "channel_id": channel_id,
            "call_info": call_info.to_dict()
        })
        
        return {"status": "handled", "action": "call_started"}
    
    @handle_errors(logger)
    def _handle_stasis_end(self, event: ARIEvent) -> Dict[str, Any]:
        """Handle call end event"""
        if not event.channel_id:
            return {"status": "error", "message": "No channel in event"}
        
        channel_id = event.channel_id
        
        # End the call using base class method
        self._end_call(channel_id)
        
        return {"status": "handled", "action": "call_ended"}
    
    @handle_errors(logger)
    def _handle_talking_started(self, event: ARIEvent) -> Dict[str, Any]:
        """Handle when caller starts talking"""
        # Call base class implementation first
        result = super()._handle_talking_started(event)
        
        if event.channel_id and result["status"] == "handled":
            channel_id = event.channel_id
            
            # Stop any current playback
            self._stop_current_playback(channel_id)
            
            # Start recording
            recording_name = self.start_recording(channel_id)
            if recording_name:
                # Store recording name in call metadata
                if channel_id in self.active_calls:
                    self.active_calls[channel_id].metadata["current_recording"] = recording_name
        
        return result
    
    @handle_errors(logger)
    def _handle_talking_finished(self, event: ARIEvent) -> Dict[str, Any]:
        """Handle when caller stops talking"""
        # Call base class implementation first
        result = super()._handle_talking_finished(event)
        
        if event.channel_id and result["status"] == "handled":
            channel_id = event.channel_id
            
            # Stop current recording
            if channel_id in self.active_calls:
                recording_name = self.active_calls[channel_id].metadata.get("current_recording")
                if recording_name:
                    self.stop_recording(recording_name)
                    del self.active_calls[channel_id].metadata["current_recording"]
        
        return result
    
    @handle_errors(logger)
    def _handle_recording_finished(self, event: ARIEvent) -> Dict[str, Any]:
        """Handle recording completion"""
        # Call base class implementation first
        result = super()._handle_recording_finished(event)
        
        if event.recording and result["status"] == "handled":
            recording_name = event.recording["name"]
            
            # Process the recording
            self._process_recording(recording_name)
        
        return result
    
    # Remove duplicate methods - using base class implementations
    
    @handle_errors(logger)
    def _play_message(self, channel_id: str, message: str):
        """Play text message to caller using TTS"""
        try:
            # Generate audio file
            audio_filename = f"response_{channel_id}_{int(time.time())}.mp3"
            audio_path = f"{self.settings.sounds_dir}/{audio_filename}"
            
            if self.tts.create_audio_file(message, audio_path):
                # Play audio file using base class method
                playback_id = self.play_audio(channel_id, f"sound:{audio_filename}")
                
                if playback_id and channel_id in self.active_calls:
                    # Store playback ID for potential stopping
                    self.active_calls[channel_id].metadata["current_playback"] = playback_id
                    
                logger.debug(f"Playing message to {channel_id}: {message[:50]}...")
            else:
                logger.error(f"Failed to create audio file for message")
                
        except Exception as e:
            logger.error(f"Failed to play message to {channel_id}: {e}")
    
    @handle_errors(logger)
    def _stop_current_playback(self, channel_id: str):
        """Stop current playback on channel"""
        if channel_id in self.active_calls:
            playback_id = self.active_calls[channel_id].metadata.get("current_playback")
            if playback_id:
                self.stop_playback(playback_id)
                del self.active_calls[channel_id].metadata["current_playback"]
    
    @handle_errors(logger)
    def _process_recording(self, recording_name: str):
        """Process completed recording with AI"""
        try:
            logger.info(f"Processing recording: {recording_name}")
            
            # TODO: Implement speech-to-text processing
            # TODO: Generate AI response using Gemini
            # TODO: Play response back to caller
            
            # For now, just acknowledge the recording
            logger.debug(f"Recording {recording_name} processed (placeholder implementation)")
            
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