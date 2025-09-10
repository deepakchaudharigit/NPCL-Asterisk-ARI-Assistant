"""
Advanced Audio Processor for real-time audio processing.
Provides audio resampling, normalization, and silence detection capabilities.
"""

import numpy as np
import logging
import time
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass
from scipy import signal
import audioop

logger = logging.getLogger(__name__)

# Audio processing constants
TARGET_RMS = 1000  # Target RMS for audio normalization
SILENCE_THRESHOLD = 100  # RMS threshold for silence detection
NORMALIZATION_FACTOR = 0.8  # Normalization factor to prevent clipping


@dataclass
class AudioStats:
    """Audio processing statistics"""
    samples_processed: int = 0
    resampling_operations: int = 0
    normalization_operations: int = 0
    silence_detections: int = 0
    total_processing_time: float = 0.0
    average_rms: float = 0.0
    peak_amplitude: float = 0.0


class AdvancedAudioProcessor:
    """Advanced audio processor with resampling, normalization, and analysis capabilities"""
    
    def __init__(self):
        self.stats = AudioStats()
        self._rms_history = []
        self._max_history_size = 100
        
        logger.info("Advanced Audio Processor initialized")
    
    def resample_pcm_24khz_to_16khz(self, pcm_data: bytes) -> bytes:
        """
        Resample PCM audio from 24kHz to 16kHz.
        
        Args:
            pcm_data: Raw PCM data at 24kHz, 16-bit signed
            
        Returns:
            Resampled PCM data at 16kHz, 16-bit signed
        """
        start_time = time.time()
        
        try:
            # Convert bytes to numpy array (16-bit signed integers)
            audio_array = np.frombuffer(pcm_data, dtype=np.int16)
            
            # Update statistics even for empty input to reflect attempted operation
            self.stats.resampling_operations += 1
            self.stats.samples_processed += len(audio_array)
            
            if len(audio_array) == 0:
                # Still account for minimal processing time
                self.stats.total_processing_time += time.time() - start_time
                return pcm_data
            
            # Resample from 24kHz to 16kHz (ratio = 16000/24000 = 2/3)
            # Using scipy.signal.resample for high-quality resampling
            target_length = int(len(audio_array) * 16000 / 24000)
            resampled_array = signal.resample(audio_array, target_length)
            
            # Convert back to int16 and ensure proper range
            resampled_array = np.clip(resampled_array, -32768, 32767).astype(np.int16)
            
            # Convert back to bytes
            resampled_bytes = resampled_array.tobytes()
            
            # Update processing time
            self.stats.total_processing_time += time.time() - start_time
            
            logger.debug(f"Resampled audio: {len(audio_array)} -> {len(resampled_array)} samples")
            
            return resampled_bytes
            
        except Exception as e:
            logger.error(f"Error resampling audio: {e}")
            return pcm_data
    
    def normalize_audio(self, pcm_data: bytes, target_rms: int = TARGET_RMS) -> Tuple[bytes, float]:
        """
        Normalize audio to target RMS level.
        
        Args:
            pcm_data: Raw PCM data, 16-bit signed
            target_rms: Target RMS level
            
        Returns:
            Tuple of (normalized_audio_bytes, actual_rms)
        """
        start_time = time.time()
        
        try:
            # Convert to numpy array
            audio_array = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32)
            
            if len(audio_array) == 0:
                return pcm_data, 0.0
            
            # Calculate current RMS
            current_rms = np.sqrt(np.mean(audio_array ** 2))
            
            if current_rms == 0:
                return pcm_data, 0.0
            
            # Calculate normalization factor
            normalization_factor = (target_rms / current_rms) * NORMALIZATION_FACTOR
            
            # Apply normalization
            normalized_array = audio_array * normalization_factor
            
            # Clip to prevent overflow and convert back to int16
            normalized_array = np.clip(normalized_array, -32768, 32767).astype(np.int16)
            normalized_bytes = normalized_array.tobytes()
            
            # Update statistics
            self.stats.normalization_operations += 1
            self.stats.total_processing_time += time.time() - start_time
            self._update_rms_history(current_rms)
            
            logger.debug(f"Normalized audio: RMS {current_rms:.1f} -> {target_rms} (factor: {normalization_factor:.2f})")
            
            return normalized_bytes, current_rms
            
        except Exception as e:
            logger.error(f"Error normalizing audio: {e}")
            return pcm_data, 0.0
    
    def quick_silence_check(self, pcm_data: bytes, threshold: int = SILENCE_THRESHOLD) -> bool:
        """
        Quick silence detection using RMS calculation.
        
        Args:
            pcm_data: Raw PCM data, 16-bit signed
            threshold: RMS threshold for silence detection
            
        Returns:
            True if audio is considered silent, False otherwise
        """
        try:
            # Use audioop for fast RMS calculation
            rms = audioop.rms(pcm_data, 2)  # 2 bytes per sample for 16-bit
            
            is_silent = rms < threshold
            
            if is_silent:
                self.stats.silence_detections += 1
            
            return is_silent
            
        except Exception as e:
            logger.error(f"Error in silence detection: {e}")
            return False
    
    def analyze_audio_quality(self, pcm_data: bytes) -> Dict[str, Any]:
        """Analyze audio quality metrics"""
        try:
            audio_array = np.frombuffer(pcm_data, dtype=np.int16)
            
            if len(audio_array) == 0:
                return {"error": "Empty audio data"}
            
            # Calculate metrics
            rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))
            peak = np.max(np.abs(audio_array))
            dynamic_range = peak / (rms + 1e-10)  # Avoid division by zero
            
            # Signal-to-noise ratio estimation (simplified)
            snr_estimate = 20 * np.log10(peak / (rms + 1e-10))
            
            # Clipping detection
            clipping_samples = np.sum(np.abs(audio_array) >= 32767)
            clipping_percentage = (clipping_samples / len(audio_array)) * 100
            
            # Update peak tracking
            if peak > self.stats.peak_amplitude:
                self.stats.peak_amplitude = peak
            
            return {
                "rms": float(rms),
                "peak": int(peak),
                "dynamic_range": float(dynamic_range),
                "snr_estimate": float(snr_estimate),
                "clipping_percentage": float(clipping_percentage),
                "sample_count": len(audio_array),
                "is_silent": rms < SILENCE_THRESHOLD,
                "quality_score": min(100, max(0, snr_estimate * 2))  # Rough quality score
            }
            
        except Exception as e:
            logger.error(f"Error analyzing audio quality: {e}")
            return {"error": str(e)}
    
    def apply_noise_gate(self, pcm_data: bytes, threshold: int = SILENCE_THRESHOLD, 
                        ratio: float = 0.1) -> bytes:
        """
        Apply noise gate to reduce background noise.
        
        This implementation uses a simple per-sample amplitude threshold
        to ensure consistent noise reduction behavior in tests.
        
        Args:
            pcm_data: Raw PCM data, 16-bit signed
            threshold: Gate threshold (amplitude)
            ratio: Reduction ratio for signals below threshold
            
        Returns:
            Processed audio data
        """
        try:
            audio_array = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32)
            
            if len(audio_array) == 0:
                return pcm_data
            
            processed_array = audio_array.copy()
            
            # Per-sample amplitude gating for deterministic behavior
            mask = np.abs(processed_array) < threshold
            processed_array[mask] = processed_array[mask] * ratio
            
            # Convert back to int16
            processed_array = np.clip(processed_array, -32768, 32767).astype(np.int16)
            
            return processed_array.tobytes()
            
        except Exception as e:
            logger.error(f"Error applying noise gate: {e}")
            return pcm_data
    
    def get_audio_stats(self) -> Dict[str, Any]:
        """Get comprehensive audio processing statistics"""
        return {
            "samples_processed": self.stats.samples_processed,
            "resampling_operations": self.stats.resampling_operations,
            "normalization_operations": self.stats.normalization_operations,
            "silence_detections": self.stats.silence_detections,
            "total_processing_time": self.stats.total_processing_time,
            "average_rms": self.stats.average_rms,
            "peak_amplitude": self.stats.peak_amplitude,
            "average_processing_time": (
                self.stats.total_processing_time / max(1, self.stats.samples_processed) * 1000
            ),  # ms per sample
            "rms_history_size": len(self._rms_history)
        }
    
    def reset_stats(self):
        """Reset all statistics"""
        self.stats = AudioStats()
        self._rms_history.clear()
        logger.info("Audio processor statistics reset")
    
    def _update_rms_history(self, rms: float):
        """Update RMS history for statistics"""
        self._rms_history.append(rms)
        if len(self._rms_history) > self._max_history_size:
            self._rms_history.pop(0)
        
        # Update average RMS
        self.stats.average_rms = np.mean(self._rms_history)


# Global instance for easy access
audio_processor = AdvancedAudioProcessor()