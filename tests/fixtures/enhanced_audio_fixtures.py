"""
Enhanced audio fixtures for comprehensive audio testing.
Extends the basic audio fixtures with more complex scenarios and edge cases.
"""

import pytest
import numpy as np
import base64
import io
import wave
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

from tests.utils.audio_generator import AudioGenerator, AudioTestPatterns


@dataclass
class AudioTestScenario:
    """Audio test scenario with expected outcomes."""
    name: str
    description: str
    audio_data: bytes
    expected_properties: Dict[str, Any] = field(default_factory=dict)
    test_parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationAudioFlow:
    """Audio flow for a complete conversation."""
    name: str
    description: str
    segments: List[Tuple[str, bytes]]  # (type, audio_data) pairs
    timing: List[float]  # Timing for each segment
    expected_outcomes: Dict[str, Any] = field(default_factory=dict)


class EnhancedAudioGenerator:
    """Enhanced audio generator with more complex scenarios."""
    
    @staticmethod
    def generate_realistic_speech(
        duration_ms: int = 2000,
        sample_rate: int = 16000,
        speaker_characteristics: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """Generate more realistic speech with speaker characteristics."""
        if speaker_characteristics is None:
            speaker_characteristics = {
                "fundamental_frequency": 150,  # Hz
                "formant_frequencies": [800, 1200, 2400],
                "voice_quality": "normal",
                "speaking_rate": "normal"
            }
        
        duration_s = duration_ms / 1000.0
        samples = int(sample_rate * duration_s)
        t = np.linspace(0, duration_s, samples, False)
        
        # Base fundamental frequency with natural variation
        f0 = speaker_characteristics["fundamental_frequency"]
        f0_variation = f0 * 0.1 * np.sin(2 * np.pi * 3 * t)  # 3 Hz variation
        
        # Generate harmonics
        signal = np.zeros(samples)
        for harmonic in range(1, 6):  # First 5 harmonics
            amplitude = 1.0 / harmonic  # Decreasing amplitude
            frequency = f0 + f0_variation * harmonic
            signal += amplitude * np.sin(2 * np.pi * frequency * t)
        
        # Add formants
        for formant_freq in speaker_characteristics["formant_frequencies"]:
            formant_signal = 0.3 * np.sin(2 * np.pi * formant_freq * t)
            # Apply formant envelope
            formant_envelope = np.exp(-((t - duration_s/2) ** 2) / (duration_s/4))
            signal += formant_signal * formant_envelope
        
        # Add natural speech envelope
        envelope = np.exp(-t * 0.5) * (1 + 0.5 * np.sin(2 * np.pi * 8 * t))
        signal *= envelope
        
        # Add breath noise
        breath_noise = 0.02 * np.random.normal(0, 1, samples)
        signal += breath_noise
        
        # Normalize and convert to 16-bit
        signal = np.clip(signal / np.max(np.abs(signal)) * 0.8, -1, 1)
        audio_data = (signal * 32767).astype(np.int16)
        return audio_data.tobytes()
    
    @staticmethod
    def generate_noisy_environment(
        clean_speech: bytes,
        noise_type: str = "office",
        snr_db: float = 10.0
    ) -> bytes:
        """Add realistic background noise to clean speech."""
        # Convert speech to numpy array
        speech_samples = np.frombuffer(clean_speech, dtype=np.int16).astype(np.float32)
        
        # Generate appropriate noise
        if noise_type == "office":
            # Office noise: keyboard, air conditioning, distant voices
            noise = (
                0.3 * np.random.normal(0, 1, len(speech_samples)) +  # White noise
                0.2 * np.sin(2 * np.pi * 60 * np.arange(len(speech_samples)) / 16000) +  # 60Hz hum
                0.1 * np.random.poisson(0.1, len(speech_samples))  # Keyboard clicks
            )
        elif noise_type == "street":
            # Street noise: traffic, wind
            noise = (
                0.5 * np.random.normal(0, 1, len(speech_samples)) +  # Wind
                0.3 * np.sin(2 * np.pi * 200 * np.arange(len(speech_samples)) / 16000)  # Traffic rumble
            )
        elif noise_type == "cafe":
            # Cafe noise: chatter, dishes, music
            noise = (
                0.4 * np.random.normal(0, 1, len(speech_samples)) +  # General chatter
                0.2 * np.sin(2 * np.pi * 440 * np.arange(len(speech_samples)) / 16000)  # Background music
            )
        else:
            # Default white noise
            noise = np.random.normal(0, 1, len(speech_samples))
        
        # Calculate noise power for desired SNR
        speech_power = np.mean(speech_samples ** 2)
        noise_power = np.mean(noise ** 2)
        noise_scaling = np.sqrt(speech_power / (noise_power * (10 ** (snr_db / 10))))
        
        # Mix speech and noise
        noisy_speech = speech_samples + noise * noise_scaling
        
        # Normalize and convert back to bytes
        noisy_speech = np.clip(noisy_speech, -32768, 32767)
        return noisy_speech.astype(np.int16).tobytes()
    
    @staticmethod
    def generate_echo_effect(
        original_audio: bytes,
        delay_ms: int = 200,
        decay_factor: float = 0.3
    ) -> bytes:
        """Add echo effect to audio."""
        samples = np.frombuffer(original_audio, dtype=np.int16).astype(np.float32)
        delay_samples = int(16000 * delay_ms / 1000)  # Assuming 16kHz
        
        # Create echo
        echoed = np.zeros(len(samples) + delay_samples)
        echoed[:len(samples)] = samples
        echoed[delay_samples:delay_samples + len(samples)] += samples * decay_factor
        
        # Normalize and convert back
        echoed = np.clip(echoed, -32768, 32767)
        return echoed[:len(samples)].astype(np.int16).tobytes()
    
    @staticmethod
    def generate_compression_artifacts(
        original_audio: bytes,
        compression_ratio: float = 0.1
    ) -> bytes:
        """Simulate audio compression artifacts."""
        samples = np.frombuffer(original_audio, dtype=np.int16).astype(np.float32)
        
        # Simulate quantization noise
        quantization_levels = int(65536 * compression_ratio)
        quantized = np.round(samples / 65536 * quantization_levels) * 65536 / quantization_levels
        
        # Add compression noise
        compression_noise = 0.05 * np.random.normal(0, 1, len(samples))
        compressed = quantized + compression_noise
        
        # Normalize and convert back
        compressed = np.clip(compressed, -32768, 32767)
        return compressed.astype(np.int16).tobytes()
    
    @staticmethod
    def generate_phone_quality_audio(original_audio: bytes) -> bytes:
        """Simulate phone quality audio (bandpass filtered)."""
        samples = np.frombuffer(original_audio, dtype=np.int16).astype(np.float32)
        
        # Simple bandpass filter simulation (300Hz - 3400Hz)
        # This is a simplified version - in practice, you'd use proper filtering
        fft = np.fft.fft(samples)
        freqs = np.fft.fftfreq(len(samples), 1/16000)
        
        # Zero out frequencies outside phone band
        mask = (np.abs(freqs) < 300) | (np.abs(freqs) > 3400)
        fft[mask] = 0
        
        # Convert back to time domain
        filtered = np.real(np.fft.ifft(fft))
        
        # Add some distortion
        filtered = np.tanh(filtered / 16384) * 16384
        
        # Normalize and convert back
        filtered = np.clip(filtered, -32768, 32767)
        return filtered.astype(np.int16).tobytes()


class ConversationAudioFlows:
    """Factory for creating conversation audio flows."""
    
    @staticmethod
    def create_natural_conversation() -> ConversationAudioFlow:
        """Create a natural conversation flow."""
        # Generate realistic speech segments
        user_speech_1 = EnhancedAudioGenerator.generate_realistic_speech(
            2000, speaker_characteristics={"fundamental_frequency": 180}  # Higher pitch
        )
        assistant_speech_1 = EnhancedAudioGenerator.generate_realistic_speech(
            2500, speaker_characteristics={"fundamental_frequency": 120}  # Lower pitch
        )
        user_speech_2 = EnhancedAudioGenerator.generate_realistic_speech(
            1500, speaker_characteristics={"fundamental_frequency": 180}
        )
        assistant_speech_2 = EnhancedAudioGenerator.generate_realistic_speech(
            3000, speaker_characteristics={"fundamental_frequency": 120}
        )
        
        return ConversationAudioFlow(
            name="natural_conversation",
            description="Natural conversation with realistic speech patterns",
            segments=[
                ("silence", AudioGenerator.generate_silence(500)),
                ("user_speech", user_speech_1),
                ("silence", AudioGenerator.generate_silence(300)),
                ("assistant_speech", assistant_speech_1),
                ("silence", AudioGenerator.generate_silence(200)),
                ("user_speech", user_speech_2),
                ("silence", AudioGenerator.generate_silence(400)),
                ("assistant_speech", assistant_speech_2),
                ("silence", AudioGenerator.generate_silence(500))
            ],
            timing=[0.0, 0.5, 2.5, 2.8, 5.3, 5.5, 7.0, 7.4, 10.4],
            expected_outcomes={
                "total_duration_ms": 11000,
                "speech_segments": 4,
                "silence_segments": 5,
                "turn_taking_detected": True
            }
        )
    
    @staticmethod
    def create_noisy_conversation() -> ConversationAudioFlow:
        """Create conversation in noisy environment."""
        clean_user_speech = EnhancedAudioGenerator.generate_realistic_speech(2000)
        clean_assistant_speech = EnhancedAudioGenerator.generate_realistic_speech(2500)
        
        # Add office noise
        noisy_user_speech = EnhancedAudioGenerator.generate_noisy_environment(
            clean_user_speech, "office", snr_db=5.0
        )
        noisy_assistant_speech = EnhancedAudioGenerator.generate_noisy_environment(
            clean_assistant_speech, "office", snr_db=8.0
        )
        
        return ConversationAudioFlow(
            name="noisy_conversation",
            description="Conversation in noisy office environment",
            segments=[
                ("background_noise", AudioGenerator.generate_white_noise(1000, amplitude=0.1)),
                ("user_speech_noisy", noisy_user_speech),
                ("background_noise", AudioGenerator.generate_white_noise(500, amplitude=0.1)),
                ("assistant_speech_noisy", noisy_assistant_speech),
                ("background_noise", AudioGenerator.generate_white_noise(1000, amplitude=0.1))
            ],
            timing=[0.0, 1.0, 3.0, 3.5, 6.0],
            expected_outcomes={
                "noise_detected": True,
                "speech_enhancement_needed": True,
                "snr_db": 6.5
            }
        )
    
    @staticmethod
    def create_phone_call_simulation() -> ConversationAudioFlow:
        """Create phone call quality conversation."""
        user_speech = EnhancedAudioGenerator.generate_realistic_speech(2000)
        assistant_speech = EnhancedAudioGenerator.generate_realistic_speech(2500)
        
        # Apply phone quality effects
        phone_user_speech = EnhancedAudioGenerator.generate_phone_quality_audio(user_speech)
        phone_assistant_speech = EnhancedAudioGenerator.generate_phone_quality_audio(assistant_speech)
        
        # Add compression artifacts
        compressed_user = EnhancedAudioGenerator.generate_compression_artifacts(
            phone_user_speech, compression_ratio=0.2
        )
        compressed_assistant = EnhancedAudioGenerator.generate_compression_artifacts(
            phone_assistant_speech, compression_ratio=0.2
        )
        
        return ConversationAudioFlow(
            name="phone_call_simulation",
            description="Phone call with compression and bandwidth limitations",
            segments=[
                ("dial_tone", AudioGenerator.generate_sine_wave(350, 1000)),
                ("silence", AudioGenerator.generate_silence(500)),
                ("user_speech_phone", compressed_user),
                ("silence", AudioGenerator.generate_silence(300)),
                ("assistant_speech_phone", compressed_assistant),
                ("silence", AudioGenerator.generate_silence(500))
            ],
            timing=[0.0, 1.0, 1.5, 3.5, 3.8, 6.3],
            expected_outcomes={
                "phone_quality_detected": True,
                "bandwidth_limited": True,
                "compression_artifacts": True
            }
        )
    
    @staticmethod
    def create_interruption_scenario() -> ConversationAudioFlow:
        """Create conversation with interruptions."""
        assistant_speech = EnhancedAudioGenerator.generate_realistic_speech(3000)
        user_interruption = EnhancedAudioGenerator.generate_realistic_speech(1000)
        assistant_continuation = EnhancedAudioGenerator.generate_realistic_speech(2000)
        
        return ConversationAudioFlow(
            name="interruption_scenario",
            description="Conversation with user interrupting assistant",
            segments=[
                ("assistant_speech_start", assistant_speech[:16000]),  # First 1 second
                ("user_interruption", user_interruption),
                ("silence", AudioGenerator.generate_silence(200)),
                ("assistant_continuation", assistant_continuation)
            ],
            timing=[0.0, 1.0, 2.0, 2.2],
            expected_outcomes={
                "interruption_detected": True,
                "context_switch": True,
                "graceful_handling": True
            }
        )


@pytest.fixture
def enhanced_audio_samples():
    """Enhanced audio samples with various characteristics."""
    return {
        # Realistic speech samples
        "male_speech": EnhancedAudioGenerator.generate_realistic_speech(
            2000, {"fundamental_frequency": 120, "voice_quality": "normal"}
        ),
        "female_speech": EnhancedAudioGenerator.generate_realistic_speech(
            2000, {"fundamental_frequency": 200, "voice_quality": "normal"}
        ),
        "child_speech": EnhancedAudioGenerator.generate_realistic_speech(
            1500, {"fundamental_frequency": 300, "voice_quality": "high"}
        ),
        
        # Noisy environments
        "office_noise_speech": EnhancedAudioGenerator.generate_noisy_environment(
            EnhancedAudioGenerator.generate_realistic_speech(2000), "office", 10.0
        ),
        "street_noise_speech": EnhancedAudioGenerator.generate_noisy_environment(
            EnhancedAudioGenerator.generate_realistic_speech(2000), "street", 5.0
        ),
        "cafe_noise_speech": EnhancedAudioGenerator.generate_noisy_environment(
            EnhancedAudioGenerator.generate_realistic_speech(2000), "cafe", 8.0
        ),
        
        # Audio quality variations
        "phone_quality": EnhancedAudioGenerator.generate_phone_quality_audio(
            EnhancedAudioGenerator.generate_realistic_speech(2000)
        ),
        "compressed_audio": EnhancedAudioGenerator.generate_compression_artifacts(
            EnhancedAudioGenerator.generate_realistic_speech(2000), 0.15
        ),
        "echo_audio": EnhancedAudioGenerator.generate_echo_effect(
            EnhancedAudioGenerator.generate_realistic_speech(2000), 150, 0.4
        ),
        
        # Edge cases
        "very_quiet_speech": (
            np.frombuffer(EnhancedAudioGenerator.generate_realistic_speech(1000), dtype=np.int16) * 0.1
        ).astype(np.int16).tobytes(),
        "very_loud_speech": np.clip(
            np.frombuffer(EnhancedAudioGenerator.generate_realistic_speech(1000), dtype=np.int16) * 3,
            -32768, 32767
        ).astype(np.int16).tobytes(),
        "clipped_audio": np.clip(
            np.frombuffer(EnhancedAudioGenerator.generate_realistic_speech(1000), dtype=np.int16) * 2,
            -16384, 16384
        ).astype(np.int16).tobytes()
    }


@pytest.fixture
def conversation_audio_flows():
    """Complete conversation audio flows."""
    return {
        "natural": ConversationAudioFlows.create_natural_conversation(),
        "noisy": ConversationAudioFlows.create_noisy_conversation(),
        "phone_call": ConversationAudioFlows.create_phone_call_simulation(),
        "interruption": ConversationAudioFlows.create_interruption_scenario()
    }


@pytest.fixture
def audio_test_scenarios():
    """Comprehensive audio test scenarios."""
    scenarios = []
    
    # Voice Activity Detection scenarios
    scenarios.append(AudioTestScenario(
        name="vad_speech_detection",
        description="Test voice activity detection with clear speech",
        audio_data=EnhancedAudioGenerator.generate_realistic_speech(2000),
        expected_properties={
            "contains_speech": True,
            "speech_duration_ms": 2000,
            "silence_duration_ms": 0,
            "energy_level": "medium"
        },
        test_parameters={
            "vad_threshold": 0.01,
            "min_speech_duration": 100
        }
    ))
    
    scenarios.append(AudioTestScenario(
        name="vad_silence_detection",
        description="Test voice activity detection with silence",
        audio_data=AudioGenerator.generate_silence(2000),
        expected_properties={
            "contains_speech": False,
            "speech_duration_ms": 0,
            "silence_duration_ms": 2000,
            "energy_level": "low"
        },
        test_parameters={
            "vad_threshold": 0.01,
            "min_silence_duration": 500
        }
    ))
    
    # Noise robustness scenarios
    scenarios.append(AudioTestScenario(
        name="noise_robustness_high_snr",
        description="Test noise robustness with high SNR",
        audio_data=EnhancedAudioGenerator.generate_noisy_environment(
            EnhancedAudioGenerator.generate_realistic_speech(2000), "office", 15.0
        ),
        expected_properties={
            "contains_speech": True,
            "snr_db": 15.0,
            "noise_type": "office",
            "speech_quality": "good"
        },
        test_parameters={
            "noise_reduction": True,
            "snr_threshold": 10.0
        }
    ))
    
    scenarios.append(AudioTestScenario(
        name="noise_robustness_low_snr",
        description="Test noise robustness with low SNR",
        audio_data=EnhancedAudioGenerator.generate_noisy_environment(
            EnhancedAudioGenerator.generate_realistic_speech(2000), "street", 0.0
        ),
        expected_properties={
            "contains_speech": True,
            "snr_db": 0.0,
            "noise_type": "street",
            "speech_quality": "poor"
        },
        test_parameters={
            "noise_reduction": True,
            "snr_threshold": 5.0,
            "enhancement_required": True
        }
    ))
    
    return scenarios


@pytest.fixture
def audio_quality_variations():
    """Different audio quality variations for testing."""
    base_speech = EnhancedAudioGenerator.generate_realistic_speech(2000)
    
    return {
        "original": base_speech,
        "phone_quality": EnhancedAudioGenerator.generate_phone_quality_audio(base_speech),
        "compressed_low": EnhancedAudioGenerator.generate_compression_artifacts(base_speech, 0.05),
        "compressed_high": EnhancedAudioGenerator.generate_compression_artifacts(base_speech, 0.3),
        "echo_short": EnhancedAudioGenerator.generate_echo_effect(base_speech, 100, 0.2),
        "echo_long": EnhancedAudioGenerator.generate_echo_effect(base_speech, 300, 0.5),
        "office_noise": EnhancedAudioGenerator.generate_noisy_environment(base_speech, "office", 10),
        "street_noise": EnhancedAudioGenerator.generate_noisy_environment(base_speech, "street", 5),
        "cafe_noise": EnhancedAudioGenerator.generate_noisy_environment(base_speech, "cafe", 8)
    }


@pytest.fixture
def audio_format_variations():
    """Audio samples in different formats and sample rates."""
    base_speech_16k = EnhancedAudioGenerator.generate_realistic_speech(1000)
    
    # Convert to different sample rates (simplified - in practice use proper resampling)
    speech_8k = base_speech_16k[::2]  # Downsample by 2
    speech_44k = np.repeat(
        np.frombuffer(base_speech_16k, dtype=np.int16), 2.75
    ).astype(np.int16).tobytes()[:int(len(base_speech_16k) * 2.75)]
    
    return {
        "16khz_16bit": base_speech_16k,
        "8khz_16bit": speech_8k,
        "44khz_16bit": speech_44k,
        "16khz_8bit": (
            np.frombuffer(base_speech_16k, dtype=np.int16) // 256
        ).astype(np.int8).tobytes(),
        "mono": base_speech_16k,
        "stereo": base_speech_16k + base_speech_16k  # Duplicate for stereo
    }


@pytest.fixture
def performance_audio_data():
    """Large audio datasets for performance testing."""
    return {
        "short_burst": EnhancedAudioGenerator.generate_realistic_speech(100),  # 100ms
        "medium_speech": EnhancedAudioGenerator.generate_realistic_speech(5000),  # 5s
        "long_speech": EnhancedAudioGenerator.generate_realistic_speech(30000),  # 30s
        "very_long_speech": EnhancedAudioGenerator.generate_realistic_speech(300000),  # 5 minutes
        "continuous_stream": b''.join([
            EnhancedAudioGenerator.generate_realistic_speech(1000) for _ in range(60)
        ])  # 1 minute of continuous speech
    }


@pytest.fixture
def audio_edge_cases():
    """Edge case audio samples for robustness testing."""
    return {
        "empty": b'',
        "single_sample": b'\x00\x01',
        "odd_length": b'\x00\x01\x02',  # Odd number of bytes
        "max_amplitude": b'\xff\x7f' * 160,  # Max positive amplitude
        "min_amplitude": b'\x00\x80' * 160,  # Max negative amplitude
        "alternating": b'\xff\x7f\x00\x80' * 80,  # Alternating max/min
        "dc_offset": (np.ones(320, dtype=np.int16) * 16384).tobytes(),
        "random_noise": np.random.randint(-32768, 32767, 320, dtype=np.int16).tobytes(),
        "sine_wave_pure": AudioGenerator.generate_sine_wave(1000, 1000, amplitude=1.0),
        "frequency_sweep": b''.join([
            AudioGenerator.generate_sine_wave(freq, 100) 
            for freq in range(100, 4000, 100)
        ])
    }