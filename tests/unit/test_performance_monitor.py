"""
Test cases for Performance Monitor.
Tests metrics tracking, latency measurement, and system monitoring.
"""

import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock

from src.voice_assistant.utils.performance_monitor import (
    PerformanceMonitor, PerformanceMetrics, performance_monitor
)


class TestPerformanceMetrics:
    """Test cases for PerformanceMetrics dataclass"""
    
    def test_initialization(self):
        """Test metrics initialization"""
        metrics = PerformanceMetrics()
        
        # Check default values
        assert metrics.audio_packets_sent == 0
        assert metrics.audio_packets_received == 0
        assert metrics.total_audio_latency == 0.0
        assert metrics.latency_measurements == 0
        assert metrics.cpu_usage_percent == 0.0
        assert metrics.memory_usage_mb == 0.0
        assert metrics.active_sessions == 0
        assert metrics.error_count == 0
        
        # Check timestamps
        assert metrics.start_time > 0
        assert metrics.last_update > 0


class TestPerformanceMonitor:
    """Test cases for PerformanceMonitor"""
    
    def setup_method(self):
        """Setup for each test"""
        self.monitor = PerformanceMonitor(enable_logging=False, update_interval=0.1)
    
    def teardown_method(self):
        """Cleanup after each test"""
        if self.monitor.monitoring_active:
            asyncio.run(self.monitor.stop_monitoring())
    
    def test_initialization(self):
        """Test monitor initialization"""
        assert isinstance(self.monitor.metrics, PerformanceMetrics)
        assert len(self.monitor.metrics_history) == 0
        assert len(self.monitor.latency_history) == 0
        assert len(self.monitor.pending_operations) == 0
        assert self.monitor.monitoring_active == False
        assert self.monitor.enable_logging == False
        assert self.monitor.update_interval == 0.1
    
    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self):
        """Test starting and stopping monitoring"""
        # Start monitoring
        await self.monitor.start_monitoring()
        assert self.monitor.monitoring_active == True
        assert self.monitor.monitor_task is not None
        
        # Wait a bit for monitoring to run
        await asyncio.sleep(0.2)
        
        # Stop monitoring
        await self.monitor.stop_monitoring()
        assert self.monitor.monitoring_active == False
    
    def test_start_operation(self):
        """Test operation tracking start"""
        operation_id = self.monitor.start_operation("test_operation")
        
        assert operation_id is not None
        assert operation_id in self.monitor.pending_operations
        assert self.monitor.pending_operations[operation_id] > 0
    
    def test_start_operation_with_custom_id(self):
        """Test operation tracking with custom ID"""
        custom_id = "custom_test_123"
        operation_id = self.monitor.start_operation("test_operation", custom_id)
        
        assert operation_id == custom_id
        assert custom_id in self.monitor.pending_operations
    
    def test_end_operation_success(self):
        """Test successful operation completion"""
        operation_id = self.monitor.start_operation("gemini_api")
        time.sleep(0.01)  # Small delay to measure latency
        
        self.monitor.end_operation(operation_id, "gemini_api", success=True)
        
        # Check operation is removed from pending
        assert operation_id not in self.monitor.pending_operations
        
        # Check metrics updated
        assert self.monitor.metrics.gemini_api_calls == 1
        assert self.monitor.metrics.gemini_api_latency > 0
        
        # Check latency history
        assert len(self.monitor.latency_history["gemini_api"]) == 1
    
    def test_end_operation_failure(self):
        """Test failed operation completion"""
        operation_id = self.monitor.start_operation("speech_recognition")
        
        self.monitor.end_operation(operation_id, "speech_recognition", success=False)
        
        # Check error count increased
        assert self.monitor.metrics.error_count == 1
        
        # Check metrics still updated
        assert self.monitor.metrics.speech_recognition_calls == 1
    
    def test_end_nonexistent_operation(self):
        """Test ending operation that doesn't exist"""
        # Should not raise exception
        self.monitor.end_operation("nonexistent", "test_operation", success=True)
        
        # No metrics should be updated
        assert self.monitor.metrics.gemini_api_calls == 0
    
    def test_record_audio_packet(self):
        """Test audio packet recording"""
        # Record sent packets
        self.monitor.record_audio_packet("sent", 1024)
        self.monitor.record_audio_packet("sent", 512)
        
        # Record received packets
        self.monitor.record_audio_packet("received", 2048)
        
        # Check metrics
        assert self.monitor.metrics.audio_packets_sent == 2
        assert self.monitor.metrics.audio_packets_received == 1
        assert self.monitor.metrics.bytes_sent == 1536  # 1024 + 512
        assert self.monitor.metrics.bytes_received == 2048
    
    def test_record_session_events(self):
        """Test session event recording"""
        # Start sessions
        self.monitor.record_session_event("start")
        self.monitor.record_session_event("start")
        
        # Check metrics
        assert self.monitor.metrics.total_sessions == 2
        assert self.monitor.metrics.active_sessions == 2
        
        # End session
        self.monitor.record_session_event("end", session_duration=120.5)
        
        # Check metrics
        assert self.monitor.metrics.active_sessions == 1
        assert self.monitor.metrics.session_duration_total == 120.5
    
    def test_record_errors(self):
        """Test error recording"""
        # Record different types of errors
        self.monitor.record_error("general")
        self.monitor.record_error("timeout")
        self.monitor.record_error("retry")
        self.monitor.record_error("general")
        
        # Check metrics
        assert self.monitor.metrics.error_count == 2  # Two general errors
        assert self.monitor.metrics.timeout_count == 1
        assert self.monitor.metrics.retry_count == 1
    
    def test_get_current_metrics(self):
        """Test current metrics retrieval"""
        # Add some test data
        self.monitor.record_audio_packet("sent", 1000)
        self.monitor.record_session_event("start")
        
        operation_id = self.monitor.start_operation("gemini_api")
        time.sleep(0.01)
        self.monitor.end_operation(operation_id, "gemini_api", True)
        
        metrics = self.monitor.get_current_metrics()
        
        # Check required fields
        required_fields = [
            "uptime_seconds", "uptime_formatted", "cpu_usage_percent",
            "memory_usage_mb", "audio_packets_sent", "audio_packets_received",
            "gemini_api_calls", "active_sessions", "total_sessions",
            "error_count", "error_rate", "operations_per_second"
        ]
        
        for field in required_fields:
            assert field in metrics
        
        # Check values
        assert metrics["audio_packets_sent"] == 1
        assert metrics["gemini_api_calls"] == 1
        assert metrics["active_sessions"] == 1
        assert metrics["uptime_seconds"] > 0
    
    def test_get_latency_stats(self):
        """Test latency statistics"""
        # Add some latency measurements
        operation_type = "test_operation"
        
        for i in range(5):
            operation_id = self.monitor.start_operation(operation_type)
            time.sleep(0.001 * (i + 1))  # Variable delay
            self.monitor.end_operation(operation_id, operation_type, True)
        
        stats = self.monitor.get_latency_stats(operation_type)
        
        # Check required fields
        assert "count" in stats
        assert "average" in stats
        assert "min" in stats
        assert "max" in stats
        assert "recent_average" in stats
        
        # Check values
        assert stats["count"] == 5
        assert stats["average"] > 0
        assert stats["min"] > 0
        assert stats["max"] > stats["min"]
    
    def test_get_latency_stats_empty(self):
        """Test latency statistics for non-existent operation"""
        stats = self.monitor.get_latency_stats("nonexistent")
        
        assert stats["count"] == 0
        assert stats["average"] == 0.0
        assert stats["min"] == 0.0
        assert stats["max"] == 0.0
    
    def test_get_performance_summary(self):
        """Test performance summary"""
        # Add some test data
        self.monitor.record_audio_packet("sent", 1000)
        self.monitor.record_session_event("start")
        
        summary = self.monitor.get_performance_summary()
        
        # Check required fields
        assert "timestamp" in summary
        assert "status" in summary
        assert "metrics" in summary
        assert "latency_stats" in summary
        assert "health_indicators" in summary
        
        # Check status
        assert summary["status"] in ["healthy", "degraded"]
        
        # Check health indicators
        health = summary["health_indicators"]
        assert "cpu_healthy" in health
        assert "memory_healthy" in health
        assert "error_rate_healthy" in health
        assert "latency_healthy" in health
    
    def test_reset_metrics(self):
        """Test metrics reset"""
        # Add some data
        self.monitor.record_audio_packet("sent", 1000)
        self.monitor.record_session_event("start")
        operation_id = self.monitor.start_operation("test")
        
        # Check data exists
        assert self.monitor.metrics.audio_packets_sent > 0
        assert len(self.monitor.pending_operations) > 0
        
        # Reset metrics
        self.monitor.reset_metrics()
        
        # Check data is reset
        assert self.monitor.metrics.audio_packets_sent == 0
        assert self.monitor.metrics.active_sessions == 0
        assert len(self.monitor.pending_operations) == 0
        assert len(self.monitor.metrics_history) == 0
    
    @patch('src.voice_assistant.utils.performance_monitor.psutil.Process')
    def test_system_metrics_update(self, mock_process):
        """Test system metrics update"""
        # Mock psutil
        mock_process_instance = MagicMock()
        mock_process_instance.cpu_percent.return_value = 45.5
        mock_process_instance.memory_info.return_value = MagicMock(rss=1024*1024*100)  # 100MB
        mock_process_instance.memory_percent.return_value = 25.0
        mock_process.return_value = mock_process_instance
        
        # Create monitor with mocked process
        monitor = PerformanceMonitor(enable_logging=False)
        monitor.process = mock_process_instance
        
        # Update system metrics
        asyncio.run(monitor._update_system_metrics())
        
        # Check metrics updated
        assert monitor.metrics.cpu_usage_percent == 45.5
        assert monitor.metrics.memory_usage_mb == 100.0
        assert monitor.metrics.memory_usage_percent == 25.0
        assert len(monitor.metrics_history) == 1
    
    def test_latency_history_size_limit(self):
        """Test latency history size limitation"""
        operation_type = "test_operation"
        
        # Add more than max size (50)
        for i in range(60):
            operation_id = self.monitor.start_operation(operation_type)
            self.monitor.end_operation(operation_id, operation_type, True)
        
        # Check size is limited
        assert len(self.monitor.latency_history[operation_type]) == 50
    
    def test_metrics_history_size_limit(self):
        """Test metrics history size limitation"""
        # Add more than max size (100)
        for i in range(110):
            asyncio.run(self.monitor._update_system_metrics())
        
        # Check size is limited
        assert len(self.monitor.metrics_history) == 100
    
    def test_global_instance(self):
        """Test global performance monitor instance"""
        assert performance_monitor is not None
        assert isinstance(performance_monitor, PerformanceMonitor)


@pytest.mark.integration
class TestPerformanceMonitorIntegration:
    """Integration tests for performance monitor"""
    
    @pytest.mark.asyncio
    async def test_full_monitoring_cycle(self):
        """Test complete monitoring cycle"""
        monitor = PerformanceMonitor(enable_logging=False, update_interval=0.1)
        
        try:
            # Start monitoring
            await monitor.start_monitoring()
            
            # Simulate some operations
            for i in range(3):
                # Start session
                monitor.record_session_event("start")
                
                # Simulate API call
                op_id = monitor.start_operation("gemini_api")
                await asyncio.sleep(0.01)
                monitor.end_operation(op_id, "gemini_api", True)
                
                # Simulate audio packets
                monitor.record_audio_packet("sent", 1024)
                monitor.record_audio_packet("received", 512)
                
                # End session
                monitor.record_session_event("end", session_duration=1.0)
            
            # Wait for monitoring updates
            await asyncio.sleep(0.3)
            
            # Get final metrics
            metrics = monitor.get_current_metrics()
            summary = monitor.get_performance_summary()
            
            # Verify results
            assert metrics["gemini_api_calls"] == 3
            assert metrics["audio_packets_sent"] == 3
            assert metrics["audio_packets_received"] == 3
            assert metrics["total_sessions"] == 3
            assert metrics["active_sessions"] == 0  # All ended
            
            assert summary["status"] in ["healthy", "degraded"]
            assert len(monitor.metrics_history) > 0
            
        finally:
            await monitor.stop_monitoring()


if __name__ == "__main__":
    pytest.main([__file__])