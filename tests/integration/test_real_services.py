"""
Integration tests with real services for production validation.
Tests actual integration with Asterisk ARI, Gemini API, and external services.
"""

import pytest
import asyncio
import os
import time
from typing import Dict, Any, Optional
from unittest.mock import patch

from voice_assistant.utils.dependency_manager import get_dependency_manager
from voice_assistant.telephony.realtime_ari_handler import RealTimeARIHandler
from voice_assistant.ai.gemini_live_client import GeminiLiveClient, GeminiLiveConfig
from voice_assistant.core.session_manager import SessionManager
from voice_assistant.observability.monitoring import get_monitoring_system
from config.production_settings import get_production_settings


@pytest.mark.integration
@pytest.mark.real_services
class TestRealServiceIntegration:
    """Integration tests with real external services"""
    
    @pytest.fixture(autouse=True)
    def setup_real_services(self):
        """Setup for real service tests"""
        # Check if we should run real service tests
        if not os.getenv("RUN_REAL_SERVICE_TESTS", "false").lower() == "true":
            pytest.skip("Real service tests disabled. Set RUN_REAL_SERVICE_TESTS=true to enable")
        
        # Validate required environment variables
        required_vars = ["GOOGLE_API_KEY", "ARI_BASE_URL", "ARI_USERNAME", "ARI_PASSWORD"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            pytest.skip(f"Missing required environment variables: {missing_vars}")
    
    @pytest.mark.asyncio
    async def test_gemini_api_connection(self):
        """Test real connection to Gemini API"""
        config = GeminiLiveConfig(
            model="gemini-1.5-flash",
            voice="Puck"
        )
        
        client = GeminiLiveClient(
            api_key=os.getenv("GOOGLE_API_KEY"),
            config=config
        )
        
        try:
            # Test connection
            connected = await client.connect()
            assert connected, "Failed to connect to Gemini Live API"
            
            # Test session creation
            session_id = await client.start_conversation()
            assert session_id is not None, "Failed to start conversation"
            
            # Test basic audio processing
            test_audio = b"test audio data" * 100  # Simulate audio chunk
            success = await client.send_audio_chunk(test_audio)
            assert success, "Failed to send audio chunk"
            
            # Test session cleanup
            await client.end_conversation()
            
        finally:
            await client.disconnect()
    
    @pytest.mark.asyncio
    async def test_asterisk_ari_connection(self):
        """Test real connection to Asterisk ARI"""
        import requests
        
        ari_base_url = os.getenv("ARI_BASE_URL", "http://localhost:8088/ari")
        ari_username = os.getenv("ARI_USERNAME", "asterisk")
        ari_password = os.getenv("ARI_PASSWORD", "1234")
        
        auth = (ari_username, ari_password)
        
        try:
            # Test basic connectivity
            response = requests.get(f"{ari_base_url}/asterisk/info", auth=auth, timeout=10)
            assert response.status_code == 200, f"ARI connection failed: {response.status_code}"
            
            # Test channels endpoint
            response = requests.get(f"{ari_base_url}/channels", auth=auth, timeout=10)
            assert response.status_code == 200, "Failed to access channels endpoint"
            
            # Test applications endpoint
            response = requests.get(f"{ari_base_url}/applications", auth=auth, timeout=10)
            assert response.status_code == 200, "Failed to access applications endpoint"
            
        except requests.exceptions.RequestException as e:
            pytest.fail(f"ARI connection test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_end_to_end_call_simulation(self):
        """Test end-to-end call simulation with real services"""
        # Initialize real-time ARI handler
        handler = RealTimeARIHandler()
        
        try:
            # Start the handler
            started = await handler.start()
            assert started, "Failed to start real-time ARI handler"
            
            # Simulate a call event
            test_event = {
                "type": "StasisStart",
                "application": "gemini-voice-assistant",
                "timestamp": "2024-01-01T12:00:00.000Z",
                "channel": {
                    "id": "test-channel-real-001",
                    "name": "SIP/test-real-00000001",
                    "state": "Ring",
                    "caller": {
                        "name": "Integration Test",
                        "number": "+91-9999999999"
                    },
                    "dialplan": {
                        "context": "default",
                        "exten": "1000",
                        "priority": 1
                    }
                }
            }
            
            # Process the event
            result = await handler.handle_ari_event(test_event)
            assert result["status"] == "handled", f"Event handling failed: {result}"
            
            # Verify call tracking
            assert "test-channel-real-001" in handler.active_calls
            
            # Simulate call end
            end_event = {
                "type": "StasisEnd",
                "application": "gemini-voice-assistant",
                "timestamp": "2024-01-01T12:05:00.000Z",
                "channel": {
                    "id": "test-channel-real-001",
                    "state": "Up"
                }
            }
            
            result = await handler.handle_ari_event(end_event)
            assert result["status"] == "handled", "Call end handling failed"
            
            # Verify cleanup
            assert "test-channel-real-001" not in handler.active_calls
            
        finally:
            await handler.stop()
    
    @pytest.mark.asyncio
    async def test_monitoring_system_integration(self):
        """Test monitoring system with real metrics collection"""
        monitoring = get_monitoring_system({
            "monitoring_interval": 5,  # Short interval for testing
            "enable_metrics": True
        })
        
        try:
            # Start monitoring
            monitoring.start_monitoring()
            
            # Wait for metrics collection
            await asyncio.sleep(10)
            
            # Verify metrics are being collected
            metrics = monitoring.get_metrics_summary()
            
            assert "system" in metrics
            assert "cpu_usage" in metrics["system"]
            assert "memory_usage" in metrics["system"]
            
            # Verify health checks
            health = monitoring.get_health_status()
            assert health["status"] in ["healthy", "degraded", "unhealthy"]
            assert health["last_check"] is not None
            
        finally:
            monitoring.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_production_configuration_validation(self):
        """Test production configuration validation"""
        settings = get_production_settings()
        
        # Validate critical settings
        assert settings.google_api_key is not None, "Google API key not configured"
        assert settings.ari_base_url is not None, "ARI base URL not configured"
        assert settings.ari_username is not None, "ARI username not configured"
        assert settings.ari_password is not None, "ARI password not configured"
        
        # Validate production-specific settings
        if settings.environment.value == "production":
            assert settings.enable_security_headers is True
            assert settings.enable_rate_limiting is True
            assert settings.log_level.value in ["INFO", "WARNING", "ERROR"]
            assert settings.max_concurrent_calls >= 50
        
        # Test configuration methods
        audio_config = settings.get_optimized_audio_config()
        assert "sample_rate" in audio_config
        assert "chunk_size" in audio_config
        
        security_config = settings.get_security_config()
        assert "enable_security_headers" in security_config
        assert "enable_rate_limiting" in security_config
        
        monitoring_config = settings.get_monitoring_config()
        assert "enable_metrics" in monitoring_config
        assert "performance_thresholds" in monitoring_config
    
    @pytest.mark.asyncio
    async def test_dependency_validation(self):
        """Test that all required dependencies are available"""
        dm = get_dependency_manager()
        
        # Validate required dependencies
        success = dm.validate_required_dependencies()
        assert success, "Required dependencies validation failed"
        
        # Check dependency status
        status = dm.check_dependencies(required_only=True)
        failed_deps = [name for name, available in status.items() if not available]
        
        assert len(failed_deps) == 0, f"Required dependencies not available: {failed_deps}"
        
        # Generate dependency report
        report = dm.get_dependency_report()
        assert report["required_missing"] == 0, f"Missing required dependencies: {report['missing_details']}"
    
    @pytest.mark.asyncio
    async def test_performance_under_load(self, performance_thresholds):
        """Test system performance under simulated load"""
        # Create multiple concurrent operations
        tasks = []
        
        # Simulate multiple session creations
        session_manager = SessionManager()
        
        start_time = time.time()
        
        for i in range(10):  # Create 10 concurrent sessions
            task = asyncio.create_task(
                session_manager.create_session(
                    channel_id=f"test-channel-{i}",
                    caller_number=f"+91-999999{i:04d}",
                    called_number="1000"
                )
            )
            tasks.append(task)
        
        # Wait for all sessions to be created
        session_ids = await asyncio.gather(*tasks)
        
        creation_time = time.time() - start_time
        
        # Verify performance
        avg_creation_time = (creation_time / len(session_ids)) * 1000  # Convert to ms
        assert avg_creation_time < performance_thresholds["session_creation_ms"], \
            f"Session creation too slow: {avg_creation_time:.2f}ms > {performance_thresholds['session_creation_ms']}ms"
        
        # Verify all sessions were created
        assert len(session_ids) == 10
        assert all(session_id is not None for session_id in session_ids)
        
        # Cleanup sessions
        cleanup_tasks = [
            session_manager.end_session(session_id) 
            for session_id in session_ids
        ]
        await asyncio.gather(*cleanup_tasks)
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self):
        """Test error handling with real service failures"""
        from voice_assistant.utils.error_handler import get_error_handler
        
        error_handler = get_error_handler()
        
        # Test with invalid API key
        invalid_client = GeminiLiveClient(
            api_key="invalid-key-12345",
            config=GeminiLiveConfig()
        )
        
        try:
            # This should fail and be handled gracefully
            connected = await invalid_client.connect()
            assert not connected, "Connection should fail with invalid API key"
            
        except Exception as e:
            # Error should be handled by error handler
            error_info = error_handler.handle_error(e)
            assert error_info.category.value in ["ai", "network"]
            assert error_info.severity.value in ["medium", "high"]
        
        # Test error statistics
        stats = error_handler.get_error_statistics()
        assert stats["total_errors"] > 0
        
        # Test recent errors
        recent_errors = error_handler.get_recent_errors(limit=5)
        assert len(recent_errors) > 0
        assert all("error_id" in error for error in recent_errors)


@pytest.mark.integration
@pytest.mark.stress
class TestStressIntegration:
    """Stress tests for production readiness"""
    
    @pytest.mark.asyncio
    async def test_concurrent_call_handling(self, performance_thresholds):
        """Test handling multiple concurrent calls"""
        if not os.getenv("RUN_STRESS_TESTS", "false").lower() == "true":
            pytest.skip("Stress tests disabled. Set RUN_STRESS_TESTS=true to enable")
        
        handler = RealTimeARIHandler()
        
        try:
            await handler.start()
            
            # Create multiple concurrent call events
            concurrent_calls = 20
            tasks = []
            
            for i in range(concurrent_calls):
                event = {
                    "type": "StasisStart",
                    "application": "gemini-voice-assistant",
                    "timestamp": "2024-01-01T12:00:00.000Z",
                    "channel": {
                        "id": f"stress-test-channel-{i}",
                        "caller": {"number": f"+91-888888{i:04d}"},
                        "dialplan": {"exten": "1000"}
                    }
                }
                
                task = asyncio.create_task(handler.handle_ari_event(event))
                tasks.append(task)
            
            # Process all events concurrently
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            processing_time = time.time() - start_time
            
            # Verify results
            successful_calls = sum(1 for result in results 
                                 if isinstance(result, dict) and result.get("status") == "handled")
            
            success_rate = (successful_calls / concurrent_calls) * 100
            avg_processing_time = (processing_time / concurrent_calls) * 1000  # ms
            
            # Validate performance
            assert success_rate >= 90, f"Success rate too low: {success_rate:.1f}%"
            assert avg_processing_time < 100, f"Processing too slow: {avg_processing_time:.2f}ms"
            
            # Verify active calls
            assert len(handler.active_calls) == successful_calls
            
        finally:
            await handler.stop()
    
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, performance_thresholds):
        """Test memory usage under sustained load"""
        if not os.getenv("RUN_STRESS_TESTS", "false").lower() == "true":
            pytest.skip("Stress tests disabled")
        
        import psutil
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create and destroy many sessions
        session_manager = SessionManager()
        
        for batch in range(5):  # 5 batches
            # Create 50 sessions
            session_tasks = [
                session_manager.create_session(
                    channel_id=f"memory-test-{batch}-{i}",
                    caller_number=f"+91-777777{i:04d}",
                    called_number="1000"
                )
                for i in range(50)
            ]
            
            session_ids = await asyncio.gather(*session_tasks)
            
            # Do some work with sessions
            await asyncio.sleep(1)
            
            # Clean up sessions
            cleanup_tasks = [
                session_manager.end_session(session_id)
                for session_id in session_ids if session_id
            ]
            await asyncio.gather(*cleanup_tasks)
            
            # Check memory usage
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = current_memory - initial_memory
            
            # Memory should not grow excessively
            assert memory_increase < performance_thresholds["memory_usage_mb"], \
                f"Memory usage increased too much: {memory_increase:.1f}MB"
        
        # Final memory check after cleanup
        await asyncio.sleep(2)  # Allow for garbage collection
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        total_increase = final_memory - initial_memory
        
        # Total memory increase should be minimal
        assert total_increase < 50, f"Memory leak detected: {total_increase:.1f}MB increase"