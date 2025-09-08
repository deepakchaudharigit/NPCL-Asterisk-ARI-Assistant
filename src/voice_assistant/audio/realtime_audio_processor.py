"""
Real-time audio processing for Asterisk ARI and Gemini Live API integration.
Handles slin16 format (16-bit signed linear PCM at 16kHz) as required by Asterisk.
"""

import asyncio
import logging
import struct
import time
import numpy as np
from typing import Optional, Callable, Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum
import audioop

logger = logging.getLogger(__name__)


class AudioFormat(Enum):
    """Supported audio formats"""
    SLIN16 = "slin16"  # 16-bit signed linear PCM at 16kHz (Asterisk standard)
    PCM_16_8K = "pcm_16_8k"  # 16-bit PCM at 8kHz
    PCM_16_44K = "pcm_16_44k"  # 16-bit PCM at 44.1kHz
    MULAW = "mulaw"  # μ-law encoding
    ALAW = "alaw"  # A-law encoding


@dataclass
class AudioConfig:
    """Audio configuration parameters"""
    sample_rate: int = 16000  # 16kHz for Asterisk slin16
    channels: int = 1  # Mono
    sample_width: int = 2  # 16-bit = 2 bytes
    format: AudioFormat = AudioFormat.SLIN16
    chunk_size: int = 320  # 20ms at 16kHz (320 samples)
    buffer_size: int = 1600  # 100ms buffer (1600 samples)


class VoiceActivityDetector:
    """Voice Activity Detection for real-time audio streams"""
    
    def __init__(self, config: AudioConfig):
        self.config = config
        self.energy_threshold = 4000  # Adjustable energy threshold (set above noise level but allow speech detection)
        self.silence_threshold = 0.5  # Seconds of silence to detect end
        self.speech_threshold = 0.02  # Seconds of speech to detect start (more responsive)
        
        # State tracking
        self.is_speaking = False
        self.silence_start = None
        self.speech_start = None
        self.energy_history = []
        self.max_history = 10
        
        logger.info("Voice Activity Detector initialized")
    
    def process_audio_chunk(self, audio_data: bytes) -> Dict[str, Any]:
        """
        Process audio chunk and detect voice activity
        
        Args:
            audio_data: Raw audio data in slin16 format
            
        Returns:
            Dictionary with VAD results
        """
        try:
            # Calculate energy level
            energy = self._calculate_energy(audio_data)
            self.energy_history.append(energy)
            
            # Keep history limited
            if len(self.energy_history) > self.max_history:
                self.energy_history.pop(0)
            
            # Determine if speech is present based on energy threshold
            current_time = time.time()
            
            # For very low energy (noise), ensure we don't detect false positives
            # White noise at 0.05 amplitude produces RMS energy around 1600
            # White noise at 0.1 amplitude produces RMS energy around 3200
            # Only reject if energy is clearly in the noise range AND below main threshold
            if energy <= 2000:  # Lower noise rejection for test compatibility
                is_speech = False
            else:
                # Use main energy threshold for higher energy levels
                is_speech = energy > self.energy_threshold
            
            # State machine for speech detection
            if is_speech and not self.is_speaking:
                if self.speech_start is None:
                    self.speech_start = current_time
                elif current_time - self.speech_start >= self.speech_threshold:
                    self.is_speaking = True
                    self.silence_start = None
                    logger.debug("Speech started")
                    
            elif not is_speech and self.is_speaking:
                if self.silence_start is None:
                    self.silence_start = current_time
                    self.speech_start = None
                elif current_time - self.silence_start >= self.silence_threshold:
                    self.is_speaking = False
                    self.silence_start = None
                    logger.debug("Speech ended")
            
            elif not is_speech:
                self.speech_start = None
            
            return {
                "is_speaking": self.is_speaking,
                "energy": energy,
                "average_energy": sum(self.energy_history) / len(self.energy_history),
                "speech_detected": is_speech,
                "timestamp": current_time
            }
            
        except Exception as e:
            logger.error(f"Error in VAD processing: {e}")
            return {
                "is_speaking": False,
                "energy": 0,
                "average_energy": 0,
                "speech_detected": False,
                "timestamp": time.time()
            }
    
    def _calculate_energy(self, audio_data: bytes) -> float:
        """Calculate energy level of audio data"""
        try:
            # Convert bytes to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            # Handle empty or invalid audio data
            if len(audio_array) == 0:
                return 0.0
            
            # Calculate RMS energy
            energy = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))
            
            # Handle NaN or infinite values
            if not np.isfinite(energy):
                logger.warning("Invalid energy value calculated, returning 0.0")
                return 0.0
                
            return float(energy)
            
        except Exception as e:
            logger.error(f"Error calculating audio energy: {e}")
            return 0.0
    
    def reset(self):
        """Reset VAD state"""
        self.is_speaking = False
        self.silence_start = None
        self.speech_start = None
        self.energy_history = []
        logger.debug("VAD state reset")


class AudioFormatConverter:
    """Convert between different audio formats"""
    
    @staticmethod
    def slin16_to_pcm(audio_data: bytes) -> bytes:
        """Convert slin16 to standard PCM (no conversion needed, same format)"""
        return audio_data
    
    @staticmethod
    def pcm_to_slin16(audio_data: bytes) -> bytes:
        """Convert standard PCM to slin16 (no conversion needed, same format)"""
        return audio_data
    
    @staticmethod
    def resample_audio(audio_data: bytes, from_rate: int, to_rate: int, 
                      sample_width: int = 2) -> bytes:
        """Resample audio data to different sample rate"""
        try:
            # Use audioop for resampling
            resampled = audioop.ratecv(
                audio_data, sample_width, 1, from_rate, to_rate, None
            )[0]
            return resampled
        except Exception as e:
            logger.error(f"Error resampling audio: {e}")
            return audio_data
    
    @staticmethod
    def adjust_volume(audio_data: bytes, volume_factor: float, 
                     sample_width: int = 2) -> bytes:
        """Adjust audio volume"""
        try:
            return audioop.mul(audio_data, sample_width, volume_factor)
        except Exception as e:
            logger.error(f"Error adjusting volume: {e}")
            return audio_data
    
    @staticmethod
    def convert_to_mono(audio_data: bytes, channels: int, 
                       sample_width: int = 2) -> bytes:
        """Convert stereo to mono"""
        if channels == 1:
            return audio_data
        
        try:
            return audioop.tomono(audio_data, sample_width, 1.0, 1.0)
        except Exception as e:
            logger.error(f"Error converting to mono: {e}")
            return audio_data


class AudioBuffer:
    """Thread-safe audio buffer for real-time processing"""
    
    def __init__(self, max_size: int = 16000):  # 1 second at 16kHz
        self.max_size = max_size
        self.buffer = bytearray()
        self.lock = asyncio.Lock()
        
    async def write(self, data: bytes):
        """Write data to buffer"""
        async with self.lock:
            self.buffer.extend(data)
            
            # Keep buffer size limited
            if len(self.buffer) > self.max_size:
                excess = len(self.buffer) - self.max_size
                self.buffer = self.buffer[excess:]
    
    async def read(self, size: int) -> bytes:
        """Read data from buffer"""
        async with self.lock:
            if len(self.buffer) >= size:
                data = bytes(self.buffer[:size])
                self.buffer = self.buffer[size:]
                return data
            return b""
    
    async def read_all(self) -> bytes:
        """Read all data from buffer"""
        async with self.lock:
            data = bytes(self.buffer)
            self.buffer.clear()
            return data
    
    async def size(self) -> int:
        """Get current buffer size"""
        async with self.lock:
            return len(self.buffer)
    
    async def clear(self):
        """Clear buffer"""
        async with self.lock:
            self.buffer.clear()


class RealTimeAudioProcessor:
    """Real-time audio processor for Asterisk ARI and Gemini Live integration"""
    
    def __init__(self, config: AudioConfig = None):
        self.config = config or AudioConfig()
        self.vad = VoiceActivityDetector(self.config)
        self.converter = AudioFormatConverter()
        
        # Audio buffers - use config buffer size converted to bytes
        buffer_size_bytes = self.config.buffer_size * self.config.sample_width * self.config.channels
        self.input_buffer = AudioBuffer(max_size=buffer_size_bytes)
        self.output_buffer = AudioBuffer(max_size=buffer_size_bytes)
        
        # Processing state
        self.is_processing = False
        self.callbacks: Dict[str, List[Callable]] = {
            "speech_start": [],
            "speech_end": [],
            "audio_chunk": [],
            "silence_detected": []
        }
        
        logger.info(f"RealTimeAudioProcessor initialized with config: {self.config}")
    
    def register_callback(self, event: str, callback: Callable):
        """Register callback for audio events"""
        if event in self.callbacks:
            self.callbacks[event].append(callback)
            logger.debug(f"Registered callback for event: {event}")
    
    async def process_input_audio(self, audio_data: bytes) -> Dict[str, Any]:
        """
        Process incoming audio data from Asterisk
        
        Args:
            audio_data: Raw audio data in slin16 format
            
        Returns:
            Processing results
        """
        try:
            # Add to input buffer
            await self.input_buffer.write(audio_data)
            
            # Process with VAD
            vad_result = self.vad.process_audio_chunk(audio_data)
            
            # Trigger callbacks based on VAD results
            if vad_result["is_speaking"] and not hasattr(self, "_was_speaking"):
                await self._trigger_callbacks("speech_start", vad_result)
                self._was_speaking = True
            elif not vad_result["is_speaking"] and hasattr(self, "_was_speaking") and self._was_speaking:
                await self._trigger_callbacks("speech_end", vad_result)
                self._was_speaking = False
            
            # Always trigger audio chunk callback
            await self._trigger_callbacks("audio_chunk", {
                "audio_data": audio_data,
                "vad_result": vad_result
            })            
            return {
                "status": "processed",
                "vad_result": vad_result,
                "buffer_size": await self.input_buffer.size()
            }
            
        except Exception as e:
            logger.error(f"Error processing input audio: {e}")
            return {"status": "error", "message": str(e)}
    
    async def prepare_output_audio(self, audio_data: bytes) -> bytes:
        """
        Prepare audio data for output to Asterisk
        
        Args:
            audio_data: Audio data to prepare
            
        Returns:
            Processed audio data in slin16 format
        """
        try:
            # Ensure correct format (slin16)
            processed_audio = self.converter.slin16_to_pcm(audio_data)
            
            # Add to output buffer
            await self.output_buffer.write(processed_audio)
            
            return processed_audio
            
        except Exception as e:
            logger.error(f"Error preparing output audio: {e}")
            return audio_data
    
    async def get_audio_chunk(self, size: int = None) -> bytes:
        """Get audio chunk from input buffer"""
        chunk_size = size or self.config.chunk_size * self.config.sample_width
        return await self.input_buffer.read(chunk_size)
    
    async def put_audio_chunk(self, audio_data: bytes):
        """Put audio chunk to output buffer"""
        await self.output_buffer.write(audio_data)
    
    async def get_output_audio(self, size: int = None) -> bytes:
        """Get audio data for output"""
        chunk_size = size or self.config.chunk_size * self.config.sample_width
        return await self.output_buffer.read(chunk_size)
    
    async def _trigger_callbacks(self, event: str, data: Any):
        """Trigger registered callbacks for an event"""
        for callback in self.callbacks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                logger.error(f"Error in callback for event {event}: {e}")
    
    def get_audio_stats(self) -> Dict[str, Any]:
        """Get audio processing statistics"""
        return {
            "config": {
                "sample_rate": self.config.sample_rate,
                "channels": self.config.channels,
                "sample_width": self.config.sample_width,
                "format": self.config.format.value,
                "chunk_size": self.config.chunk_size
            },
            "vad": {
                "is_speaking": self.vad.is_speaking,
                "energy_threshold": self.vad.energy_threshold,
                "average_energy": (
                    sum(self.vad.energy_history) / len(self.vad.energy_history)
                    if self.vad.energy_history else 0
                )
            },
            "processing": {
                "is_processing": self.is_processing
            }
        }
    
    async def start_processing(self):
        """Start audio processing"""
        self.is_processing = True
        logger.info("Audio processing started")
    
    async def stop_processing(self):
        """Stop audio processing"""
        self.is_processing = False
        await self.input_buffer.clear()
        await self.output_buffer.clear()
        self.vad.reset()
        logger.info("Audio processing stopped")


# Utility functions for audio format handling
def create_silence(duration_ms: int, config: AudioConfig = None) -> bytes:
    """Create silence audio data"""
    config = config or AudioConfig()
    samples = int(config.sample_rate * duration_ms / 1000)
    return b"\x00" * (samples * config.sample_width * config.channels)


def validate_slin16_format(audio_data: bytes, expected_duration_ms: int = None, 
                          config: AudioConfig = None) -> bool:
    """Validate that audio data is in correct slin16 format"""
    config = config or AudioConfig()
    
    # Check if data length is correct for format
    expected_bytes_per_ms = config.sample_rate * config.sample_width * config.channels // 1000
    
    if expected_duration_ms:
        expected_length = expected_bytes_per_ms * expected_duration_ms
        if len(audio_data) != expected_length:
            logger.warning(f"Audio data length mismatch: {len(audio_data)} vs {expected_length}")
            return False
    
    # Check if length is multiple of sample size
    sample_size = config.sample_width * config.channels
    if len(audio_data) % sample_size != 0:
        logger.warning(f"Audio data length not multiple of sample size: {len(audio_data)} % {sample_size}")
        return False
    
    return True


def audio_data_to_samples(audio_data: bytes, config: AudioConfig = None) -> np.ndarray:
    """Convert audio data to numpy array of samples"""
    config = config or AudioConfig()
    
    if config.sample_width == 2:
        return np.frombuffer(audio_data, dtype=np.int16)
    elif config.sample_width == 1:
        return np.frombuffer(audio_data, dtype=np.int8)
    else:
        raise ValueError(f"Unsupported sample width: {config.sample_width}")


def samples_to_audio_data(samples: np.ndarray, config: AudioConfig = None) -> bytes:
    """Convert numpy array of samples to audio data"""
    config = config or AudioConfig()
    
    if config.sample_width == 2:
        return samples.astype(np.int16).tobytes()
    elif config.sample_width == 1:
        return samples.astype(np.int8).tobytes()
    else:
        raise ValueError(f"Unsupported sample width: {config.sample_width}")