"""
Audio test data generator for creating various audio samples.
"""

import numpy as np
import struct
import wave
import io
from typing import Tuple, Optional
from pathlib import Path


class AudioGenerator:
    """Generate audio test data in various formats."""
    
    @staticmethod
    def generate_sine_wave(
        frequency: float = 440.0,
        duration_ms: int = 20,
        sample_rate: int = 16000,
        amplitude: float = 0.5
    ) -> bytes:
        """Generate a sine wave audio sample."""
        duration_s = duration_ms / 1000.0
        samples = int(sample_rate * duration_s)
        
        t = np.linspace(0, duration_s, samples, False)
        wave_data = amplitude * np.sin(2 * np.pi * frequency * t)
        
        # Convert to 16-bit signed integers
        audio_data = (wave_data * 32767).astype(np.int16)
        return audio_data.tobytes()
    
    @staticmethod
    def generate_silence(duration_ms: int = 20, sample_rate: int = 16000) -> bytes:
        """Generate silence audio sample."""
        samples = int(sample_rate * duration_ms / 1000.0)
        return b'\x00' * (samples * 2)  # 2 bytes per 16-bit sample
    
    @staticmethod
    def generate_white_noise(
        duration_ms: int = 20,
        sample_rate: int = 16000,
        amplitude: float = 0.1
    ) -> bytes:
        """Generate white noise audio sample."""
        samples = int(sample_rate * duration_ms / 1000.0)
        noise = np.random.normal(0, amplitude, samples)
        audio_data = (noise * 32767).astype(np.int16)
        return audio_data.tobytes()
    
    @staticmethod
    def generate_speech_like(
        duration_ms: int = 1000,
        sample_rate: int = 16000
    ) -> bytes:
        """Generate speech-like audio with varying frequencies."""
        duration_s = duration_ms / 1000.0
        samples = int(sample_rate * duration_s)
        
        t = np.linspace(0, duration_s, samples, False)
        
        # Mix multiple frequencies to simulate speech with very high amplitudes
        frequencies = [200, 400, 800, 1600]  # Typical speech formants
        amplitudes = [0.6, 0.5, 0.4, 0.35]  # Very high amplitudes for reliable detection
        
        wave_data = np.zeros(samples)
        for freq, amp in zip(frequencies, amplitudes):
            wave_data += amp * np.sin(2 * np.pi * freq * t)
        
        # Add some envelope to make it more speech-like (very minimal decay)
        envelope = np.exp(-t * 0.1) * (1 + 0.1 * np.sin(2 * np.pi * 1.5 * t))
        wave_data *= envelope
        
        # Add some noise
        noise = np.random.normal(0, 0.02, samples)
        wave_data += noise
        
        # Ensure high amplitude for detection
        wave_data = np.clip(wave_data, -0.9, 0.9)  # Use more of the range
        
        # Convert to 16-bit with maximum scaling for detection
        audio_data = (wave_data * 32767 * 0.95).astype(np.int16)  # Scale to 95% of max
        return audio_data.tobytes()
    
    @staticmethod
    def generate_dtmf_tone(
        digit: str,
        duration_ms: int = 100,
        sample_rate: int = 16000
    ) -> bytes:
        """Generate DTMF tone for a digit."""
        dtmf_freqs = {
            '1': (697, 1209), '2': (697, 1336), '3': (697, 1477),
            '4': (770, 1209), '5': (770, 1336), '6': (770, 1477),
            '7': (852, 1209), '8': (852, 1336), '9': (852, 1477),
            '*': (941, 1209), '0': (941, 1336), '#': (941, 1477)
        }
        
        if digit not in dtmf_freqs:
            raise ValueError(f"Invalid DTMF digit: {digit}")
        
        freq1, freq2 = dtmf_freqs[digit]
        duration_s = duration_ms / 1000.0
        samples = int(sample_rate * duration_s)
        
        t = np.linspace(0, duration_s, samples, False)
        wave_data = (
            0.5 * np.sin(2 * np.pi * freq1 * t) +
            0.5 * np.sin(2 * np.pi * freq2 * t)
        )
        
        audio_data = (wave_data * 32767).astype(np.int16)
        return audio_data.tobytes()
    
    @staticmethod
    def generate_varying_amplitude(
        duration_ms: int = 1000,
        sample_rate: int = 16000,
        base_frequency: float = 440.0
    ) -> bytes:
        """Generate audio with varying amplitude for VAD testing."""
        duration_s = duration_ms / 1000.0
        samples = int(sample_rate * duration_s)
        
        t = np.linspace(0, duration_s, samples, False)
        
        # Create amplitude envelope that varies over time
        amplitude_envelope = 0.1 + 0.4 * (1 + np.sin(2 * np.pi * 2 * t))
        
        # Generate base tone
        wave_data = amplitude_envelope * np.sin(2 * np.pi * base_frequency * t)
        
        audio_data = (wave_data * 32767).astype(np.int16)
        return audio_data.tobytes()
    
    @staticmethod
    def create_wav_file(
        audio_data: bytes,
        sample_rate: int = 16000,
        channels: int = 1,
        sample_width: int = 2
    ) -> bytes:
        """Create a WAV file from raw audio data."""
        buffer = io.BytesIO()
        
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data)
        
        return buffer.getvalue()
    
    @staticmethod
    def validate_audio_format(
        audio_data: bytes,
        expected_samples: int,
        sample_width: int = 2
    ) -> bool:
        """Validate audio data format."""
        expected_bytes = expected_samples * sample_width
        return len(audio_data) == expected_bytes
    
    @staticmethod
    def calculate_rms_energy(audio_data: bytes) -> float:
        """Calculate RMS energy of audio data."""
        if len(audio_data) == 0:
            return 0.0
        
        # Convert bytes to numpy array
        samples = np.frombuffer(audio_data, dtype=np.int16)
        
        # Calculate RMS
        rms = np.sqrt(np.mean(samples.astype(np.float32) ** 2))
        return float(rms)
    
    @staticmethod
    def detect_silence(
        audio_data: bytes,
        threshold: float = 100.0
    ) -> bool:
        """Detect if audio data contains silence."""
        energy = AudioGenerator.calculate_rms_energy(audio_data)
        return energy < threshold
    
    @staticmethod
    def mix_audio(
        audio1: bytes,
        audio2: bytes,
        ratio1: float = 0.5,
        ratio2: float = 0.5
    ) -> bytes:
        """Mix two audio samples."""
        # Ensure both audio samples are the same length
        min_len = min(len(audio1), len(audio2))
        audio1 = audio1[:min_len]
        audio2 = audio2[:min_len]
        
        # Convert to numpy arrays
        samples1 = np.frombuffer(audio1, dtype=np.int16).astype(np.float32)
        samples2 = np.frombuffer(audio2, dtype=np.int16).astype(np.float32)
        
        # Mix with specified ratios
        mixed = ratio1 * samples1 + ratio2 * samples2
        
        # Clip to prevent overflow
        mixed = np.clip(mixed, -32768, 32767)
        
        # Convert back to bytes
        return mixed.astype(np.int16).tobytes()


class AudioTestPatterns:
    """Predefined audio test patterns for common test scenarios."""
    
    @staticmethod
    def speech_with_silence() -> bytes:
        """Generate pattern: silence -> speech -> silence."""
        silence1 = AudioGenerator.generate_silence(500)  # 500ms silence
        speech = AudioGenerator.generate_speech_like(2000)  # 2s speech
        silence2 = AudioGenerator.generate_silence(500)  # 500ms silence
        
        return silence1 + speech + silence2
    
    @staticmethod
    def interrupted_speech() -> bytes:
        """Generate pattern for interruption testing."""
        speech1 = AudioGenerator.generate_speech_like(1000)  # 1s speech
        silence = AudioGenerator.generate_silence(200)  # 200ms silence
        speech2 = AudioGenerator.generate_speech_like(1000)  # 1s speech
        
        return speech1 + silence + speech2
    
    @staticmethod
    def varying_volume_speech() -> bytes:
        """Generate speech with varying volume levels."""
        patterns = []
        volumes = [0.1, 0.3, 0.5, 0.7, 0.9]
        
        for volume in volumes:
            speech = AudioGenerator.generate_speech_like(500)
            # Adjust volume
            samples = np.frombuffer(speech, dtype=np.int16).astype(np.float32)
            samples *= volume
            patterns.append(samples.astype(np.int16).tobytes())
        
        return b''.join(patterns)
    
    @staticmethod
    def dtmf_sequence() -> bytes:
        """Generate DTMF sequence for testing."""
        digits = ['1', '2', '3', '4', '5']
        patterns = []
        
        for digit in digits:
            dtmf = AudioGenerator.generate_dtmf_tone(digit, 200)
            silence = AudioGenerator.generate_silence(100)
            patterns.extend([dtmf, silence])
        
        return b''.join(patterns)
    
    @staticmethod
    def noise_with_speech() -> bytes:
        """Generate speech mixed with background noise."""
        speech = AudioGenerator.generate_speech_like(2000)
        noise = AudioGenerator.generate_white_noise(2000, amplitude=0.05)
        
        return AudioGenerator.mix_audio(speech, noise, 0.8, 0.2)