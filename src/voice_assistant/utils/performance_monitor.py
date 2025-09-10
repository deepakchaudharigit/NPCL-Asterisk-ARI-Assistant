"""
Performance Monitoring System for Voice Assistant.
Tracks metrics, latency, and system performance in real-time.
"""

import time
import psutil
import logging
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict, deque
import threading
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics data structure"""
    # Audio metrics
    audio_packets_sent: int = 0
    audio_packets_received: int = 0
    total_audio_latency: float = 0.0
    latency_measurements: int = 0
    
    # Aggregate counters
    operations_count_total: int = 0
    
    # System metrics
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0
    memory_usage_percent: float = 0.0
    
    # Network metrics
    bytes_sent: int = 0
    bytes_received: int = 0
    
    # Processing metrics
    gemini_api_calls: int = 0
    gemini_api_latency: float = 0.0
    speech_recognition_calls: int = 0
    speech_recognition_latency: float = 0.0
    tts_calls: int = 0
    tts_latency: float = 0.0
    function_calls: int = 0  # Added to track function calling system usage
    
    # Session metrics
    active_sessions: int = 0
    total_sessions: int = 0
    session_duration_total: float = 0.0
    
    # Error metrics
    error_count: int = 0
    timeout_count: int = 0
    retry_count: int = 0
    
    # Timestamps
    start_time: float = field(default_factory=time.time)
    last_update: float = field(default_factory=time.time)


class PerformanceMonitor:
    """Real-time performance monitoring system"""
    
    def __init__(self, enable_logging: bool = True, update_interval: float = 5.0):
        self.enable_logging = enable_logging
        self.update_interval = update_interval
        
        # Metrics storage
        self.metrics = PerformanceMetrics()
        self.metrics_history: deque = deque(maxlen=100)  # Keep last 100 measurements
        
        # Latency tracking
        self.latency_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=50))
        self.pending_operations: Dict[str, float] = {}  # operation_id -> start_time
        
        # System monitoring
        self.process = psutil.Process()
        self.monitoring_active = False
        self.monitor_task: Optional[asyncio.Task] = None
        
        # Thread safety
        self._lock = threading.Lock()
        
        logger.info("Performance Monitor initialized")
    
    async def start_monitoring(self):
        """Start continuous performance monitoring"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Performance monitoring started")
    
    async def stop_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring_active = False
        
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Performance monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        try:
            while self.monitoring_active:
                await self._update_system_metrics()
                await self._log_performance_summary()
                await asyncio.sleep(self.update_interval)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
    
    async def _update_system_metrics(self):
        """Update system performance metrics"""
        try:
            with self._lock:
                # CPU and memory usage
                self.metrics.cpu_usage_percent = self.process.cpu_percent()
                memory_info = self.process.memory_info()
                self.metrics.memory_usage_mb = memory_info.rss / 1024 / 1024
                self.metrics.memory_usage_percent = self.process.memory_percent()
                
                # Update timestamp
                self.metrics.last_update = time.time()
                
                # Store in history
                self.metrics_history.append({
                    "timestamp": self.metrics.last_update,
                    "cpu_percent": self.metrics.cpu_usage_percent,
                    "memory_mb": self.metrics.memory_usage_mb,
                    "memory_percent": self.metrics.memory_usage_percent,
                    "active_sessions": self.metrics.active_sessions,
                    "audio_packets_sent": self.metrics.audio_packets_sent,
                    "audio_packets_received": self.metrics.audio_packets_received
                })
                
        except Exception as e:
            logger.error(f"Error updating system metrics: {e}")
    
    def start_operation(self, operation_type: str, operation_id: str = None) -> str:
        """
        Start tracking an operation.
        
        Args:
            operation_type: Type of operation (e.g., 'gemini_api', 'speech_recognition')
            operation_id: Optional operation ID, will be generated if not provided
            
        Returns:
            Operation ID for tracking
        """
        if operation_id is None:
            operation_id = f"{operation_type}_{int(time.time() * 1000000)}"
        
        with self._lock:
            self.pending_operations[operation_id] = time.time()
        
        return operation_id
    
    def end_operation(self, operation_id: str, operation_type: str, success: bool = True):
        """
        End tracking an operation and record metrics.
        
        Args:
            operation_id: Operation ID from start_operation
            operation_type: Type of operation
            success: Whether the operation was successful
        """
        with self._lock:
            start_time = self.pending_operations.pop(operation_id, None)
            
            if start_time is None:
                logger.warning(f"Operation {operation_id} not found in pending operations")
                return
            
            latency = time.time() - start_time
            
            # Record latency
            self.latency_history[operation_type].append(latency)
            
            # Increment aggregate operations counter
            self.metrics.operations_count_total += 1
            
            # Update specific metrics
            if operation_type == "gemini_api":
                self.metrics.gemini_api_calls += 1
                self.metrics.gemini_api_latency += latency
            elif operation_type == "speech_recognition":
                self.metrics.speech_recognition_calls += 1
                self.metrics.speech_recognition_latency += latency
            elif operation_type == "tts":
                self.metrics.tts_calls += 1
                self.metrics.tts_latency += latency
            elif operation_type == "audio_processing":
                self.metrics.latency_measurements += 1
                self.metrics.total_audio_latency += latency
            elif operation_type == "function_call":
                self.metrics.function_calls += 1
            
            # Record errors
            if not success:
                self.metrics.error_count += 1
    
    def record_audio_packet(self, direction: str, size: int = 0):
        """
        Record audio packet transmission.
        
        Args:
            direction: 'sent' or 'received'
            size: Packet size in bytes
        """
        with self._lock:
            if direction == "sent":
                self.metrics.audio_packets_sent += 1
                self.metrics.bytes_sent += size
            elif direction == "received":
                self.metrics.audio_packets_received += 1
                self.metrics.bytes_received += size
    
    def record_session_event(self, event_type: str, session_duration: float = 0):
        """
        Record session-related events.
        
        Args:
            event_type: 'start', 'end', 'active_count'
            session_duration: Duration for ended sessions
        """
        with self._lock:
            if event_type == "start":
                self.metrics.total_sessions += 1
                self.metrics.active_sessions += 1
            elif event_type == "end":
                self.metrics.active_sessions = max(0, self.metrics.active_sessions - 1)
                self.metrics.session_duration_total += session_duration
            elif event_type == "active_count":
                # For manual active session count updates
                pass
    
    def record_error(self, error_type: str = "general"):
        """Record an error occurrence"""
        with self._lock:
            if error_type == "timeout":
                self.metrics.timeout_count += 1
            elif error_type == "retry":
                self.metrics.retry_count += 1
            else:
                self.metrics.error_count += 1
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        with self._lock:
            uptime = time.time() - self.metrics.start_time
            
            return {
                "uptime_seconds": uptime,
                "uptime_formatted": str(timedelta(seconds=int(uptime))),
                
                # System metrics
                "cpu_usage_percent": self.metrics.cpu_usage_percent,
                "memory_usage_mb": round(self.metrics.memory_usage_mb, 2),
                "memory_usage_percent": round(self.metrics.memory_usage_percent, 2),
                
                # Audio metrics
                "audio_packets_sent": self.metrics.audio_packets_sent,
                "audio_packets_received": self.metrics.audio_packets_received,
                "average_audio_latency": (
                    self.metrics.total_audio_latency / max(1, self.metrics.latency_measurements)
                ),
                
                # API metrics
                "gemini_api_calls": self.metrics.gemini_api_calls,
                "average_gemini_latency": (
                    self.metrics.gemini_api_latency / max(1, self.metrics.gemini_api_calls)
                ),
                "speech_recognition_calls": self.metrics.speech_recognition_calls,
                "average_speech_recognition_latency": (
                    self.metrics.speech_recognition_latency / max(1, self.metrics.speech_recognition_calls)
                ),
                "tts_calls": self.metrics.tts_calls,
                "average_tts_latency": (
                    self.metrics.tts_latency / max(1, self.metrics.tts_calls)
                ),
                
                # Session metrics
                "active_sessions": self.metrics.active_sessions,
                "total_sessions": self.metrics.total_sessions,
                "average_session_duration": (
                    self.metrics.session_duration_total / max(1, self.metrics.total_sessions)
                ),
                
                # Network metrics
                "bytes_sent": self.metrics.bytes_sent,
                "bytes_received": self.metrics.bytes_received,
                "total_bytes": self.metrics.bytes_sent + self.metrics.bytes_received,
                
                # Error metrics
                "error_count": self.metrics.error_count,
                "timeout_count": self.metrics.timeout_count,
                "retry_count": self.metrics.retry_count,
                "error_rate": (
                    self.metrics.error_count / max(1, self.metrics.total_sessions) * 100
                ),
                
                # Performance indicators
                "operations_per_second": (
                    max(
                        self.metrics.operations_count_total,
                        (self.metrics.gemini_api_calls + self.metrics.speech_recognition_calls + 
                         self.metrics.tts_calls + self.metrics.function_calls + self.metrics.latency_measurements)
                    ) / max(1, uptime)
                ),
                "audio_packets_per_second": (
                    (self.metrics.audio_packets_sent + self.metrics.audio_packets_received) / max(1, uptime)
                )
            }
    
    def get_latency_stats(self, operation_type: str) -> Dict[str, float]:
        """Get latency statistics for a specific operation type"""
        with self._lock:
            latencies = list(self.latency_history[operation_type])
            
            if not latencies:
                return {"count": 0, "average": 0.0, "min": 0.0, "max": 0.0}
            
            return {
                "count": len(latencies),
                "average": sum(latencies) / len(latencies),
                "min": min(latencies),
                "max": max(latencies),
                "recent_average": sum(latencies[-10:]) / min(10, len(latencies))
            }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        current_metrics = self.get_current_metrics()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "healthy" if current_metrics["error_rate"] < 5 else "degraded",
            "metrics": current_metrics,
            "latency_stats": {
                "gemini_api": self.get_latency_stats("gemini_api"),
                "speech_recognition": self.get_latency_stats("speech_recognition"),
                "tts": self.get_latency_stats("tts"),
                "audio_processing": self.get_latency_stats("audio_processing")
            },
            "health_indicators": {
                "cpu_healthy": current_metrics["cpu_usage_percent"] < 80,
                "memory_healthy": current_metrics["memory_usage_percent"] < 80,
                "error_rate_healthy": current_metrics["error_rate"] < 5,
                "latency_healthy": current_metrics["average_gemini_latency"] < 2.0
            }
        }
    
    async def _log_performance_summary(self):
        """Log performance summary if logging is enabled"""
        if not self.enable_logging:
            return
        
        try:
            summary = self.get_performance_summary()
            metrics = summary["metrics"]
            
            logger.info(
                f"Performance Summary - "
                f"CPU: {metrics['cpu_usage_percent']:.1f}% | "
                f"Memory: {metrics['memory_usage_mb']:.1f}MB | "
                f"Sessions: {metrics['active_sessions']} active, {metrics['total_sessions']} total | "
                f"Audio: {metrics['audio_packets_sent']} sent, {metrics['audio_packets_received']} received | "
                f"Errors: {metrics['error_count']} ({metrics['error_rate']:.1f}%)"
            )
            
        except Exception as e:
            logger.error(f"Error logging performance summary: {e}")
    
    def reset_metrics(self):
        """Reset all metrics"""
        with self._lock:
            self.metrics = PerformanceMetrics()
            self.metrics_history.clear()
            self.latency_history.clear()
            self.pending_operations.clear()
        
        logger.info("Performance metrics reset")


# Global instance
performance_monitor = PerformanceMonitor()