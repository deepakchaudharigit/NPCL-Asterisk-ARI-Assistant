"""
Performance monitoring and metrics collection for the Voice Assistant.
Provides comprehensive performance tracking, metrics collection, and optimization insights.
"""

import time
import psutil
import asyncio
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import logging
from contextlib import asynccontextmanager, contextmanager

from .constants import AppConstants, NetworkConstants
from .error_handling import ErrorHandler, ErrorContext


logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Individual performance metric."""
    name: str
    value: float
    unit: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tags: Dict[str, str] = field(default_factory=dict)
    description: str = ""


@dataclass
class SystemMetrics:
    """System-level performance metrics."""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_free_gb: float
    network_bytes_sent: int
    network_bytes_recv: int
    process_count: int
    thread_count: int
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ApplicationMetrics:
    """Application-level performance metrics."""
    active_sessions: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time: float
    p95_response_time: float
    p99_response_time: float
    audio_processing_time: float
    ai_processing_time: float
    cache_hit_rate: float
    error_rate: float
    timestamp: datetime = field(default_factory=datetime.utcnow)


class MetricsCollector:
    """Collects and aggregates performance metrics."""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.metrics_history: deque = deque(maxlen=max_history)
        self.counters: Dict[str, int] = defaultdict(int)
        self.timers: Dict[str, List[float]] = defaultdict(list)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.lock = threading.Lock()
        self.logger = logging.getLogger(f"{__name__}.MetricsCollector")
    
    def increment_counter(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        """Increment a counter metric."""
        with self.lock:
            key = self._make_key(name, tags)
            self.counters[key] += value
            self._record_metric(name, self.counters[key], "count", tags)
    
    def record_timer(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a timing metric."""
        with self.lock:
            key = self._make_key(name, tags)
            self.timers[key].append(value)
            
            # Keep only recent values
            if len(self.timers[key]) > 100:
                self.timers[key] = self.timers[key][-100:]
            
            self._record_metric(name, value, "seconds", tags)
    
    def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Set a gauge metric."""
        with self.lock:
            key = self._make_key(name, tags)
            self.gauges[key] = value
            self._record_metric(name, value, "gauge", tags)
    
    def record_histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a histogram metric."""
        with self.lock:
            key = self._make_key(name, tags)
            self.histograms[key].append(value)
            self._record_metric(name, value, "histogram", tags)
    
    def _make_key(self, name: str, tags: Optional[Dict[str, str]]) -> str:
        """Create a unique key for the metric."""
        if not tags:
            return name
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}[{tag_str}]"
    
    def _record_metric(self, name: str, value: float, unit: str, tags: Optional[Dict[str, str]]):
        """Record a metric in history."""
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            tags=tags or {},
            timestamp=datetime.utcnow()
        )
        self.metrics_history.append(metric)
    
    def get_counter(self, name: str, tags: Optional[Dict[str, str]] = None) -> int:
        """Get current counter value."""
        key = self._make_key(name, tags)
        return self.counters.get(key, 0)
    
    def get_timer_stats(self, name: str, tags: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """Get timer statistics."""
        key = self._make_key(name, tags)
        values = self.timers.get(key, [])
        
        if not values:
            return {"count": 0, "avg": 0, "min": 0, "max": 0, "p95": 0, "p99": 0}
        
        sorted_values = sorted(values)
        count = len(sorted_values)
        
        return {
            "count": count,
            "avg": sum(sorted_values) / count,
            "min": sorted_values[0],
            "max": sorted_values[-1],
            "p95": sorted_values[int(count * 0.95)] if count > 0 else 0,
            "p99": sorted_values[int(count * 0.99)] if count > 0 else 0
        }
    
    def get_gauge(self, name: str, tags: Optional[Dict[str, str]] = None) -> float:
        """Get current gauge value."""
        key = self._make_key(name, tags)
        return self.gauges.get(key, 0.0)
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all current metrics."""
        with self.lock:
            return {
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "timers": {k: self.get_timer_stats(k.split('[')[0], {}) for k in self.timers.keys()},
                "timestamp": datetime.utcnow().isoformat()
            }


class SystemMonitor:
    """Monitors system-level performance metrics."""
    
    def __init__(self, collection_interval: float = 10.0):
        self.collection_interval = collection_interval
        self.is_monitoring = False
        self.monitor_task: Optional[asyncio.Task] = None
        self.metrics_collector = MetricsCollector()
        self.logger = logging.getLogger(f"{__name__}.SystemMonitor")
    
    async def start_monitoring(self):
        """Start system monitoring."""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("System monitoring started")
    
    async def stop_monitoring(self):
        """Stop system monitoring."""
        self.is_monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        self.logger.info("System monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.is_monitoring:
            try:
                await self._collect_system_metrics()
                await asyncio.sleep(self.collection_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.collection_interval)
    
    async def _collect_system_metrics(self):
        """Collect system metrics."""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            self.metrics_collector.set_gauge("system.cpu.percent", cpu_percent)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            self.metrics_collector.set_gauge("system.memory.percent", memory.percent)
            self.metrics_collector.set_gauge("system.memory.used_mb", memory.used / 1024 / 1024)
            self.metrics_collector.set_gauge("system.memory.available_mb", memory.available / 1024 / 1024)
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self.metrics_collector.set_gauge("system.disk.percent", disk_percent)
            self.metrics_collector.set_gauge("system.disk.free_gb", disk.free / 1024 / 1024 / 1024)
            
            # Network metrics
            network = psutil.net_io_counters()
            self.metrics_collector.set_gauge("system.network.bytes_sent", network.bytes_sent)
            self.metrics_collector.set_gauge("system.network.bytes_recv", network.bytes_recv)
            
            # Process metrics
            process_count = len(psutil.pids())
            self.metrics_collector.set_gauge("system.processes.count", process_count)
            
            # Current process metrics
            current_process = psutil.Process()
            self.metrics_collector.set_gauge("process.cpu.percent", current_process.cpu_percent())
            self.metrics_collector.set_gauge("process.memory.percent", current_process.memory_percent())
            self.metrics_collector.set_gauge("process.threads.count", current_process.num_threads())
            
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")
    
    def get_current_metrics(self) -> SystemMetrics:
        """Get current system metrics."""
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            network = psutil.net_io_counters()
            
            return SystemMetrics(
                cpu_percent=psutil.cpu_percent(),
                memory_percent=memory.percent,
                memory_used_mb=memory.used / 1024 / 1024,
                memory_available_mb=memory.available / 1024 / 1024,
                disk_usage_percent=(disk.used / disk.total) * 100,
                disk_free_gb=disk.free / 1024 / 1024 / 1024,
                network_bytes_sent=network.bytes_sent,
                network_bytes_recv=network.bytes_recv,
                process_count=len(psutil.pids()),
                thread_count=psutil.Process().num_threads()
            )
        except Exception as e:
            self.logger.error(f"Error getting current metrics: {e}")
            return SystemMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)


class PerformanceTimer:
    """Context manager for timing operations."""
    
    def __init__(self, metrics_collector: MetricsCollector, name: str, tags: Optional[Dict[str, str]] = None):
        self.metrics_collector = metrics_collector
        self.name = name
        self.tags = tags
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        duration = self.end_time - self.start_time
        self.metrics_collector.record_timer(self.name, duration, self.tags)
    
    async def __aenter__(self):
        self.start_time = time.perf_counter()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        duration = self.end_time - self.start_time
        self.metrics_collector.record_timer(self.name, duration, self.tags)


class PerformanceMonitor:
    """Main performance monitoring system."""
    
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.system_monitor = SystemMonitor()
        self.error_handler = ErrorHandler()
        self.is_started = False
        self.logger = logging.getLogger(f"{__name__}.PerformanceMonitor")
    
    async def start(self):
        """Start performance monitoring."""
        if self.is_started:
            return
        
        await self.system_monitor.start_monitoring()
        self.is_started = True
        self.logger.info("Performance monitoring started")
    
    async def stop(self):
        """Stop performance monitoring."""
        if not self.is_started:
            return
        
        await self.system_monitor.stop_monitoring()
        self.is_started = False
        self.logger.info("Performance monitoring stopped")
    
    def timer(self, name: str, tags: Optional[Dict[str, str]] = None) -> PerformanceTimer:
        """Create a performance timer."""
        return PerformanceTimer(self.metrics_collector, name, tags)
    
    def increment(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        """Increment a counter."""
        self.metrics_collector.increment_counter(name, value, tags)
    
    def gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Set a gauge value."""
        self.metrics_collector.set_gauge(name, value, tags)
    
    def histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a histogram value."""
        self.metrics_collector.record_histogram(name, value, tags)
    
    def get_application_metrics(self) -> ApplicationMetrics:
        """Get current application metrics."""
        try:
            # Get metrics from collector
            total_requests = self.metrics_collector.get_counter("requests.total")
            successful_requests = self.metrics_collector.get_counter("requests.success")
            failed_requests = self.metrics_collector.get_counter("requests.error")
            
            # Calculate rates
            error_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0
            
            # Get timing stats
            response_time_stats = self.metrics_collector.get_timer_stats("response.time")
            audio_time_stats = self.metrics_collector.get_timer_stats("audio.processing")
            ai_time_stats = self.metrics_collector.get_timer_stats("ai.processing")
            
            # Get current values
            active_sessions = self.metrics_collector.get_gauge("sessions.active")
            cache_hit_rate = self.metrics_collector.get_gauge("cache.hit_rate")
            
            return ApplicationMetrics(
                active_sessions=int(active_sessions),
                total_requests=total_requests,
                successful_requests=successful_requests,
                failed_requests=failed_requests,
                average_response_time=response_time_stats["avg"],
                p95_response_time=response_time_stats["p95"],
                p99_response_time=response_time_stats["p99"],
                audio_processing_time=audio_time_stats["avg"],
                ai_processing_time=ai_time_stats["avg"],
                cache_hit_rate=cache_hit_rate,
                error_rate=error_rate
            )
        except Exception as e:
            self.logger.error(f"Error getting application metrics: {e}")
            return ApplicationMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        system_metrics = self.system_monitor.get_current_metrics()
        app_metrics = self.get_application_metrics()
        all_metrics = self.metrics_collector.get_all_metrics()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "system": {
                "cpu_percent": system_metrics.cpu_percent,
                "memory_percent": system_metrics.memory_percent,
                "memory_used_mb": system_metrics.memory_used_mb,
                "disk_usage_percent": system_metrics.disk_usage_percent,
                "process_count": system_metrics.process_count,
                "thread_count": system_metrics.thread_count
            },
            "application": {
                "active_sessions": app_metrics.active_sessions,
                "total_requests": app_metrics.total_requests,
                "error_rate": app_metrics.error_rate,
                "avg_response_time": app_metrics.average_response_time,
                "p95_response_time": app_metrics.p95_response_time,
                "cache_hit_rate": app_metrics.cache_hit_rate
            },
            "detailed_metrics": all_metrics
        }
    
    def export_prometheus_metrics(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        
        # System metrics
        system_metrics = self.system_monitor.get_current_metrics()
        lines.extend([
            f"# HELP system_cpu_percent CPU usage percentage",
            f"# TYPE system_cpu_percent gauge",
            f"system_cpu_percent {system_metrics.cpu_percent}",
            f"# HELP system_memory_percent Memory usage percentage",
            f"# TYPE system_memory_percent gauge",
            f"system_memory_percent {system_metrics.memory_percent}",
        ])
        
        # Application metrics
        app_metrics = self.get_application_metrics()
        lines.extend([
            f"# HELP voice_assistant_requests_total Total number of requests",
            f"# TYPE voice_assistant_requests_total counter",
            f"voice_assistant_requests_total {app_metrics.total_requests}",
            f"# HELP voice_assistant_active_sessions Current active sessions",
            f"# TYPE voice_assistant_active_sessions gauge",
            f"voice_assistant_active_sessions {app_metrics.active_sessions}",
            f"# HELP voice_assistant_response_time_seconds Response time in seconds",
            f"# TYPE voice_assistant_response_time_seconds histogram",
            f"voice_assistant_response_time_seconds_sum {app_metrics.average_response_time}",
            f"voice_assistant_response_time_seconds_count {app_metrics.total_requests}",
        ])
        
        return "\n".join(lines)


# Global performance monitor instance
global_performance_monitor = PerformanceMonitor()


# Decorator for automatic performance monitoring
def monitor_performance(name: str, tags: Optional[Dict[str, str]] = None):
    """Decorator for automatic performance monitoring."""
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                async with global_performance_monitor.timer(name, tags):
                    try:
                        result = await func(*args, **kwargs)
                        global_performance_monitor.increment(f"{name}.success", tags=tags)
                        return result
                    except Exception as e:
                        global_performance_monitor.increment(f"{name}.error", tags=tags)
                        raise
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                with global_performance_monitor.timer(name, tags):
                    try:
                        result = func(*args, **kwargs)
                        global_performance_monitor.increment(f"{name}.success", tags=tags)
                        return result
                    except Exception as e:
                        global_performance_monitor.increment(f"{name}.error", tags=tags)
                        raise
            return sync_wrapper
    return decorator


# Context managers for performance monitoring
@asynccontextmanager
async def monitor_async_operation(name: str, tags: Optional[Dict[str, str]] = None):
    """Async context manager for monitoring operations."""
    async with global_performance_monitor.timer(name, tags):
        try:
            yield
            global_performance_monitor.increment(f"{name}.success", tags=tags)
        except Exception as e:
            global_performance_monitor.increment(f"{name}.error", tags=tags)
            raise


@contextmanager
def monitor_operation(name: str, tags: Optional[Dict[str, str]] = None):
    """Sync context manager for monitoring operations."""
    with global_performance_monitor.timer(name, tags):
        try:
            yield
            global_performance_monitor.increment(f"{name}.success", tags=tags)
        except Exception as e:
            global_performance_monitor.increment(f"{name}.error", tags=tags)
            raise