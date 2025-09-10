"""
Test cases for Advanced Audio Processor.
Tests audio resampling, normalization, and silence detection.
"""

import pytest
import numpy as np
import struct
from unittest.mock import patch, MagicMock

from src.voice_assistant.audio.advanced_audio_processor import (
    AdvancedAudioProcessor, AudioStats, audio_processor,
    TARGET_RMS, SILENCE_THRESHOLD, NORMALIZATION_FACTOR
)


class TestAdvancedAudioProcessor:
    """Test cases for AdvancedAudioProcessor"""
    
    def setup_method(self):
        """Setup for each test"""
        self.processor = AdvancedAudioProcessor()
    
    def test_initialization(self):
        """Test processor initialization"""
        assert isinstance(self.processor.stats, AudioStats)
        assert self.processor.stats.samples_processed == 0
        assert len(self.processor._rms_history) == 0
        assert self.processor._max_history_size == 100
    
    def test_resample_pcm_24khz_to_16khz(self):
        """Test audio resampling from 24kHz to 16kHz"""
        # Create test audio data (24kHz, 16-bit, 1 second)
        sample_rate_24k = 24000
        duration = 1.0
        frequency = 440  # A4 note
        
        # Generate sine wave
        t = np.linspace(0, duration, int(sample_rate_24k * duration), False)
        audio_24k = np.sin(2 * np.pi * frequency * t) * 16000
        audio_24k = audio_24k.astype(np.int16)
        
        # Convert to bytes
        audio_bytes_24k = audio_24k.tobytes()
        
        # Resample to 16kHz
        resampled_bytes = self.processor.resample_pcm_24khz_to_16khz(audio_bytes_24k)
        
        # Convert back to numpy array
        resampled_audio = np.frombuffer(resampled_bytes, dtype=np.int16)
        
        # Check length (should be 2/3 of original)
        expected_length = int(len(audio_24k) * 16000 / 24000)
        assert abs(len(resampled_audio) - expected_length) <= 1  # Allow for rounding
        
        # Check statistics updated
        assert self.processor.stats.resampling_operations == 1
        assert self.processor.stats.samples_processed == len(audio_24k)
        assert self.processor.stats.total_processing_time > 0
    
    def test_resample_empty_data(self):
        """Test resampling with empty data"""
        empty_data = b''
        result = self.processor.resample_pcm_24khz_to_16khz(empty_data)
        assert result == empty_data
        assert self.processor.stats.resampling_operations == 1
        assert self.processor.stats.samples_processed == 0  # No samples in empty data
    
    def test_normalize_audio(self):
        """Test audio normalization"""
        # Create test audio with known RMS
        audio_data = np.array([1000, -1000, 2000, -2000] * 100, dtype=np.int16)
        audio_bytes = audio_data.tobytes()
        
        # Calculate expected RMS
        expected_rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
        
        # Normalize audio
        normalized_bytes, actual_rms = self.processor.normalize_audio(audio_bytes, TARGET_RMS)
        
        # Check RMS calculation
        assert abs(actual_rms - expected_rms) < 1.0
        
        # Check normalization
        normalized_audio = np.frombuffer(normalized_bytes, dtype=np.int16)
        normalized_rms = np.sqrt(np.mean(normalized_audio.astype(np.float32) ** 2))
        
        # Should be close to target RMS
        assert abs(normalized_rms - TARGET_RMS * NORMALIZATION_FACTOR) < TARGET_RMS * 0.1
        
        # Check statistics
        assert self.processor.stats.normalization_operations == 1
        assert len(self.processor._rms_history) == 1
    
    def test_normalize_silent_audio(self):
        """Test normalization with silent audio"""
        silent_audio = np.zeros(1000, dtype=np.int16)
        silent_bytes = silent_audio.tobytes()
        
        normalized_bytes, rms = self.processor.normalize_audio(silent_bytes)
        
        assert rms == 0.0
        assert normalized_bytes == silent_bytes
    
    def test_quick_silence_check(self):
        """Test silence detection"""
        # Create silent audio
        silent_audio = np.zeros(1000, dtype=np.int16)
        silent_bytes = silent_audio.tobytes()
        
        # Create loud audio
        loud_audio = np.array([5000, -5000] * 500, dtype=np.int16)
        loud_bytes = loud_audio.tobytes()
        
        # Test silence detection
        assert self.processor.quick_silence_check(silent_bytes) == True
        assert self.processor.quick_silence_check(loud_bytes) == False
        
        # Check statistics
        assert self.processor.stats.silence_detections == 1
    
    def test_quick_silence_check_custom_threshold(self):
        """Test silence detection with custom threshold"""
        # Create medium volume audio
        medium_audio = np.array([200, -200] * 500, dtype=np.int16)
        medium_bytes = medium_audio.tobytes()
        
        # Test with different thresholds
        assert self.processor.quick_silence_check(medium_bytes, threshold=100) == False
        assert self.processor.quick_silence_check(medium_bytes, threshold=500) == True
    
    def test_analyze_audio_quality(self):
        """Test audio quality analysis"""
        # Create test audio with known characteristics
        audio_data = np.array([1000, -1000, 2000, -2000, 3000, -3000] * 100, dtype=np.int16)
        audio_bytes = audio_data.tobytes()
        
        quality_metrics = self.processor.analyze_audio_quality(audio_bytes)
        
        # Check required metrics
        assert "rms" in quality_metrics
        assert "peak" in quality_metrics
        assert "dynamic_range" in quality_metrics
        assert "snr_estimate" in quality_metrics
        assert "clipping_percentage" in quality_metrics
        assert "sample_count" in quality_metrics
        assert "is_silent" in quality_metrics
        assert "quality_score" in quality_metrics
        
        # Check values
        assert quality_metrics["sample_count"] == len(audio_data)
        assert quality_metrics["peak"] == 3000
        assert quality_metrics["is_silent"] == False
        assert 0 <= quality_metrics["quality_score"] <= 100
    
    def test_analyze_empty_audio(self):
        """Test audio quality analysis with empty data"""
        empty_bytes = b''
        quality_metrics = self.processor.analyze_audio_quality(empty_bytes)
        
        assert "error" in quality_metrics
        assert quality_metrics["error"] == "Empty audio data"
    
    def test_apply_noise_gate(self):
        """Test noise gate application"""
        # Create audio with noise and signal
        noise = np.random.randint(-50, 50, 1000, dtype=np.int16)  # Low level noise
        signal = np.array([2000, -2000] * 500, dtype=np.int16)    # High level signal
        
        # Combine noise and signal
        combined = np.concatenate([noise, signal])
        combined_bytes = combined.tobytes()
        
        # Apply noise gate
        gated_bytes = self.processor.apply_noise_gate(combined_bytes, threshold=100, ratio=0.1)
        gated_audio = np.frombuffer(gated_bytes, dtype=np.int16)
        
        # Check that noise is reduced but signal is preserved
        noise_section = gated_audio[:1000]
        signal_section = gated_audio[1000:]
        
        # Noise should be reduced
        assert np.max(np.abs(noise_section)) < np.max(np.abs(noise))
        
        # Signal should be mostly preserved
        assert np.max(np.abs(signal_section)) > 1000
    
    def test_get_audio_stats(self):
        """Test audio statistics retrieval"""
        # Perform some operations
        test_audio = np.array([1000, -1000] * 100, dtype=np.int16).tobytes()
        
        self.processor.resample_pcm_24khz_to_16khz(test_audio)
        self.processor.normalize_audio(test_audio)
        self.processor.quick_silence_check(test_audio)
        
        stats = self.processor.get_audio_stats()
        
        # Check all required fields
        assert "samples_processed" in stats
        assert "resampling_operations" in stats
        assert "normalization_operations" in stats
        assert "silence_detections" in stats
        assert "total_processing_time" in stats
        assert "average_rms" in stats
        assert "peak_amplitude" in stats
        
        # Check values
        assert stats["resampling_operations"] == 1
        assert stats["normalization_operations"] == 1
        assert stats["silence_detections"] == 0  # Test audio is not silent
        assert stats["total_processing_time"] > 0
    
    def test_reset_stats(self):
        """Test statistics reset"""
        # Perform some operations
        test_audio = np.array([1000, -1000] * 100, dtype=np.int16).tobytes()
        self.processor.normalize_audio(test_audio)
        
        # Check stats are not zero
        assert self.processor.stats.normalization_operations > 0
        assert len(self.processor._rms_history) > 0
        
        # Reset stats
        self.processor.reset_stats()
        
        # Check stats are reset
        assert self.processor.stats.normalization_operations == 0
        assert len(self.processor._rms_history) == 0
    
    def test_rms_history_management(self):
        """Test RMS history size management"""
        # Add more than max history size
        test_audio = np.array([1000, -1000] * 100, dtype=np.int16).tobytes()
        
        for i in range(150):  # More than max_history_size (100)
            self.processor.normalize_audio(test_audio)
        
        # Check history size is limited
        assert len(self.processor._rms_history) <= self.processor._max_history_size
        assert len(self.processor._rms_history) == 100
    
    def test_global_instance(self):
        """Test global audio processor instance"""
        assert audio_processor is not None
        assert isinstance(audio_processor, AdvancedAudioProcessor)
    
    @patch('src.voice_assistant.audio.advanced_audio_processor.signal.resample')
    def test_resample_error_handling(self, mock_resample):
        """Test error handling in resampling"""
        mock_resample.side_effect = Exception("Resampling error")
        
        test_audio = np.array([1000, -1000] * 100, dtype=np.int16).tobytes()
        result = self.processor.resample_pcm_24khz_to_16khz(test_audio)
        
        # Should return original data on error
        assert result == test_audio
    
    @patch('src.voice_assistant.audio.advanced_audio_processor.audioop.rms')
    def test_silence_check_error_handling(self, mock_rms):
        """Test error handling in silence detection"""
        mock_rms.side_effect = Exception("RMS calculation error")
        
        test_audio = np.array([1000, -1000] * 100, dtype=np.int16).tobytes()
        result = self.processor.quick_silence_check(test_audio)
        
        # Should return False on error
        assert result == False


@pytest.mark.integration
class TestAdvancedAudioProcessorIntegration:
    """Integration tests for audio processor"""
    
    def test_full_audio_pipeline(self):
        """Test complete audio processing pipeline"""
        processor = AdvancedAudioProcessor()
        
        # Create test audio (24kHz)
        sample_rate = 24000
        duration = 0.5  # 500ms
        frequency = 440
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio_24k = np.sin(2 * np.pi * frequency * t) * 8000
        audio_24k = audio_24k.astype(np.int16)
        audio_bytes_24k = audio_24k.tobytes()
        
        # Step 1: Resample to 16kHz
        audio_16k = processor.resample_pcm_24khz_to_16khz(audio_bytes_24k)
        
        # Step 2: Normalize audio
        normalized_audio, rms = processor.normalize_audio(audio_16k)
        
        # Step 3: Check if silent
        is_silent = processor.quick_silence_check(normalized_audio)
        
        # Step 4: Apply noise gate
        gated_audio = processor.apply_noise_gate(normalized_audio)
        
        # Step 5: Analyze quality
        quality = processor.analyze_audio_quality(gated_audio)
        
        # Verify pipeline results
        assert len(audio_16k) < len(audio_bytes_24k)  # Resampled is shorter
        assert rms > 0  # Audio has signal
        assert is_silent == False  # Audio is not silent
        assert quality["sample_count"] > 0  # Quality analysis worked
        
        # Check statistics
        stats = processor.get_audio_stats()
        assert stats["resampling_operations"] == 1
        assert stats["normalization_operations"] == 1
        assert stats["silence_detections"] == 0


if __name__ == "__main__":
    pytest.main([__file__])