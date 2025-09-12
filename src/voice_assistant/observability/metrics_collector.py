"""
Metrics Collection and Prometheus Integration
Collects and exports application metrics for monitoring
"""

import time
import asyncio
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
from abc import ABC, abstractmethod
import threading
import logging

# Prometheus client imports (optional)
try:
    from prometheus_client import Counter, Histogram, Gauge, Summary, CollectorRegistry, generate_latest
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Create dummy classes for type hints when prometheus is not available
    class CollectorRegistry:
        pass
    class Counter:
        pass
    class Histogram:
        pass
    class Gauge:
        pass
    class Summary:
        pass

logger = logging.getLogger(__name__)

@dataclass
class MetricValue:
    """Represents a metric value with metadata"""
    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    metric_type: str = "gauge"  # gauge, counter, histogram, summary

class MetricsCollector(ABC):
    """Abstract base class for metrics collectors"""
    
    @abstractmethod
    def increment_counter(self, name: str, value: float = 1.0, labels: Dict[str, str] = None):
        """Increment a counter metric"""
        pass
    
    @abstractmethod
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge metric value"""
        pass
    
    @abstractmethod
    def record_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a value in a histogram"""
        pass
    
    @abstractmethod
    def record_summary(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a value in a summary"""
        pass
    
    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics"""
        pass

class InMemoryMetricsCollector(MetricsCollector):
    """In-memory metrics collector for development and testing"""
    
    def __init__(self):
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.summaries: Dict[str, List[float]] = defaultdict(list)
        self.labels_data: Dict[str, Dict[str, str]] = {}
        self._lock = threading.Lock()
    
    def increment_counter(self, name: str, value: float = 1.0, labels: Dict[str, str] = None):
        """Increment a counter metric"""
        with self._lock:
            key = self._make_key(name, labels)
            self.counters[key] += value
            if labels:
                self.labels_data[key] = labels
    
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge metric value"""
        with self._lock:
            key = self._make_key(name, labels)
            self.gauges[key] = value
            if labels:
                self.labels_data[key] = labels
    
    def record_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a value in a histogram"""
        with self._lock:
            key = self._make_key(name, labels)
            self.histograms[key].append(value)
            if labels:
                self.labels_data[key] = labels
            
            # Keep only last 1000 values to prevent memory issues
            if len(self.histograms[key]) > 1000:
                self.histograms[key] = self.histograms[key][-1000:]
    
    def record_summary(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a value in a summary"""
        with self._lock:
            key = self._make_key(name, labels)
            self.summaries[key].append(value)
            if labels:
                self.labels_data[key] = labels
            
            # Keep only last 1000 values
            if len(self.summaries[key]) > 1000:
                self.summaries[key] = self.summaries[key][-1000:]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics"""
        with self._lock:
            metrics = {
                'counters': dict(self.counters),
                'gauges': dict(self.gauges),
                'histograms': {k: self._histogram_stats(v) for k, v in self.histograms.items()},
                'summaries': {k: self._summary_stats(v) for k, v in self.summaries.items()},
                'labels': dict(self.labels_data),
                'timestamp': time.time()
            }
        return metrics
    
    def _make_key(self, name: str, labels: Dict[str, str] = None) -> str:
        """Create a unique key for metric with labels"""
        if not labels:
            return name
        
        label_str = ','.join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
    
    def _histogram_stats(self, values: List[float]) -> Dict[str, float]:
        """Calculate histogram statistics"""
        if not values:
            return {'count': 0, 'sum': 0, 'avg': 0, 'min': 0, 'max': 0}
        
        sorted_values = sorted(values)
        count = len(values)
        
        return {
            'count': count,
            'sum': sum(values),
            'avg': sum(values) / count,
            'min': min(values),
            'max': max(values),
            'p50': sorted_values[int(count * 0.5)],
            'p90': sorted_values[int(count * 0.9)],
            'p95': sorted_values[int(count * 0.95)],
            'p99': sorted_values[int(count * 0.99)]
        }
    
    def _summary_stats(self, values: List[float]) -> Dict[str, float]:
        """Calculate summary statistics"""
        return self._histogram_stats(values)

class PrometheusMetrics(MetricsCollector):
    """Prometheus metrics collector"""
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        if not PROMETHEUS_AVAILABLE:
            raise ImportError("prometheus_client is required for PrometheusMetrics")
        
        self.registry = registry or CollectorRegistry()
        self.counters: Dict[str, Counter] = {}
        self.gauges: Dict[str, Gauge] = {}
        self.histograms: Dict[str, Histogram] = {}
        self.summaries: Dict[str, Summary] = {}
        self._lock = threading.Lock()
        
        # Default buckets for histograms
        self.default_buckets = [0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0]
    
    def increment_counter(self, name: str, value: float = 1.0, labels: Dict[str, str] = None):
        """Increment a counter metric"""
        counter = self._get_or_create_counter(name, labels)
        if labels:
            counter.labels(**labels).inc(value)
        else:
            counter.inc(value)
    
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge metric value"""
        gauge = self._get_or_create_gauge(name, labels)
        if labels:
            gauge.labels(**labels).set(value)
        else:
            gauge.set(value)
    
    def record_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a value in a histogram"""
        histogram = self._get_or_create_histogram(name, labels)
        if labels:
            histogram.labels(**labels).observe(value)
        else:
            histogram.observe(value)
    
    def record_summary(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a value in a summary"""
        summary = self._get_or_create_summary(name, labels)
        if labels:
            summary.labels(**labels).observe(value)
        else:
            summary.observe(value)
    
    def get_metrics(self) -> str:
        """Get metrics in Prometheus format"""
        return generate_latest(self.registry).decode('utf-8')
    
    def _get_or_create_counter(self, name: str, labels: Dict[str, str] = None) -> Counter:
        """Get or create a counter metric"""
        with self._lock:
            if name not in self.counters:
                label_names = list(labels.keys()) if labels else []
                self.counters[name] = Counter(
                    name, f"Counter metric: {name}",
                    labelnames=label_names,
                    registry=self.registry
                )
            return self.counters[name]
    
    def _get_or_create_gauge(self, name: str, labels: Dict[str, str] = None) -> Gauge:
        """Get or create a gauge metric"""
        with self._lock:
            if name not in self.gauges:
                label_names = list(labels.keys()) if labels else []
                self.gauges[name] = Gauge(
                    name, f"Gauge metric: {name}",
                    labelnames=label_names,
                    registry=self.registry
                )
            return self.gauges[name]
    
    def _get_or_create_histogram(self, name: str, labels: Dict[str, str] = None) -> Histogram:
        """Get or create a histogram metric"""
        with self._lock:
            if name not in self.histograms:
                label_names = list(labels.keys()) if labels else []
                self.histograms[name] = Histogram(
                    name, f"Histogram metric: {name}",
                    labelnames=label_names,
                    buckets=self.default_buckets,
                    registry=self.registry
                )
            return self.histograms[name]
    
    def _get_or_create_summary(self, name: str, labels: Dict[str, str] = None) -> Summary:
        """Get or create a summary metric"""
        with self._lock:
            if name not in self.summaries:
                label_names = list(labels.keys()) if labels else []
                self.summaries[name] = Summary(
                    name, f"Summary metric: {name}",
                    labelnames=label_names,
                    registry=self.registry
                )
            return self.summaries[name]

class ApplicationMetrics:
    """High-level application metrics collector"""
    
    def __init__(self, collector: MetricsCollector):
        self.collector = collector
        self.start_time = time.time()
    
    # Voice Assistant specific metrics
    def record_voice_session_start(self, user_id: str = None):
        """Record voice session start"""
        labels = {'user_id': user_id} if user_id else {}
        self.collector.increment_counter('voice_sessions_started_total', labels=labels)
    
    def record_voice_session_end(self, user_id: str = None, duration: float = None):
        """Record voice session end"""
        labels = {'user_id': user_id} if user_id else {}
        self.collector.increment_counter('voice_sessions_ended_total', labels=labels)
        
        if duration is not None:
            self.collector.record_histogram('voice_session_duration_seconds', duration, labels=labels)
    
    def record_audio_processing_time(self, processing_time: float, stage: str = None):
        """Record audio processing time"""
        labels = {'stage': stage} if stage else {}
        self.collector.record_histogram('audio_processing_duration_seconds', processing_time, labels=labels)
    
    def record_ai_response_time(self, response_time: float, model: str = None):
        """Record AI response time"""
        labels = {'model': model} if model else {}
        self.collector.record_histogram('ai_response_duration_seconds', response_time, labels=labels)
    
    def record_api_request(self, endpoint: str, method: str, status_code: int, duration: float):
        """Record API request metrics"""
        labels = {
            'endpoint': endpoint,
            'method': method,
            'status_code': str(status_code)
        }
        
        self.collector.increment_counter('api_requests_total', labels=labels)
        self.collector.record_histogram('api_request_duration_seconds', duration, labels=labels)
    
    def record_error(self, error_type: str, component: str = None):
        """Record error occurrence"""
        labels = {
            'error_type': error_type,
            'component': component or 'unknown'
        }
        self.collector.increment_counter('errors_total', labels=labels)
    
    def set_active_sessions(self, count: int):
        """Set number of active sessions"""
        self.collector.set_gauge('active_sessions', count)
    
    def set_system_resource_usage(self, cpu_percent: float, memory_percent: float, 
                                 disk_percent: float = None):
        """Set system resource usage"""
        self.collector.set_gauge('cpu_usage_percent', cpu_percent)
        self.collector.set_gauge('memory_usage_percent', memory_percent)
        
        if disk_percent is not None:
            self.collector.set_gauge('disk_usage_percent', disk_percent)
    
    def record_websocket_connection(self, event: str, connection_type: str = None):
        """Record WebSocket connection events"""
        labels = {
            'event': event,  # connected, disconnected, error
            'type': connection_type or 'unknown'
        }
        self.collector.increment_counter('websocket_connections_total', labels=labels)
    
    def record_rate_limit_hit(self, endpoint: str, user_id: str = None):
        """Record rate limit hit"""
        labels = {
            'endpoint': endpoint,
            'user_id': user_id or 'anonymous'
        }
        self.collector.increment_counter('rate_limits_hit_total', labels=labels)
    
    def record_security_event(self, event_type: str, severity: str = 'medium'):
        """Record security event"""
        labels = {
            'event_type': event_type,
            'severity': severity
        }
        self.collector.increment_counter('security_events_total', labels=labels)
    
    def get_uptime(self) -> float:
        """Get application uptime in seconds"""
        return time.time() - self.start_time

class MetricsServer:
    """HTTP server for exposing metrics"""
    
    def __init__(self, metrics_collector: MetricsCollector, port: int = 9090):
        self.metrics_collector = metrics_collector
        self.port = port
        self.server = None
    
    async def start(self):
        """Start metrics server"""
        try:
            from aiohttp import web, web_runner
            
            app = web.Application()
            app.router.add_get('/metrics', self._metrics_handler)
            app.router.add_get('/health', self._health_handler)
            
            runner = web_runner.AppRunner(app)
            await runner.setup()
            
            site = web_runner.TCPSite(runner, '0.0.0.0', self.port)
            await site.start()
            
            self.server = runner
            logger.info(f"Metrics server started on port {self.port}")
            
        except ImportError:
            logger.warning("aiohttp not available, metrics server not started")
        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}")
    
    async def stop(self):
        """Stop metrics server"""
        if self.server:
            await self.server.cleanup()
            self.server = None
    
    async def _metrics_handler(self, request):
        """Handle metrics endpoint"""
        try:
            if isinstance(self.metrics_collector, PrometheusMetrics):
                metrics_data = self.metrics_collector.get_metrics()
                return web.Response(text=metrics_data, content_type='text/plain')
            else:
                metrics_data = self.metrics_collector.get_metrics()
                return web.json_response(metrics_data)
        except Exception as e:
            logger.error(f"Error serving metrics: {e}")
            return web.Response(status=500, text="Internal server error")
    
    async def _health_handler(self, request):
        """Handle health check endpoint"""
        return web.json_response({
            'status': 'healthy',
            'timestamp': time.time()
        })

# Context manager for timing operations
class MetricsTimer:
    """Context manager for timing operations"""
    
    def __init__(self, metrics: ApplicationMetrics, metric_name: str, labels: Dict[str, str] = None):
        self.metrics = metrics
        self.metric_name = metric_name
        self.labels = labels
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            
            if self.metric_name == 'audio_processing':
                self.metrics.record_audio_processing_time(duration, self.labels.get('stage') if self.labels else None)
            elif self.metric_name == 'ai_response':
                self.metrics.record_ai_response_time(duration, self.labels.get('model') if self.labels else None)
            else:
                # Generic histogram recording
                self.metrics.collector.record_histogram(f"{self.metric_name}_duration_seconds", duration, self.labels)