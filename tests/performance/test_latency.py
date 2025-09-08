"""
Performance tests for latency measurements.
Tests real-time processing latency requirements.
"""

import pytest
import asyncio
import time
import statistics
from typing import List

from src.voice_assistant.audio.realtime_audio_processor import RealTimeAudioProcessor, AudioConfig
from src.voice_assistant.ai.gemini_live_client import GeminiLiveClient, GeminiLiveConfig
from src.voice_assistant.core.session_manager import SessionManager, CallDirection
from tests.utils.audio_generator import AudioGenerator
from tests.utils.test_helpers import PerformanceMonitor


@pytest.mark.performance
class TestAudioProcessingLatency:
    """Test audio processing latency requirements."""
    
    @pytest.mark.asyncio
    async def test_single_chunk_processing_latency(self, audio_config, performance_thresholds):
        """Test latency for processing a single audio chunk."""
        processor = RealTimeAudioProcessor(audio_config)
        
        # Generate test audio (20ms chunk)
        test_audio = AudioGenerator.generate_speech_like(20)
        
        # Measure processing latency
        latencies = []
        
        for _ in range(100):  # Test 100 iterations
            start_time = time.perf_counter()
            
            result = await processor.process_input_audio(test_audio)
            
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)
            
            assert result["status"] == "processed"
        
        # Calculate statistics
        avg_latency = statistics.mean(latencies)
        max_latency = max(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
        
        # Verify latency requirements
        threshold = performance_thresholds["audio_processing_latency_ms"]
        assert avg_latency < threshold, f"Average latency {avg_latency:.2f}ms exceeds threshold {threshold}ms"
        assert max_latency < threshold * 2, f"Max latency {max_latency:.2f}ms exceeds threshold {threshold * 2}ms"
        assert p95_latency < threshold * 1.5, f"P95 latency {p95_latency:.2f}ms exceeds threshold {threshold * 1.5}ms"
    
    @pytest.mark.asyncio
    async def test_continuous_processing_latency(self, audio_config, performance_thresholds):
        """Test latency under continuous processing load."""
        processor = RealTimeAudioProcessor(audio_config)
        await processor.start_processing()
        
        # Generate continuous audio stream
        chunk_count = 500  # 10 seconds of 20ms chunks
        latencies = []
        
        try:
            for i in range(chunk_count):
                test_audio = AudioGenerator.generate_speech_like(20)
                
                start_time = time.perf_counter()
                await processor.process_input_audio(test_audio)
                end_time = time.perf_counter()
                
                latency_ms = (end_time - start_time) * 1000
                latencies.append(latency_ms)
                
                # Simulate real-time processing (20ms intervals)
                await asyncio.sleep(0.02)
        
        finally:
            await processor.stop_processing()
        
        # Analyze latency distribution
        avg_latency = statistics.mean(latencies)
        std_latency = statistics.stdev(latencies)
        max_latency = max(latencies)
        
        threshold = performance_thresholds["audio_processing_latency_ms"]
        
        # Continuous processing should maintain low latency
        assert avg_latency < threshold
        assert std_latency < threshold / 2  # Low variance
        assert max_latency < threshold * 3  # Allow some spikes