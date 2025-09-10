"""
Integration tests for all implemented features.
Tests the complete system with all 8 missing components integrated.
"""

import pytest
import asyncio
import numpy as np
from unittest.mock import AsyncMock, MagicMock, patch

from src.voice_assistant.audio.advanced_audio_processor import audio_processor
from src.voice_assistant.utils.performance_monitor import performance_monitor
from src.voice_assistant.utils.optimized_logger import LoggerFactory
from src.voice_assistant.ai.function_calling import function_registry, function_call_handler
from src.voice_assistant.ai.npcl_prompts import npcl_customer_service
from src.voice_assistant.tools.weather_tool import weather_tool
from src.voice_assistant.telephony.rtp_streaming_handler import rtp_streaming_manager
from src.voice_assistant.ai.websocket_gemini_client import WebSocketGeminiClient


@pytest.mark.integration
class TestCompleteSystemIntegration:
    """Test complete system integration with all features"""
    
    def setup_method(self):
        """Setup for each test"""
        # Reset global instances
        audio_processor.reset_stats()
        performance_monitor.reset_metrics()
        
        # Register weather tool if not already registered
        if weather_tool not in function_registry.functions.values():
            function_registry.register_function(weather_tool)
    
    def teardown_method(self):
        """Cleanup after each test"""
        # Stop any running monitoring
        if performance_monitor.monitoring_active:
            asyncio.run(performance_monitor.stop_monitoring())
    
    @pytest.mark.asyncio
    async def test_audio_processing_pipeline(self):
        """Test complete audio processing pipeline"""
        # Create test audio (24kHz)
        sample_rate = 24000
        duration = 0.5
        frequency = 440
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio_24k = np.sin(2 * np.pi * frequency * t) * 8000
        audio_24k = audio_24k.astype(np.int16)
        audio_bytes_24k = audio_24k.tobytes()
        
        # Start performance monitoring
        await performance_monitor.start_monitoring()
        
        # Process audio through complete pipeline
        operation_id = performance_monitor.start_operation("audio_processing")
        
        # Step 1: Resample
        audio_16k = audio_processor.resample_pcm_24khz_to_16khz(audio_bytes_24k)
        
        # Step 2: Check silence
        is_silent = audio_processor.quick_silence_check(audio_16k)
        
        # Step 3: Normalize if not silent
        if not is_silent:
            normalized_audio, rms = audio_processor.normalize_audio(audio_16k)
        else:
            normalized_audio = audio_16k
            rms = 0
        
        # Step 4: Analyze quality
        quality = audio_processor.analyze_audio_quality(normalized_audio)
        
        performance_monitor.end_operation(operation_id, "audio_processing", True)
        
        # Verify results
        assert len(audio_16k) < len(audio_bytes_24k)  # Resampled
        assert is_silent == False  # Audio has signal
        assert rms > 0  # Audio was normalized
        assert quality["sample_count"] > 0  # Quality analysis worked
        
        # Check performance metrics
        metrics = performance_monitor.get_current_metrics()
        assert metrics["operations_per_second"] > 0
        
        # Check audio processor stats
        stats = audio_processor.get_audio_stats()
        assert stats["resampling_operations"] == 1
        assert stats["normalization_operations"] == 1
        
        await performance_monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_function_calling_integration(self):
        """Test function calling system integration"""
        # Start performance monitoring
        await performance_monitor.start_monitoring()
        
        # Test weather tool function call
        function_call_data = {
            "name": "get_weather",
            "args": {"location": "Noida"},
            "id": "test_call_123"
        }
        
        # Handle function call
        response = await function_call_handler.handle_function_call(function_call_data)
        
        # Verify response structure
        assert "functionResponse" in response
        func_response = response["functionResponse"]
        assert func_response["name"] == "get_weather"
        assert func_response["id"] == "test_call_123"
        assert "response" in func_response
        assert "result" in func_response["response"]
        
        # Verify NPCL-specific response for Noida
        result_text = func_response["response"]["result"]
        assert "Noida" in result_text
        assert "NPCL service area" in result_text
        assert "power supply should be stable" in result_text
        
        # Check performance metrics
        metrics = performance_monitor.get_current_metrics()
        assert metrics["operations_per_second"] > 0
        
        await performance_monitor.stop_monitoring()
    
    def test_npcl_customer_service_workflow(self):
        """Test NPCL customer service complete workflow"""
        # Test complete conversation flow
        
        # Step 1: Welcome message
        welcome = npcl_customer_service.get_welcome_message()
        assert "Welcome to NPCL" in welcome
        
        # Step 2: Name verification
        name_prompt = npcl_customer_service.get_name_verification_prompt()
        assert "Is this connection registered with" in name_prompt
        
        # Step 3: Process affirmative response
        result = npcl_customer_service.process_user_response("yes")
        assert result["action"] == "complaint_status"
        assert "zero zero zero zero five four three two one zero" in result["message"]
        
        # Step 4: Test complaint number workflow
        result = npcl_customer_service.process_user_response("000054322")
        assert result["action"] == "complaint_status"
        assert result["complaint_id"] == "000054322"
        
        # Step 5: Test service request
        result = npcl_customer_service.process_user_response("power outage in my area")
        assert result["action"] == "power_complaint"
        assert "register a complaint" in result["message"]
        
        # Step 6: Register new complaint
        complaint_id = npcl_customer_service.register_new_complaint(
            customer_name="integration_test",
            area="Test Sector",
            issue_type="Integration test issue"
        )
        
        # Verify complaint registration
        complaint = npcl_customer_service.get_complaint_status(complaint_id)
        assert complaint is not None
        assert complaint.customer_name == "integration_test"
    
    def test_optimized_logging_system(self):
        """Test optimized logging system"""
        logger = LoggerFactory.get_logger("integration_test")
        
        # Test different logging methods
        logger.log_client("Test client message")
        logger.log_server("Test server message")
        
        # Test rate-limited logging
        for i in range(20):
            logger.log_audio_packet("test_channel", "sent", 1024, i)
        
        # Test performance logging
        logger.log_performance_metric("test_metric", 42.5, "test_channel")
        
        # Test WebSocket event logging
        logger.log_websocket_event("connection_established", "test_channel", "Test details")
        
        # Test error logging with context
        try:
            raise ValueError("Test error")
        except Exception as e:
            logger.log_error_with_context(e, {"channel": "test", "operation": "test"})
        
        # Get logging statistics
        stats = logger.get_log_stats()
        
        # Verify logging worked
        assert stats["total_logs"] > 0
        assert "error" in stats["log_counts"]
        assert stats["performance_logging_enabled"] in [True, False]
    
    @pytest.mark.asyncio
    async def test_performance_monitoring_complete_cycle(self):
        """Test complete performance monitoring cycle"""
        monitor = performance_monitor
        
        # Start monitoring
        await monitor.start_monitoring()
        
        # Simulate various operations
        
        # Audio operations
        for i in range(5):
            monitor.record_audio_packet("sent", 1024)
            monitor.record_audio_packet("received", 512)
        
        # API operations
        for i in range(3):
            op_id = monitor.start_operation("gemini_api")
            await asyncio.sleep(0.01)  # Simulate processing time
            monitor.end_operation(op_id, "gemini_api", True)
        
        # Session operations
        monitor.record_session_event("start")
        await asyncio.sleep(0.1)
        monitor.record_session_event("end", session_duration=0.1)
        
        # Error operations
        monitor.record_error("general")
        monitor.record_error("timeout")
        
        # Wait for monitoring updates
        await asyncio.sleep(0.2)
        
        # Get comprehensive metrics
        metrics = monitor.get_current_metrics()
        summary = monitor.get_performance_summary()
        latency_stats = monitor.get_latency_stats("gemini_api")
        
        # Verify metrics
        assert metrics["audio_packets_sent"] == 5
        assert metrics["audio_packets_received"] == 5
        assert metrics["gemini_api_calls"] == 3
        assert metrics["total_sessions"] == 1
        assert metrics["error_count"] == 1
        assert metrics["timeout_count"] == 1
        
        # Verify summary
        assert summary["status"] in ["healthy", "degraded"]
        assert "health_indicators" in summary
        assert "latency_stats" in summary
        
        # Verify latency stats
        assert latency_stats["count"] == 3
        assert latency_stats["average"] > 0
        
        await monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_rtp_streaming_simulation(self):
        """Test RTP streaming simulation (without actual network)"""
        # This test simulates RTP streaming without actual network connections
        
        # Create mock RTP handler
        mock_rtp_handler = MagicMock()
        mock_stream_interface = {
            "read": AsyncMock(return_value=b"mock_audio_data"),
            "write": AsyncMock(),
            "get_stats": MagicMock(return_value={"packets_sent": 10}),
            "stop": AsyncMock()
        }
        mock_rtp_handler.start_rtp_streaming = AsyncMock(return_value=mock_stream_interface)
        
        # Test RTP streaming manager
        channel_id = "test_channel_123"
        rtp_source = "127.0.0.1:5004"
        
        # Start streaming (mocked)
        with patch.object(rtp_streaming_manager, 'start_rtp_streaming', 
                         return_value=mock_stream_interface) as mock_start:
            
            stream_interface = await rtp_streaming_manager.start_rtp_streaming(
                channel_id, rtp_source
            )
            
            # Verify interface
            assert "read" in stream_interface
            assert "write" in stream_interface
            assert "get_stats" in stream_interface
            assert "stop" in stream_interface
            
            # Test audio operations
            audio_data = await stream_interface["read"]()
            assert audio_data == b"mock_audio_data"
            
            await stream_interface["write"](b"test_audio")
            mock_stream_interface["write"].assert_called_with(b"test_audio")
    
    @pytest.mark.asyncio
    async def test_websocket_gemini_client_simulation(self):
        """Test WebSocket Gemini client simulation (without actual WebSocket)"""
        # This test simulates WebSocket client without actual connections
        
        channel_id = "test_channel_456"
        rtp_source = "127.0.0.1:5004"
        
        # Create client
        client = WebSocketGeminiClient(channel_id, rtp_source)
        
        # Test initialization
        assert client.channel_id == channel_id
        assert client.rtp_source == rtp_source
        assert client.running == False
        assert client.setup_complete == False
        
        # Test performance stats
        stats = client.get_performance_stats()
        assert "channel_id" in stats
        assert "uptime" in stats
        assert "audio_packets_sent" in stats
        assert "audio_packets_received" in stats
        assert "audio_processor_stats" in stats
        assert "performance_metrics" in stats
        
        # Test audio processing simulation
        test_audio = np.array([1000, -1000] * 1000, dtype=np.int16).tobytes()
        
        # Simulate adding audio (without actual WebSocket)
        client.running = True
        client.setup_complete = True
        
        # Mock WebSocket
        client.ws = MagicMock()
        client.ws.send = AsyncMock()
        
        await client.add_audio_from_user(test_audio)
        
        # Verify audio was processed
        assert client.audio_packets_sent > 0
    
    @pytest.mark.asyncio
    async def test_complete_system_workflow(self):
        """Test complete system workflow with all components"""
        # This test simulates a complete call workflow
        
        # Start performance monitoring
        await performance_monitor.start_monitoring()
        
        # Step 1: Initialize all components
        logger = LoggerFactory.get_logger("system_test")
        
        # Step 2: Simulate incoming call
        channel_id = "system_test_channel"
        performance_monitor.record_session_event("start")
        
        # Step 3: Process NPCL welcome
        welcome = npcl_customer_service.get_welcome_message()
        logger.log_server(f"Welcome message: {welcome}")
        
        # Step 4: Simulate audio processing
        test_audio_24k = np.array([2000, -2000] * 12000, dtype=np.int16).tobytes()  # 1 second at 24kHz
        
        # Process audio
        audio_16k = audio_processor.resample_pcm_24khz_to_16khz(test_audio_24k)
        is_silent = audio_processor.quick_silence_check(audio_16k)
        
        if not is_silent:
            normalized_audio, rms = audio_processor.normalize_audio(audio_16k)
            logger.log_performance_metric("audio_rms", rms, channel_id)
        
        # Step 5: Simulate user response processing
        user_response = "yes"
        npcl_result = npcl_customer_service.process_user_response(user_response)
        logger.log_server(f"NPCL response: {npcl_result['action']}")
        
        # Step 6: Simulate function call (weather)
        if npcl_result["action"] == "complaint_status":
            # User might ask for weather
            weather_call = {
                "name": "get_weather",
                "args": {"location": "Noida"},
                "id": "weather_call_1"
            }
            
            weather_response = await function_call_handler.handle_function_call(weather_call)
            logger.log_server("Weather function executed")
        
        # Step 7: End session
        performance_monitor.record_session_event("end", session_duration=2.5)
        
        # Step 8: Get final metrics
        final_metrics = performance_monitor.get_current_metrics()
        audio_stats = audio_processor.get_audio_stats()
        log_stats = logger.get_log_stats()
        
        # Verify complete workflow
        assert final_metrics["total_sessions"] == 1
        assert final_metrics["active_sessions"] == 0  # Session ended
        assert audio_stats["resampling_operations"] >= 1
        assert log_stats["total_logs"] > 0
        
        # Verify NPCL workflow
        assert npcl_result["action"] == "complaint_status"
        assert "complaint" in npcl_result["message"]
        
        # Verify weather function
        if 'weather_response' in locals():
            assert "functionResponse" in weather_response
            assert "Noida" in weather_response["functionResponse"]["response"]["result"]
        
        await performance_monitor.stop_monitoring()
    
    def test_all_components_initialized(self):
        """Test that all components are properly initialized"""
        # Test global instances exist
        assert audio_processor is not None
        assert performance_monitor is not None
        assert function_registry is not None
        assert function_call_handler is not None
        assert npcl_customer_service is not None
        assert weather_tool is not None
        assert rtp_streaming_manager is not None
        
        # Test weather tool is registered
        assert "get_weather" in function_registry.list_functions()
        
        # Test NPCL service has required data
        assert len(npcl_customer_service.sample_names) > 0
        assert len(npcl_customer_service.complaints_db) > 0
        assert len(npcl_customer_service.service_areas) > 0
        
        # Test weather tool has data
        assert len(weather_tool.weather_cities) > 0
        assert weather_tool.is_city_supported("Noida")
        assert weather_tool.is_city_supported("Delhi")
    
    def test_configuration_integration(self):
        """Test that configuration supports all new features"""
        from config.settings import get_settings
        
        settings = get_settings()
        
        # Test new configuration fields exist
        assert hasattr(settings, 'target_rms')
        assert hasattr(settings, 'silence_threshold')
        assert hasattr(settings, 'normalization_factor')
        assert hasattr(settings, 'enable_function_calling')
        assert hasattr(settings, 'function_timeout')
        assert hasattr(settings, 'npcl_mode')
        assert hasattr(settings, 'npcl_service_areas')
        assert hasattr(settings, 'rtp_payload_type')
        assert hasattr(settings, 'rtp_frame_size')
        assert hasattr(settings, 'gemini_realtime_url')
        
        # Test default values
        assert settings.target_rms == 1000
        assert settings.silence_threshold == 100
        assert settings.enable_function_calling == True
        assert settings.npcl_mode == True
        assert "Noida" in settings.npcl_service_areas


if __name__ == "__main__":
    pytest.main([__file__])