"""
Audio sample fixtures for testing.
Provides pre-generated audio samples for consistent testing.
"""

import numpy as np
from typing import Dict, Any
from tests.utils.audio_generator import AudioGenerator


class AudioSampleFixtures:
    """Pre-generated audio samples for testing."""
    
    def __init__(self):
        self._samples = {}
        self._generate_samples()
    
    def _generate_samples(self):
        """Generate all audio samples."""
        
        # Basic audio samples
        self._samples["silence_20ms"] = AudioGenerator.generate_silence(20)
        self._samples["silence_100ms"] = AudioGenerator.generate_silence(100)
        self._samples["silence_500ms"] = AudioGenerator.generate_silence(500)
        
        # Speech-like samples
        self._samples["speech_20ms"] = AudioGenerator.generate_speech_like(20)
        self._samples["speech_100ms"] = AudioGenerator.generate_speech_like(100)
        self._samples["speech_500ms"] = AudioGenerator.generate_speech_like(500)
        self._samples["speech_1000ms"] = AudioGenerator.generate_speech_like(1000)
        
        # Tone samples
        self._samples["tone_440hz_100ms"] = AudioGenerator.generate_sine_wave(440, 100)
        self._samples["tone_1000hz_100ms"] = AudioGenerator.generate_sine_wave(1000, 100)
        self._samples["tone_low_200hz"] = AudioGenerator.generate_sine_wave(200, 200)
        self._samples["tone_high_3000hz"] = AudioGenerator.generate_sine_wave(3000, 200)
        
        # Noise samples
        self._samples["white_noise_100ms"] = AudioGenerator.generate_white_noise(100)
        self._samples["quiet_noise"] = AudioGenerator.generate_white_noise(200, amplitude=0.05)
        self._samples["loud_noise"] = AudioGenerator.generate_white_noise(200, amplitude=0.3)
        
        # DTMF samples
        for digit in ['1', '2', '5', '9', '*', '#']:
            self._samples[f"dtmf_{digit}"] = AudioGenerator.generate_dtmf_tone(digit, 100)
        
        # Volume variations
        self._samples["quiet_speech"] = AudioGenerator.generate_speech_like(300)
        # Reduce volume
        quiet_samples = np.frombuffer(self._samples["quiet_speech"], dtype=np.int16)
        quiet_samples = (quiet_samples * 0.1).astype(np.int16)
        self._samples["quiet_speech"] = quiet_samples.tobytes()
        
        self._samples["loud_speech"] = AudioGenerator.generate_speech_like(300)
        # Increase volume
        loud_samples = np.frombuffer(self._samples["loud_speech"], dtype=np.int16)
        loud_samples = np.clip(loud_samples * 3, -32768, 32767).astype(np.int16)
        self._samples["loud_speech"] = loud_samples.tobytes()
        
        # Mixed audio
        speech = AudioGenerator.generate_speech_like(500)
        noise = AudioGenerator.generate_white_noise(500, amplitude=0.1)
        self._samples["speech_with_noise"] = AudioGenerator.mix_audio(speech, noise, 0.8, 0.2)
        
        # Varying amplitude
        self._samples["varying_amplitude"] = AudioGenerator.generate_varying_amplitude(1000)
        
        # Conversation patterns
        from tests.utils.audio_generator import AudioTestPatterns
        self._samples["conversation_pattern"] = AudioTestPatterns.speech_with_silence()
        self._samples["interruption_pattern"] = AudioTestPatterns.interrupted_speech()
        self._samples["volume_pattern"] = AudioTestPatterns.varying_volume_speech()
        self._samples["dtmf_sequence"] = AudioTestPatterns.dtmf_sequence()
        self._samples["noisy_speech"] = AudioTestPatterns.noise_with_speech()
    
    def get_sample(self, name: str) -> bytes:
        """Get audio sample by name."""
        if name not in self._samples:
            raise ValueError(f"Audio sample '{name}' not found. Available: {list(self._samples.keys())}")
        return self._samples[name]
    
    def get_all_samples(self) -> Dict[str, bytes]:
        """Get all audio samples."""
        return self._samples.copy()
    
    def get_sample_info(self, name: str) -> Dict[str, Any]:
        """Get information about an audio sample."""
        if name not in self._samples:
            raise ValueError(f"Audio sample '{name}' not found")
        
        audio_data = self._samples[name]
        sample_count = len(audio_data) // 2  # 16-bit samples
        duration_ms = (sample_count / 16000) * 1000  # 16kHz sample rate
        energy = AudioGenerator.calculate_rms_energy(audio_data)
        
        return {
            "name": name,
            "size_bytes": len(audio_data),
            "sample_count": sample_count,
            "duration_ms": duration_ms,
            "energy": energy,
            "is_silence": AudioGenerator.detect_silence(audio_data)
        }
    
    def list_samples(self) -> list:
        """List all available sample names."""
        return list(self._samples.keys())
    
    def get_samples_by_category(self, category: str) -> Dict[str, bytes]:
        """Get samples by category."""
        categories = {
            "silence": [name for name in self._samples.keys() if "silence" in name],
            "speech": [name for name in self._samples.keys() if "speech" in name],
            "tone": [name for name in self._samples.keys() if "tone" in name],
            "noise": [name for name in self._samples.keys() if "noise" in name],
            "dtmf": [name for name in self._samples.keys() if "dtmf" in name],
            "pattern": [name for name in self._samples.keys() if "pattern" in name],
            "mixed": [name for name in self._samples.keys() if any(x in name for x in ["with", "varying", "mix"])]
        }
        
        if category not in categories:
            raise ValueError(f"Category '{category}' not found. Available: {list(categories.keys())}")
        
        return {name: self._samples[name] for name in categories[category]}


# Global instance
audio_fixtures = AudioSampleFixtures()


def get_audio_sample(name: str) -> bytes:
    """Get audio sample by name (convenience function)."""
    return audio_fixtures.get_sample(name)


def get_audio_samples_by_category(category: str) -> Dict[str, bytes]:
    """Get audio samples by category (convenience function)."""
    return audio_fixtures.get_samples_by_category(category)