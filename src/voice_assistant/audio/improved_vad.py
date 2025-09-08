"""
Improved Voice Activity Detection with adaptive noise floor and hysteresis.
"""

from dataclasses import dataclass
import numpy as np
import math
from typing import Optional
import time


@dataclass
class VADConfig:
    """Configuration for improved VAD"""
    sample_rate: int = 16000
    frame_ms: int = 20
    min_speech_ms: int = 120       # min duration to confirm speech
    min_silence_ms: int = 200      # min duration to confirm silence
    noise_lr: float = 0.05         # noise-floor learning rate
    on_margin_db: float = 10.0     # speech when energy > noise + margin
    off_margin_db: float = 6.0     # back to silence when energy < noise + margin
    hangover_ms: int = 120         # keep speech for a bit after dropping
    min_floor_db: float = -70.0    # clamp (avoid -inf)


class ImprovedVoiceActivityDetector:
    """Improved VAD with adaptive noise floor and hysteresis"""
    
    def __init__(self, cfg: VADConfig = None):
        self.cfg = cfg or VADConfig()
        self.frame_len = int(self.cfg.sample_rate * self.cfg.frame_ms / 1000)
        self.noise_db: Optional[float] = None
        self.state = "silence"
        self.state_frames = 0
        self.hang_frames_left = 0
        
        # For compatibility with existing interface
        self.is_speaking = False
        self.energy_threshold = 1000  # Not used in new implementation
        self.silence_threshold = self.cfg.min_silence_ms / 1000.0
        self.speech_threshold = self.cfg.min_speech_ms / 1000.0
        
        # State tracking for compatibility
        self.silence_start = None
        self.speech_start = None
        self.energy_history = []
        self.max_history = 10

    @staticmethod
    def _pcm16_to_float(x: np.ndarray) -> np.ndarray:
        """Convert PCM16 to float32 in [-1,1] range"""
        if x.dtype != np.int16:
            x = x.astype(np.int16, copy=False)
        return (x.astype(np.float32)) / 32768.0

    def _frame_db(self, pcm_bytes: bytes) -> float:
        """Calculate frame energy in dB"""
        x = np.frombuffer(pcm_bytes, dtype=np.int16)
        if x.size == 0:
            return self.cfg.min_floor_db
        
        x = self._pcm16_to_float(x)
        # DC remove
        x = x - np.mean(x)
        # avoid log(0)
        rms = float(np.sqrt(np.mean(x * x) + 1e-12))
        db = 20.0 * math.log10(rms + 1e-9)
        return max(db, self.cfg.min_floor_db)

    def reset(self):
        """Reset VAD state"""
        self.noise_db = None
        self.state = "silence"
        self.state_frames = 0
        self.hang_frames_left = 0
        self.is_speaking = False
        self.silence_start = None
        self.speech_start = None
        self.energy_history = []

    def process_frame(self, pcm_bytes: bytes) -> bool:
        """Process a single frame and return True if speech detected"""
        db = self._frame_db(pcm_bytes)

        if self.noise_db is None:
            self.noise_db = db

        # Update noise floor slowly towards current energy (only downward quickly)
        if db < self.noise_db:
            self.noise_db = (1 - self.cfg.noise_lr) * self.noise_db + self.cfg.noise_lr * db
        else:
            self.noise_db = 0.995 * self.noise_db + 0.005 * db  # rise even slower

        on_th = self.noise_db + self.cfg.on_margin_db
        off_th = self.noise_db + self.cfg.off_margin_db

        is_speech_now = db > (on_th if self.state == "silence" else off_th)

        # State machine w/ hangover and min durations
        if self.state == "silence":
            if is_speech_now:
                self.state_frames += 1
                if self.state_frames * self.cfg.frame_ms >= self.cfg.min_speech_ms:
                    self.state = "speech"
                    self.hang_frames_left = int(self.cfg.hangover_ms / self.cfg.frame_ms)
                    self.state_frames = 0
                    self.is_speaking = True
            else:
                self.state_frames = 0
        else:  # speech
            if is_speech_now:
                self.hang_frames_left = int(self.cfg.hangover_ms / self.cfg.frame_ms)
                self.state_frames = 0
            else:
                if self.hang_frames_left > 0:
                    self.hang_frames_left -= 1
                else:
                    self.state_frames += 1
                    if self.state_frames * self.cfg.frame_ms >= self.cfg.min_silence_ms:
                        self.state = "silence"
                        self.state_frames = 0
                        self.is_speaking = False
        
        return self.state == "speech"

    def process_audio_chunk(self, audio_data: bytes) -> dict:
        """Process audio chunk and return VAD results (compatibility interface)"""
        try:
            # Calculate energy for compatibility
            energy = self._calculate_energy(audio_data)
            self.energy_history.append(energy)
            
            # Keep history limited
            if len(self.energy_history) > self.max_history:
                self.energy_history.pop(0)
            
            current_time = time.time()
            
            # Process with improved VAD
            # Split audio into frames if needed
            frame_size_bytes = self.frame_len * 2  # 2 bytes per int16 sample
            speech_detected = False
            
            for i in range(0, len(audio_data), frame_size_bytes):
                frame = audio_data[i:i + frame_size_bytes]
                if len(frame) == frame_size_bytes:
                    speech_detected = self.process_frame(frame)
            
            # Update timing for compatibility
            if self.is_speaking and self.speech_start is None:
                self.speech_start = current_time
            elif not self.is_speaking:
                self.speech_start = None
                if self.silence_start is None:
                    self.silence_start = current_time
            else:
                self.silence_start = None
            
            return {
                "is_speaking": self.is_speaking,
                "energy": energy,
                "average_energy": sum(self.energy_history) / len(self.energy_history),
                "speech_detected": speech_detected,
                "timestamp": current_time
            }
            
        except Exception as e:
            return {
                "is_speaking": False,
                "energy": 0,
                "average_energy": 0,
                "speech_detected": False,
                "timestamp": time.time()
            }

    def _calculate_energy(self, audio_data: bytes) -> float:
        """Calculate energy level of audio data (compatibility method)"""
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
                return 0.0
                
            return float(energy)
            
        except Exception:
            return 0.0