"""
Real-time audio player for Gemini Live API responses
Plays audio responses directly from the Live API
"""

import logging
import threading
import time
from typing import Optional
import pyaudio
import numpy as np
from collections import deque

logger = logging.getLogger(__name__)


class RealTimeAudioPlayer:
    """Real-time audio player for streaming audio responses"""
    
    def __init__(self, sample_rate: int = 16000, channels: int = 1, sample_width: int = 2):
        self.sample_rate = sample_rate
        self.channels = channels
        self.sample_width = sample_width
        self.format = pyaudio.paInt16
        
        # PyAudio
        self.audio = None
        self.stream = None
        
        # Audio buffer
        self.audio_buffer = deque()
        self.buffer_lock = threading.Lock()
        
        # Playback state
        self.is_playing = False
        self.playback_thread = None
        self.stop_event = threading.Event()
        
        logger.info("Real-time audio player initialized")
    
    def start_playback(self) -> bool:
        """Start audio playback"""
        if self.is_playing:
            return True
        
        try:
            # Initialize PyAudio
            self.audio = pyaudio.PyAudio()
            
            # Open output stream
            self.stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                output=True,
                frames_per_buffer=1024
            )
            
            # Start playback thread
            self.stop_event.clear()
            self.playback_thread = threading.Thread(target=self._playback_loop, daemon=True)
            self.playback_thread.start()
            
            self.is_playing = True
            logger.info("Audio playback started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start audio playback: {e}")
            self._cleanup()
            return False
    
    def stop_playback(self):
        """Stop audio playback"""
        if not self.is_playing:
            return
        
        logger.info("Stopping audio playback...")
        
        self.is_playing = False
        self.stop_event.set()
        
        # Wait for playback thread to finish
        if self.playback_thread and self.playback_thread.is_alive():
            self.playback_thread.join(timeout=2.0)
        
        self._cleanup()
        
        # Clear buffer
        with self.buffer_lock:
            self.audio_buffer.clear()
        
        logger.info("Audio playback stopped")
    
    def add_audio_data(self, audio_data: bytes):
        """Add audio data to playback buffer"""
        if not self.is_playing:
            return
        
        with self.buffer_lock:
            self.audio_buffer.append(audio_data)
    
    def _playback_loop(self):
        """Main playback loop"""
        try:
            while self.is_playing and not self.stop_event.is_set():
                # Get audio data from buffer
                audio_data = None
                with self.buffer_lock:
                    if self.audio_buffer:
                        audio_data = self.audio_buffer.popleft()
                
                if audio_data:
                    try:
                        # Play audio data
                        self.stream.write(audio_data)
                    except Exception as e:
                        logger.error(f"Error playing audio: {e}")
                        break
                else:
                    # No audio data, wait a bit
                    time.sleep(0.01)
                    
        except Exception as e:
            logger.error(f"Error in playback loop: {e}")
        finally:
            logger.debug("Playback loop ended")
    
    def _cleanup(self):
        """Cleanup audio resources"""
        try:
            if self.stream:
                if self.stream.is_active():
                    self.stream.stop_stream()
                self.stream.close()
                self.stream = None
            
            if self.audio:
                self.audio.terminate()
                self.audio = None
                
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def get_buffer_size(self) -> int:
        """Get current buffer size"""
        with self.buffer_lock:
            return len(self.audio_buffer)
    
    def clear_buffer(self):
        """Clear audio buffer"""
        with self.buffer_lock:
            self.audio_buffer.clear()
        logger.debug("Audio buffer cleared")
    
    def test_playback(self, duration: float = 1.0) -> bool:
        """Test audio playback with a tone"""
        try:
            logger.info(f"Testing audio playback for {duration} seconds...")
            
            # Generate test tone (440 Hz)
            samples = int(self.sample_rate * duration)
            t = np.linspace(0, duration, samples, False)
            tone = np.sin(2 * np.pi * 440 * t) * 0.3  # 440 Hz at 30% volume
            
            # Convert to int16
            audio_data = (tone * 32767).astype(np.int16).tobytes()
            
            # Start playback
            if not self.start_playback():
                return False
            
            # Add test audio
            self.add_audio_data(audio_data)
            
            # Wait for playback
            time.sleep(duration + 0.5)
            
            # Stop playback
            self.stop_playback()
            
            logger.info("Audio playback test completed")
            return True
            
        except Exception as e:
            logger.error(f"Audio playback test failed: {e}")
            return False


class LiveAPIAudioHandler:
    """Handles audio from Gemini Live API"""
    
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.player = RealTimeAudioPlayer(sample_rate=sample_rate)
        self.is_active = False
        
        logger.info("Live API audio handler initialized")
    
    def start(self) -> bool:
        """Start audio handling"""
        if self.is_active:
            return True
        
        if self.player.start_playback():
            self.is_active = True
            logger.info("Live API audio handler started")
            return True
        else:
            logger.error("Failed to start Live API audio handler")
            return False
    
    def stop(self):
        """Stop audio handling"""
        if not self.is_active:
            return
        
        self.player.stop_playback()
        self.is_active = False
        logger.info("Live API audio handler stopped")
    
    def handle_audio_response(self, audio_data: bytes):
        """Handle audio response from Live API"""
        if self.is_active:
            self.player.add_audio_data(audio_data)
            logger.debug(f"Added {len(audio_data)} bytes to audio buffer")
    
    def clear_audio_buffer(self):
        """Clear audio buffer (for interruptions)"""
        if self.is_active:
            self.player.clear_buffer()
            logger.debug("Audio buffer cleared for interruption")
    
    def get_status(self) -> dict:
        """Get audio handler status"""
        return {
            "is_active": self.is_active,
            "is_playing": self.player.is_playing if self.player else False,
            "buffer_size": self.player.get_buffer_size() if self.player else 0,
            "sample_rate": self.sample_rate
        }