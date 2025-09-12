"""
Comprehensive test suite that validates all implemented features.
This is the main test file that ensures all components work together.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch

from src.voice_assistant.audio.realtime_audio_processor import RealTimeAudioProcessor, AudioConfig
from src.voice_assistant.ai.gemini_live_client import GeminiLiveClient, GeminiLiveConfig
from src.voice_assistant.core.session_manager import SessionManager, CallDirection, SessionState
from src.voice_assistant.telephony.external_media_handler import ExternalMediaHandler
from src.voice_assistant.telephony.realtime_ari_handler import RealTimeARIHandler, RealTimeARIConfig
from tests.utils.audio_generator import AudioGenerator, AudioTestPatterns
from tests.utils.test_helpers import EventCollector, PerformanceMonitor
from tests.mocks.mock_asterisk import MockAsteriskARIServer
from tests.mocks.mock_gemini import MockGeminiLiveAPI


@pytest.mark.e2e
class TestCompleteFeatureSet:
    """Test all implemented features working together."""
    
    @pytest.mark.asyncio
    async def test_complete_call_workflow(self, test_settings):
        """Test complete call workflow from start to finish."""
        # Setup all components
        session_manager = SessionManager()
        gemini_client = GeminiLiveClient(api_key="test-key")
        external_media_handler = ExternalMediaHandler(session_manager, gemini_client)
        
        # Mock external dependencies
        gemini_client.is_connected = True
        gemini_client.websocket = AsyncMock()
        gemini_client._send_event = AsyncMock()
        
        # Track events throughout the workflow
        events = EventCollector()
        events.start_collecting()
        
        try:
            # 1. Simulate incoming call
            session_id = await session_manager.create_session(
                channel_id="test-channel-123",
                caller_number="1234567890",
                called_number="1000",
                direction=CallDirection.INBOUND
            )
            events.add_event("call_started", {"session_id": session_id})
            
            # 2. Update session to active state
            await session_manager.update_session_state(session_id, SessionState.ACTIVE)
            events.add_event("session_active")
            
            # 3. Simulate audio input processing
            audio_processor = RealTimeAudioProcessor()
            await audio_processor.start_processing()
            
            # Process speech audio
            speech_audio = AudioGenerator.generate_speech_like(1000)  # 1 second
            result = await audio_processor.process_input_audio(speech_audio)
            events.add_event("audio_processed", result)
            
            # 4. Add conversation turn
            turn_id = await session_manager.add_conversation_turn(
                session_id=session_id,
                speaker="user",
                content_type="audio",
                content={"transcription": "Hello, how are you?"},
                duration=1.0,
                confidence=0.95
            )
            events.add_event("turn_added", {"turn_id": turn_id})
            
            # 5. Simulate Gemini response
            await gemini_client.send_audio_chunk(speech_audio)
            await gemini_client.commit_audio_buffer()
            await gemini_client.create_response()
            events.add_event("gemini_response_requested")
            
            # 6. Add assistant response turn
            response_turn_id = await session_manager.add_conversation_turn(
                session_id=session_id,
                speaker="assistant",
                content_type="audio",
                content={"text": "I'm doing great, thank you!"},
                duration=1.5
            )
            events.add_event("assistant_response", {"turn_id": response_turn_id})
            
            # 7. End the call
            await session_manager.end_session(session_id)
            events.add_event("call_ended")
            
            await audio_processor.stop_processing()
            
            # Verify complete workflow
            timeline = events.get_event_timeline()
            event_types = [event["type"] for event in timeline]
            
            expected_events = [
                "call_started", "session_active", "audio_processed", 
                "turn_added", "gemini_response_requested", 
                "assistant_response", "call_ended"
            ]
            
            for expected_event in expected_events:
                assert expected_event in event_types, f"Missing event: {expected_event}"
            
            # Verify session final state
            session = session_manager.get_session(session_id)
            assert session.state == SessionState.ENDED
            assert len(session.turns) == 2  # User + Assistant turns
            assert session.metrics.total_turns == 2
            assert session.metrics.user_turns == 1
            assert session.metrics.assistant_turns == 1
            
        finally:
            await session_manager.stop_cleanup_task()
    
    @pytest.mark.asyncio
    async def test_real_time_audio_pipeline(self, audio_config, gemini_config):
        """Test real-time audio processing pipeline."""
        # Setup components
        audio_processor = RealTimeAudioProcessor(audio_config)
        gemini_client = GeminiLiveClient(config=gemini_config)
        
        # Mock Gemini connection
        gemini_client.is_connected = True
        gemini_client.websocket = AsyncMock()
        gemini_client._send_event = AsyncMock()
        
        # Track pipeline performance
        monitor = PerformanceMonitor()
        monitor.start_monitoring()
        
        # Track audio flow
        audio_chunks_processed = []
        gemini_chunks_sent = []
        
        async def audio_pipeline(data):
            audio_data = data["audio_data"]
            audio_chunks_processed.append(len(audio_data))
            
            # Send to Gemini
            success = await gemini_client.send_audio_chunk(audio_data)
            if success:
                gemini_chunks_sent.append(len(audio_data))
        
        audio_processor.register_callback("audio_chunk", audio_pipeline)
        
        try:
            await audio_processor.start_processing()
            
            # Process real-time audio stream
            chunk_count = 100  # 2 seconds of 20ms chunks
            
            for i in range(chunk_count):
                # Generate varied audio content
                if i % 10 < 3:  # 30% silence
                    audio_chunk = AudioGenerator.generate_silence(20)
                elif i % 10 < 7:  # 40% speech
                    audio_chunk = AudioGenerator.generate_speech_like(20)
                else:  # 30% noise
                    audio_chunk = AudioGenerator.generate_white_noise(20, amplitude=0.1)
                
                await audio_processor.process_input_audio(audio_chunk)
                
                # Simulate real-time intervals
                await asyncio.sleep(0.02)  # 20ms
            
            await audio_processor.stop_processing()
            
        finally:
            monitor.stop_monitoring()
        
        # Verify pipeline performance
        metrics = monitor.get_metrics()
        
        assert len(audio_chunks_processed) == chunk_count
        assert len(gemini_chunks_sent) == chunk_count
        assert all(size > 0 for size in audio_chunks_processed)
        
        # Performance should be good for real-time processing
        assert metrics["duration_seconds"] < 5.0  # Should complete quickly
        assert metrics["peak_memory_mb"] < 200  # Reasonable memory usage
    
    @pytest.mark.asyncio
    async def test_voice_activity_detection_accuracy(self, audio_config):
        """Test Voice Activity Detection accuracy with various audio patterns."""
        audio_processor = RealTimeAudioProcessor(audio_config)
        
        # Test patterns with known characteristics
        test_patterns = [
            ("silence", AudioTestPatterns.speech_with_silence(), "silence_detection"),
            ("interrupted", AudioTestPatterns.interrupted_speech(), "interruption_handling"),
            ("varying_volume", AudioTestPatterns.varying_volume_speech(), "volume_adaptation"),
            ("noise_mixed", AudioTestPatterns.noise_with_speech(), "noise_robustness")
        ]
        
        vad_results = {}
        
        for pattern_name, audio_data, test_type in test_patterns:
            # Process pattern in chunks
            chunk_size = 320 * 2  # 20ms chunks in bytes
            pattern_results = []
            
            for i in range(0, len(audio_data), chunk_size):
                chunk = audio_data[i:i + chunk_size]
                if len(chunk) == chunk_size:
                    result = await audio_processor.process_input_audio(chunk)
                    pattern_results.append(result["vad_result"])
            
            vad_results[pattern_name] = {
                "results": pattern_results,
                "test_type": test_type,
                "total_chunks": len(pattern_results)
            }
        
        # Analyze VAD performance
        for pattern_name, data in vad_results.items():
            results = data["results"]
            
            # Calculate statistics
            speech_detected_count = sum(1 for r in results if r["speech_detected"])
            avg_energy = sum(r["energy"] for r in results) / len(results)
            
            # Verify reasonable detection
            assert len(results) > 0, f"No results for {pattern_name}"
            assert avg_energy >= 0, f"Invalid energy for {pattern_name}"
            
            # Pattern-specific validations
            if pattern_name == "silence":
                # Should detect some silence periods
                silence_count = sum(1 for r in results if not r["speech_detected"])
                assert silence_count > 0, "Should detect some silence"
            
            elif pattern_name in ["interrupted", "varying_volume", "noise_mixed"]:
                # Should detect some speech
                assert speech_detected_count > 0, f"Should detect speech in {pattern_name}"
    
    @pytest.mark.asyncio
    async def test_session_state_management(self):
        """Test comprehensive session state management."""
        session_manager = SessionManager()
        
        try:
            # Create multiple sessions
            sessions = []
            for i in range(5):
                session_id = await session_manager.create_session(
                    channel_id=f"channel-{i}",
                    caller_number=f"123456789{i}",
                    called_number="1000",
                    direction=CallDirection.INBOUND
                )
                sessions.append(session_id)
            
            # Test state transitions
            state_transitions = [
                SessionState.INITIALIZING,
                SessionState.ACTIVE,
                SessionState.WAITING_FOR_INPUT,
                SessionState.PROCESSING_AUDIO,
                SessionState.GENERATING_RESPONSE,
                SessionState.PLAYING_RESPONSE,
                SessionState.ENDED
            ]
            
            # Apply different states to different sessions
            # Note: We have 5 sessions and 7 states, so we'll cycle through them
            # This means sessions 0-4 get states 0-4, and no session gets ENDED state
            for i, session_id in enumerate(sessions):
                target_state = state_transitions[i % len(state_transitions)]
                
                if target_state != SessionState.ENDED:
                    success = await session_manager.update_session_state(session_id, target_state)
                    assert success
                    
                    session = session_manager.get_session(session_id)
                    assert session.state == target_state
                else:
                    await session_manager.end_session(session_id)
                    session = session_manager.get_session(session_id)
                    assert session.state == SessionState.ENDED
            
            # Manually end one session to test the counting logic
            await session_manager.end_session(sessions[0])
            session = session_manager.get_session(sessions[0])
            assert session.state == SessionState.ENDED
            
            # Test session statistics
            stats = session_manager.get_session_stats()
            assert stats["total_sessions"] == 5
            
            # Test active sessions
            active_sessions = session_manager.get_active_sessions()
            ended_sessions = [s for s in sessions if session_manager.get_session(s).state == SessionState.ENDED]
            
            # Count sessions that should be active (not ended)
            # We manually ended sessions[0], so we should have 4 active sessions
            expected_active = 4
            assert len(active_sessions) == expected_active
            assert len(ended_sessions) == 1
            
        finally:
            await session_manager.stop_cleanup_task()
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, audio_config, gemini_config):
        """Test error handling and recovery mechanisms."""
        # Setup components
        audio_processor = RealTimeAudioProcessor(audio_config)
        gemini_client = GeminiLiveClient(config=gemini_config)
        session_manager = SessionManager()
        
        # Track errors and recoveries
        errors_encountered = []
        recoveries_successful = []
        
        try:
            # Test 1: Audio processing with invalid data
            try:
                await audio_processor.process_input_audio(b"invalid_audio_data")
                # Should handle gracefully
                recoveries_successful.append("audio_invalid_data")
            except Exception as e:
                errors_encountered.append(("audio_invalid_data", str(e)))
            
            # Test 2: Gemini client operations when not connected
            gemini_client.is_connected = False
            
            success = await gemini_client.send_audio_chunk(b"test_audio")
            assert not success  # Should fail gracefully
            recoveries_successful.append("gemini_not_connected")
            
            # Test 3: Session operations on non-existent session
            try:
                success = await session_manager.update_session_state("non-existent", SessionState.ACTIVE)
                assert not success  # Should fail gracefully
                recoveries_successful.append("session_not_found")
            except Exception as e:
                errors_encountered.append(("session_not_found", str(e)))
            
            # Test 4: Recovery after errors
            # Reconnect Gemini
            gemini_client.is_connected = True
            gemini_client.websocket = AsyncMock()
            gemini_client._send_event = AsyncMock()
            
            # Should work after reconnection
            success = await gemini_client.send_audio_chunk(b"test_audio")
            assert success
            recoveries_successful.append("gemini_reconnected")
            
            # Create valid session
            session_id = await session_manager.create_session(
                "test-channel", "123", "456", CallDirection.INBOUND
            )
            
            success = await session_manager.update_session_state(session_id, SessionState.ACTIVE)
            assert success
            recoveries_successful.append("session_created")
            
            # Verify error handling effectiveness
            assert len(recoveries_successful) >= 4, "Not all recovery scenarios succeeded"
            
            # Errors should be minimal with proper error handling
            assert len(errors_encountered) <= 1, f"Too many unhandled errors: {errors_encountered}"
            
        finally:
            await session_manager.stop_cleanup_task()
    
    @pytest.mark.asyncio
    async def test_performance_under_load(self, audio_config, gemini_config, performance_thresholds):
        """Test system performance under realistic load."""
        # Setup components
        audio_processor = RealTimeAudioProcessor(audio_config)
        gemini_client = GeminiLiveClient(config=gemini_config)
        session_manager = SessionManager()
        
        # Mock Gemini for performance testing
        gemini_client.is_connected = True
        gemini_client.websocket = AsyncMock()
        gemini_client._send_event = AsyncMock()
        
        # Performance monitoring
        monitor = PerformanceMonitor()
        monitor.start_monitoring()
        
        try:
            # Create multiple concurrent sessions
            session_count = 10
            sessions = []
            
            for i in range(session_count):
                session_id = await session_manager.create_session(
                    f"channel-{i}", f"123456789{i}", "1000", CallDirection.INBOUND
                )
                sessions.append(session_id)
            
            await audio_processor.start_processing()
            
            # Simulate concurrent audio processing
            async def process_session_audio(session_id, session_index):
                for chunk_index in range(50):  # 1 second per session
                    audio_chunk = AudioGenerator.generate_speech_like(20)
                    
                    # Process audio
                    await audio_processor.process_input_audio(audio_chunk)
                    
                    # Send to Gemini
                    await gemini_client.send_audio_chunk(audio_chunk)
                    
                    # Update session
                    await session_manager.update_session_audio_state(
                        session_id, 
                        is_user_speaking=(chunk_index % 10 < 5),
                        audio_buffer_size=len(audio_chunk)
                    )
                    
                    # Simulate real-time processing
                    await asyncio.sleep(0.02)
            
            # Run all sessions concurrently
            tasks = [
                process_session_audio(session_id, i) 
                for i, session_id in enumerate(sessions)
            ]
            
            start_time = time.time()
            await asyncio.gather(*tasks)
            end_time = time.time()
            
            await audio_processor.stop_processing()
            
            # End all sessions
            for session_id in sessions:
                await session_manager.end_session(session_id)
            
        finally:
            monitor.stop_monitoring()
            await session_manager.stop_cleanup_task()
        
        # Analyze performance
        metrics = monitor.get_metrics()
        processing_time = end_time - start_time
        
        # Verify performance requirements
        # Note: memory_usage_mb threshold includes pytest overhead (~120-200MB)
        # For production deployment, use production_memory_usage_mb threshold (100MB)
        assert metrics["peak_memory_mb"] < performance_thresholds["memory_usage_mb"]
        assert metrics["peak_cpu_percent"] < performance_thresholds["cpu_usage_percent"]
        assert processing_time < 15.0  # Should complete within reasonable time
        
        # Log memory breakdown for debugging
        print(f"Load test memory - Total: {metrics['peak_memory_mb']:.1f}MB, "
              f"Baseline: {metrics.get('baseline_memory_mb', 0):.1f}MB, "
              f"Test impact: {metrics.get('peak_memory_delta_mb', 0):.1f}MB")
        
        # Verify all sessions were processed
        stats = session_manager.get_session_stats()
        assert stats["total_sessions"] == session_count
        assert stats["sessions_by_state"][SessionState.ENDED.value] == session_count
    
    @pytest.mark.asyncio
    async def test_audio_format_compatibility(self, audio_config):
        """Test audio format compatibility and conversion."""
        audio_processor = RealTimeAudioProcessor(audio_config)
        
        # Test different audio formats and patterns
        test_cases = [
            ("slin16_speech", AudioGenerator.generate_speech_like(100)),
            ("slin16_silence", AudioGenerator.generate_silence(100)),
            ("slin16_tone", AudioGenerator.generate_sine_wave(440, 100)),
            ("slin16_noise", AudioGenerator.generate_white_noise(100)),
            ("slin16_dtmf", AudioGenerator.generate_dtmf_tone("5", 100))
        ]
        
        format_results = {}
        
        for test_name, audio_data in test_cases:
            # Verify format before processing
            expected_samples = len(audio_data) // 2  # 16-bit samples
            expected_duration_ms = (expected_samples / audio_config.sample_rate) * 1000
            
            # Process audio
            result = await audio_processor.process_input_audio(audio_data)
            
            # Prepare for output
            output_audio = await audio_processor.prepare_output_audio(audio_data)
            
            format_results[test_name] = {
                "input_size": len(audio_data),
                "output_size": len(output_audio),
                "expected_duration_ms": expected_duration_ms,
                "processing_result": result,
                "format_preserved": len(audio_data) == len(output_audio)
            }
        
        # Verify format compatibility
        for test_name, results in format_results.items():
            assert results["format_preserved"], f"Format not preserved for {test_name}"
            assert results["processing_result"]["status"] == "processed"
            assert results["input_size"] > 0
            assert results["output_size"] > 0
    
    def test_configuration_validation(self, test_settings):
        """Test configuration validation and settings."""
        # Test audio configuration
        audio_config = AudioConfig(
            sample_rate=test_settings.audio_sample_rate,
            channels=test_settings.audio_channels,
            sample_width=test_settings.audio_sample_width,
            chunk_size=test_settings.audio_chunk_size,
            buffer_size=test_settings.audio_buffer_size
        )
        
        assert audio_config.sample_rate == 16000
        assert audio_config.channels == 1
        assert audio_config.sample_width == 2
        assert audio_config.format.value == "slin16"
        
        # Test Gemini configuration
        gemini_config = GeminiLiveConfig(
            model=test_settings.gemini_live_model,
            voice=test_settings.gemini_voice
        )
        
        assert gemini_config.model == "gemini-2.0-flash-exp"
        assert gemini_config.voice == "Puck"
        assert gemini_config.input_audio_format == "pcm16"
        assert gemini_config.output_audio_format == "pcm16"
        
        # Test settings validation
        assert test_settings.google_api_key == "test-api-key"
        assert test_settings.ari_base_url == "http://localhost:8088/ari"
        assert test_settings.external_media_host == "localhost"
        assert test_settings.external_media_port == 8090


@pytest.mark.e2e
class TestFeatureIntegration:
    """Test integration between all major features."""
    
    @pytest.mark.asyncio
    async def test_interruption_handling_workflow(self, audio_config, gemini_config):
        """Test interruption handling in conversation flow."""
        # Setup components
        audio_processor = RealTimeAudioProcessor(audio_config)
        gemini_client = GeminiLiveClient(config=gemini_config)
        session_manager = SessionManager()
        
        # Mock Gemini
        gemini_client.is_connected = True
        gemini_client.websocket = AsyncMock()
        gemini_client._send_event = AsyncMock()
        
        # Track interruption events
        interruption_events = []
        
        async def interruption_handler(data):
            interruption_events.append(data)
        
        audio_processor.register_callback("speech_start", interruption_handler)
        
        try:
            # Create session
            session_id = await session_manager.create_session(
                "test-channel", "123", "456", CallDirection.INBOUND
            )
            
            await audio_processor.start_processing()
            
            # Simulate conversation with interruption
            # 1. User speaks
            user_speech = AudioGenerator.generate_speech_like(500)  # 500ms
            await audio_processor.process_input_audio(user_speech)
            
            # 2. Assistant starts responding (simulated)
            await session_manager.update_session_audio_state(
                session_id, is_assistant_speaking=True
            )
            
            # 3. User interrupts (speaks while assistant is speaking)
            interruption_speech = AudioGenerator.generate_speech_like(300)  # 300ms
            await audio_processor.process_input_audio(interruption_speech)
            
            # Record interruption
            await session_manager.record_interruption(session_id)
            
            # 4. Assistant stops, user continues
            await session_manager.update_session_audio_state(
                session_id, is_assistant_speaking=False, is_user_speaking=True
            )
            
            await audio_processor.stop_processing()
            
            # Verify interruption handling
            session = session_manager.get_session(session_id)
            assert session.metrics.interruptions >= 1
            
        finally:
            await session_manager.stop_cleanup_task()
    
    @pytest.mark.asyncio
    async def test_multi_session_handling(self):
        """Test handling multiple concurrent sessions."""
        session_manager = SessionManager()
        
        try:
            # Create multiple sessions
            session_count = 20
            sessions = []
            
            for i in range(session_count):
                session_id = await session_manager.create_session(
                    f"channel-{i}",
                    f"caller-{i}",
                    "1000",
                    CallDirection.INBOUND
                )
                sessions.append(session_id)
            
            # Perform operations on all sessions concurrently
            async def session_operations(session_id, index):
                # Update states
                await session_manager.update_session_state(session_id, SessionState.ACTIVE)
                
                # Add conversation turns
                for turn_index in range(5):
                    await session_manager.add_conversation_turn(
                        session_id,
                        "user" if turn_index % 2 == 0 else "assistant",
                        "audio",
                        {"text": f"Message {turn_index}"},
                        duration=1.0
                    )
                
                # Update audio state
                await session_manager.update_session_audio_state(
                    session_id,
                    is_user_speaking=(index % 2 == 0),
                    audio_buffer_size=1024
                )
                
                # End some sessions
                if index % 3 == 0:
                    await session_manager.end_session(session_id)
            
            # Run all operations concurrently
            tasks = [session_operations(session_id, i) for i, session_id in enumerate(sessions)]
            await asyncio.gather(*tasks)
            
            # Verify results
            stats = session_manager.get_session_stats()
            assert stats["total_sessions"] == session_count
            
            active_sessions = session_manager.get_active_sessions()
            ended_sessions_count = stats["sessions_by_state"][SessionState.ENDED.value]
            
            # Verify session distribution
            assert len(active_sessions) + ended_sessions_count == session_count
            
        finally:
            await session_manager.stop_cleanup_task()


if __name__ == "__main__":
    # Run the comprehensive test suite
    pytest.main([__file__, "-v", "--tb=short"])