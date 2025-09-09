"""
Real-time microphone streaming for Gemini Live API
Captures audio from microphone and streams it to the Live API
"""

import asyncio
import logging
import threading
import time
from typing import Optional, Callable, Dict, Any
import pyaudio
import numpy as np
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MicrophoneConfig:
    """Configuration for microphone streaming"""
    sample_rate: int = 16000  # 16kHz for Gemini Live API
    channels: int = 1  # Mono
    sample_width: int = 2  # 16-bit
    chunk_size: int = 320  # 20ms at 16kHz
    format: int = pyaudio.paInt16
    device_index: Optional[int] = None


class MicrophoneStream:
    """Real-time microphone audio streaming"""
    
    def __init__(self, config: MicrophoneConfig = None):
        self.config = config or MicrophoneConfig()
        self.audio = None
        self.stream = None
        self.is_streaming = False
        self.audio_callback: Optional[Callable[[bytes], None]] = None
        
        # Threading
        self.stream_thread = None
        self.stop_event = threading.Event()
        
        logger.info("Microphone stream initialized")
    
    def set_audio_callback(self, callback: Callable[[bytes], None]):
        """Set callback for audio data"""
        self.audio_callback = callback
        logger.debug("Audio callback set")
    
    def start_streaming(self) -> bool:
        """Start microphone streaming"""
        if self.is_streaming:
            logger.warning("Microphone already streaming")
            return True
        
        try:
            # Initialize PyAudio
            self.audio = pyaudio.PyAudio()
            
            # Check if device is available
            if not self._check_microphone():
                return False
            
            # Open audio stream
            self.stream = self.audio.open(
                format=self.config.format,
                channels=self.config.channels,
                rate=self.config.sample_rate,
                input=True,
                input_device_index=self.config.device_index,
                frames_per_buffer=self.config.chunk_size,
                stream_callback=self._audio_callback
            )
            
            # Start streaming
            self.stream.start_stream()
            self.is_streaming = True
            
            logger.info("Microphone streaming started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start microphone streaming: {e}")
            self._cleanup()
            return False
    
    def stop_streaming(self):
        """Stop microphone streaming"""
        if not self.is_streaming:
            return
        
        logger.info("Stopping microphone streaming...")
        
        self.is_streaming = False
        self.stop_event.set()
        
        self._cleanup()
        
        logger.info("Microphone streaming stopped")
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """PyAudio callback for audio data"""
        if status:
            logger.warning(f"Audio callback status: {status}")
        
        if self.audio_callback and self.is_streaming:
            try:
                self.audio_callback(in_data)
            except Exception as e:
                logger.error(f"Error in audio callback: {e}")
        
        return (None, pyaudio.paContinue)
    
    def _check_microphone(self) -> bool:
        """Check if microphone is available"""
        try:
            if self.config.device_index is not None:
                device_info = self.audio.get_device_info_by_index(self.config.device_index)
                logger.info(f"Using microphone: {device_info['name']}")
            else:
                device_info = self.audio.get_default_input_device_info()
                logger.info(f"Using default microphone: {device_info['name']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Microphone check failed: {e}")
            return False
    
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
    
    def get_available_devices(self) -> Dict[int, Dict[str, Any]]:
        """Get list of available audio input devices"""
        devices = {}
        
        try:
            if not self.audio:
                temp_audio = pyaudio.PyAudio()
            else:
                temp_audio = self.audio
            
            for i in range(temp_audio.get_device_count()):
                try:
                    device_info = temp_audio.get_device_info_by_index(i)
                    if device_info['maxInputChannels'] > 0:
                        devices[i] = {
                            'name': device_info['name'],
                            'channels': device_info['maxInputChannels'],
                            'sample_rate': device_info['defaultSampleRate']
                        }
                except Exception:
                    continue
            
            if not self.audio:
                temp_audio.terminate()
                
        except Exception as e:
            logger.error(f"Error getting audio devices: {e}")
        
        return devices
    
    def test_microphone(self, duration: float = 2.0) -> bool:
        """Test microphone by recording for a short duration"""
        try:
            logger.info(f"Testing microphone for {duration} seconds...")
            
            # Temporary callback to collect audio
            audio_data = []
            
            def test_callback(data):
                audio_data.append(data)
            
            # Set test callback
            old_callback = self.audio_callback
            self.audio_callback = test_callback
            
            # Start streaming
            if not self.start_streaming():
                return False
            
            # Record for specified duration
            time.sleep(duration)
            
            # Stop streaming
            self.stop_streaming()
            
            # Restore old callback
            self.audio_callback = old_callback
            
            # Check if we got audio data
            if audio_data:
                total_samples = sum(len(chunk) for chunk in audio_data)
                logger.info(f"Microphone test successful: {total_samples} bytes recorded")
                return True
            else:
                logger.error("Microphone test failed: No audio data received")
                return False
                
        except Exception as e:
            logger.error(f"Microphone test failed: {e}")
            return False


class VoiceActivityDetector:
    """Simple voice activity detection for microphone stream"""
    
    def __init__(self, config: MicrophoneConfig = None):
        self.config = config or MicrophoneConfig()
        self.energy_threshold = 4000
        self.silence_threshold = 0.5  # seconds
        self.speech_threshold = 0.1   # seconds
        
        # State
        self.is_speaking = False
        self.last_speech_time = 0
        self.last_silence_time = 0
        self.energy_history = []
        
        # Callbacks
        self.on_speech_start: Optional[Callable] = None
        self.on_speech_end: Optional[Callable] = None
        
        logger.info("Voice Activity Detector initialized")
    
    def set_callbacks(self, on_speech_start: Callable = None, on_speech_end: Callable = None):
        """Set VAD callbacks"""
        self.on_speech_start = on_speech_start
        self.on_speech_end = on_speech_end
    
    def process_audio(self, audio_data: bytes) -> Dict[str, Any]:
        """Process audio data for voice activity detection"""
        try:
            # Convert to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            # Calculate energy
            energy = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))
            
            # Update energy history
            self.energy_history.append(energy)
            if len(self.energy_history) > 10:
                self.energy_history.pop(0)
            
            # Determine if speech is present
            current_time = time.time()
            is_speech = energy > self.energy_threshold
            
            # State machine
            if is_speech and not self.is_speaking:
                if current_time - self.last_speech_time < self.speech_threshold:
                    self.is_speaking = True
                    if self.on_speech_start:
                        self.on_speech_start()
                    logger.debug("Speech started")
                self.last_speech_time = current_time
                
            elif not is_speech and self.is_speaking:
                if current_time - self.last_silence_time > self.silence_threshold:
                    self.is_speaking = False
                    if self.on_speech_end:
                        self.on_speech_end()
                    logger.debug("Speech ended")
                self.last_silence_time = current_time
            
            elif is_speech:
                self.last_speech_time = current_time
            else:
                self.last_silence_time = current_time
            
            return {
                "is_speaking": self.is_speaking,
                "energy": energy,
                "average_energy": sum(self.energy_history) / len(self.energy_history),
                "speech_detected": is_speech
            }
            
        except Exception as e:
            logger.error(f"Error in VAD processing: {e}")
            return {
                "is_speaking": False,
                "energy": 0,
                "average_energy": 0,
                "speech_detected": False
            }
    
    def reset(self):
        """Reset VAD state"""
        self.is_speaking = False
        self.last_speech_time = 0
        self.last_silence_time = 0
        self.energy_history = []
        logger.debug("VAD state reset")


class LiveAudioStreamer:
    """Streams microphone audio to Gemini Live API"""
    
    def __init__(self, gemini_live_client, config: MicrophoneConfig = None):
        self.gemini_live = gemini_live_client
        self.config = config or MicrophoneConfig()
        
        # Components
        self.microphone = MicrophoneStream(self.config)
        self.vad = VoiceActivityDetector(self.config)
        
        # State
        self.is_streaming = False
        self.loop = None
        
        # Setup callbacks
        self.microphone.set_audio_callback(self._on_audio_data)
        self.vad.set_callbacks(
            on_speech_start=self._on_speech_start,
            on_speech_end=self._on_speech_end
        )
        
        logger.info("Live audio streamer initialized")
    
    def start_streaming(self, event_loop) -> bool:
        """Start streaming audio to Live API"""
        if self.is_streaming:
            return True
        
        self.loop = event_loop
        
        # Start microphone
        if not self.microphone.start_streaming():
            return False
        
        self.is_streaming = True
        logger.info("Live audio streaming started")
        return True
    
    def stop_streaming(self):
        """Stop streaming audio"""
        if not self.is_streaming:
            return
        
        self.is_streaming = False
        self.microphone.stop_streaming()
        self.vad.reset()
        
        logger.info("Live audio streaming stopped")
    
    def _on_audio_data(self, audio_data: bytes):
        """Handle audio data from microphone"""
        if not self.is_streaming or not self.loop:
            return
        
        try:
            # Process with VAD
            vad_result = self.vad.process_audio(audio_data)
            
            # Send audio to Live API
            if self.gemini_live.is_connected:
                future = asyncio.run_coroutine_threadsafe(
                    self.gemini_live.send_audio_chunk(audio_data),
                    self.loop
                )
                # Don't wait for result to avoid blocking
                
        except Exception as e:
            logger.error(f"Error processing audio data: {e}")
    
    def _on_speech_start(self):
        """Handle speech start event"""
        logger.debug("Speech started - Live API will detect this")
    
    def _on_speech_end(self):
        """Handle speech end event"""
        logger.debug("Speech ended - Live API will detect this")
        
        # Commit audio buffer
        if self.is_streaming and self.loop and self.gemini_live.is_connected:
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self.gemini_live.commit_audio_buffer(),
                    self.loop
                )
                # Don't wait for result
            except Exception as e:
                logger.error(f"Error committing audio buffer: {e}")
    
    def test_setup(self) -> bool:
        """Test the audio streaming setup"""
        logger.info("Testing live audio streaming setup...")
        
        # Test microphone
        if not self.microphone.test_microphone(duration=1.0):
            return False
        
        # Test Live API connection
        if not self.gemini_live.is_connected:
            logger.error("Live API not connected")
            return False
        
        logger.info("Live audio streaming setup test passed")
        return True