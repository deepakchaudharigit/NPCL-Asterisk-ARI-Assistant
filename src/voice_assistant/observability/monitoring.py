"""
Comprehensive monitoring and observability system for production deployment.
Provides metrics collection, health checks, alerting, and performance monitoring.
"""

import asyncio
import logging
import time
import psutil
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json

from ..utils.dependency_manager import safe_import
from ..utils.error_handler import get_error_handler, ErrorSeverity

# Optional imports for monitoring
prometheus_client = safe_import("prometheus_client", "prometheus_client", required=False)
aiohttp = safe_import("aiohttp", "aiohttp", required=False)

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class MetricType(Enum):
    """Metric types"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class HealthCheck:
    """Health check definition"""
    name: str
    check_function: Callable[[], bool]
    timeout: float = 5.0
    critical: bool = False
    description: str = ""
    
    def __post_init__(self):
        if not self.description:
            self.description = f"Health check for {self.name}"


@dataclass
class Metric:
    """Metric definition"""
    name: str
    metric_type: MetricType
    description: str
    labels: List[str] = field(default_factory=list)
    value: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Alert:
    """Alert definition"""
    name: str
    condition: Callable[[Dict[str, Any]], bool]
    severity: ErrorSeverity
    message_template: str
    cooldown_minutes: int = 5
    last_triggered: Optional[datetime] = None


class MonitoringSystem:
    """Comprehensive monitoring and observability system"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.is_running = False
        
        # Health checks
        self.health_checks: Dict[str, HealthCheck] = {}
        self.health_status = HealthStatus.UNKNOWN
        self.last_health_check = None
        
        # Metrics
        self.metrics: Dict[str, Metric] = {}
        self.metric_history: Dict[str, List[float]] = {}
        self.prometheus_metrics = {}
        
        # Alerts
        self.alerts: Dict[str, Alert] = {}
        self.alert_callbacks: List[Callable[[str, str, ErrorSeverity], None]] = []
        
        # Performance tracking
        self.performance_data = {
            "cpu_usage": [],
            "memory_usage": [],
            "disk_usage": [],
            "network_io": [],
            "call_metrics": {
                "active_calls": 0,
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "average_duration": 0.0
            },
            "audio_metrics": {
                "processing_latency": [],
                "quality_score": [],
                "error_rate": 0.0
            },
            "ai_metrics": {
                "response_time": [],
                "token_usage": 0,
                "error_rate": 0.0
            }
        }
        
        # Monitoring thread
        self.monitoring_thread = None
        self.monitoring_interval = self.config.get("monitoring_interval", 30)
        
        # Initialize Prometheus metrics if available
        self._init_prometheus_metrics()
        
        # Register default health checks and alerts
        self._register_default_health_checks()
        self._register_default_alerts()
        
        logger.info("Monitoring system initialized")
    
    def _init_prometheus_metrics(self):
        """Initialize Prometheus metrics if available"""
        if not prometheus_client:
            logger.warning("Prometheus client not available - metrics will be stored locally only")
            return
        
        try:
            # System metrics
            self.prometheus_metrics.update({
                "cpu_usage": prometheus_client.Gauge(
                    "voice_assistant_cpu_usage_percent",
                    "CPU usage percentage"
                ),
                "memory_usage": prometheus_client.Gauge(
                    "voice_assistant_memory_usage_percent", 
                    "Memory usage percentage"
                ),
                "active_calls": prometheus_client.Gauge(
                    "voice_assistant_active_calls",
                    "Number of active calls"
                ),
                "total_calls": prometheus_client.Counter(
                    "voice_assistant_total_calls",
                    "Total number of calls"
                ),
                "call_duration": prometheus_client.Histogram(
                    "voice_assistant_call_duration_seconds",
                    "Call duration in seconds",
                    buckets=[1, 5, 10, 30, 60, 300, 600, 1800]
                ),
                "audio_processing_latency": prometheus_client.Histogram(
                    "voice_assistant_audio_processing_latency_seconds",
                    "Audio processing latency in seconds",
                    buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0]
                ),
                "ai_response_time": prometheus_client.Histogram(
                    "voice_assistant_ai_response_time_seconds",
                    "AI response time in seconds",
                    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
                ),
                "error_rate": prometheus_client.Gauge(
                    "voice_assistant_error_rate_percent",
                    "Error rate percentage"
                ),
                "health_status": prometheus_client.Enum(
                    "voice_assistant_health_status",
                    "Overall health status",
                    states=[status.value for status in HealthStatus]
                )
            })
            
            logger.info("Prometheus metrics initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Prometheus metrics: {e}")
    
    def _register_default_health_checks(self):
        """Register default health checks"""
        
        def check_cpu_usage():
            """Check CPU usage"""
            cpu_percent = psutil.cpu_percent(interval=1)
            return cpu_percent < 90.0
        
        def check_memory_usage():
            """Check memory usage"""
            memory = psutil.virtual_memory()
            return memory.percent < 90.0
        
        def check_disk_space():
            """Check disk space"""
            disk = psutil.disk_usage('/')
            return (disk.free / disk.total) > 0.1  # At least 10% free
        
        def check_error_handler():
            """Check error handler status"""
            error_handler = get_error_handler()
            stats = error_handler.get_error_statistics()
            # Check if error rate is acceptable
            return stats.get("recent_errors_count", 0) < 10
        
        # Register health checks
        self.register_health_check("cpu_usage", check_cpu_usage, critical=True, 
                                 description="CPU usage below 90%")
        self.register_health_check("memory_usage", check_memory_usage, critical=True,
                                 description="Memory usage below 90%")
        self.register_health_check("disk_space", check_disk_space, critical=True,
                                 description="Disk space above 10%")
        self.register_health_check("error_handler", check_error_handler, critical=False,
                                 description="Error rate within acceptable limits")
    
    def _register_default_alerts(self):
        """Register default alerts"""
        
        def high_cpu_alert(metrics):
            cpu_usage = metrics.get("cpu_usage", 0)
            return cpu_usage > 80.0
        
        def high_memory_alert(metrics):
            memory_usage = metrics.get("memory_usage", 0)
            return memory_usage > 85.0
        
        def high_error_rate_alert(metrics):
            error_rate = metrics.get("error_rate", 0)
            return error_rate > 5.0
        
        def slow_response_alert(metrics):
            avg_response_time = metrics.get("average_response_time", 0)
            return avg_response_time > 2.0
        
        # Register alerts
        self.register_alert("high_cpu", high_cpu_alert, ErrorSeverity.HIGH,
                          "High CPU usage detected: {cpu_usage:.1f}%")
        self.register_alert("high_memory", high_memory_alert, ErrorSeverity.HIGH,
                          "High memory usage detected: {memory_usage:.1f}%")
        self.register_alert("high_error_rate", high_error_rate_alert, ErrorSeverity.MEDIUM,
                          "High error rate detected: {error_rate:.1f}%")
        self.register_alert("slow_response", slow_response_alert, ErrorSeverity.MEDIUM,
                          "Slow response time detected: {average_response_time:.2f}s")
    
    def start_monitoring(self):
        """Start the monitoring system"""
        if self.is_running:
            logger.warning("Monitoring system is already running")
            return
        
        self.is_running = True
        
        # Start monitoring thread
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="MonitoringThread"
        )
        self.monitoring_thread.start()
        
        logger.info("Monitoring system started")
    
    def stop_monitoring(self):
        """Stop the monitoring system"""
        self.is_running = False
        
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5)
        
        logger.info("Monitoring system stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                # Collect system metrics
                self._collect_system_metrics()
                
                # Run health checks
                self._run_health_checks()
                
                # Check alerts
                self._check_alerts()
                
                # Update Prometheus metrics
                self._update_prometheus_metrics()
                
                # Sleep until next interval
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)  # Short sleep on error
    
    def _collect_system_metrics(self):
        """Collect system performance metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self._record_metric("cpu_usage", cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            self._record_metric("memory_usage", memory.percent)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self._record_metric("disk_usage", disk_percent)
            
            # Network I/O
            network = psutil.net_io_counters()
            self._record_metric("network_bytes_sent", network.bytes_sent)
            self._record_metric("network_bytes_recv", network.bytes_recv)
            
            # Process-specific metrics
            process = psutil.Process()
            self._record_metric("process_cpu_percent", process.cpu_percent())
            self._record_metric("process_memory_mb", process.memory_info().rss / 1024 / 1024)
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    def _record_metric(self, name: str, value: float):
        """Record a metric value"""
        # Store in local metrics
        if name not in self.metric_history:
            self.metric_history[name] = []
        
        self.metric_history[name].append(value)
        
        # Keep only last 100 values
        if len(self.metric_history[name]) > 100:
            self.metric_history[name] = self.metric_history[name][-100:]
        
        # Update current metric
        self.metrics[name] = Metric(
            name=name,
            metric_type=MetricType.GAUGE,
            description=f"Metric: {name}",
            value=value,
            timestamp=datetime.now()
        )
    
    def _run_health_checks(self):
        """Run all registered health checks"""
        overall_status = HealthStatus.HEALTHY
        failed_checks = []
        
        for name, health_check in self.health_checks.items():
            try:
                # Run health check with timeout
                start_time = time.time()
                result = health_check.check_function()
                duration = time.time() - start_time
                
                if duration > health_check.timeout:
                    logger.warning(f"Health check '{name}' took {duration:.2f}s (timeout: {health_check.timeout}s)")
                
                if not result:
                    failed_checks.append(name)
                    if health_check.critical:
                        overall_status = HealthStatus.UNHEALTHY
                    elif overall_status == HealthStatus.HEALTHY:
                        overall_status = HealthStatus.DEGRADED
                
            except Exception as e:
                logger.error(f"Health check '{name}' failed with exception: {e}")
                failed_checks.append(name)
                if health_check.critical:
                    overall_status = HealthStatus.UNHEALTHY
                elif overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
        
        self.health_status = overall_status
        self.last_health_check = datetime.now()
        
        if failed_checks:
            logger.warning(f"Failed health checks: {failed_checks}")
    
    def _check_alerts(self):
        """Check all registered alerts"""
        current_metrics = self._get_current_metrics()
        
        for name, alert in self.alerts.items():
            try:
                # Check cooldown period
                if alert.last_triggered:
                    cooldown_end = alert.last_triggered + timedelta(minutes=alert.cooldown_minutes)
                    if datetime.now() < cooldown_end:
                        continue
                
                # Check alert condition
                if alert.condition(current_metrics):
                    # Trigger alert
                    message = alert.message_template.format(**current_metrics)
                    self._trigger_alert(name, message, alert.severity)
                    alert.last_triggered = datetime.now()
                    
            except Exception as e:
                logger.error(f"Error checking alert '{name}': {e}")
    
    def _get_current_metrics(self) -> Dict[str, Any]:
        """Get current metric values"""
        metrics = {}
        
        for name, metric in self.metrics.items():
            metrics[name] = metric.value
        
        # Add calculated metrics
        if "cpu_usage" in self.metric_history:
            metrics["average_cpu_usage"] = sum(self.metric_history["cpu_usage"][-10:]) / min(10, len(self.metric_history["cpu_usage"]))
        
        if "memory_usage" in self.metric_history:
            metrics["average_memory_usage"] = sum(self.metric_history["memory_usage"][-10:]) / min(10, len(self.metric_history["memory_usage"]))
        
        # Add performance data
        metrics.update(self.performance_data["call_metrics"])
        
        return metrics
    
    def _trigger_alert(self, alert_name: str, message: str, severity: ErrorSeverity):
        """Trigger an alert"""
        logger.warning(f"ALERT [{severity.value.upper()}] {alert_name}: {message}")
        
        # Call registered alert callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert_name, message, severity)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
    
    def _update_prometheus_metrics(self):
        """Update Prometheus metrics"""
        if not self.prometheus_metrics:
            return
        
        try:
            # Update system metrics
            if "cpu_usage" in self.metrics:
                self.prometheus_metrics["cpu_usage"].set(self.metrics["cpu_usage"].value)
            
            if "memory_usage" in self.metrics:
                self.prometheus_metrics["memory_usage"].set(self.metrics["memory_usage"].value)
            
            # Update call metrics
            call_metrics = self.performance_data["call_metrics"]
            self.prometheus_metrics["active_calls"].set(call_metrics["active_calls"])
            
            # Update health status
            self.prometheus_metrics["health_status"].state(self.health_status.value)
            
        except Exception as e:
            logger.error(f"Error updating Prometheus metrics: {e}")
    
    # Public API methods
    
    def register_health_check(self, name: str, check_function: Callable[[], bool],
                            timeout: float = 5.0, critical: bool = False,
                            description: str = ""):
        """Register a health check"""
        self.health_checks[name] = HealthCheck(
            name=name,
            check_function=check_function,
            timeout=timeout,
            critical=critical,
            description=description
        )
        logger.debug(f"Registered health check: {name}")
    
    def register_alert(self, name: str, condition: Callable[[Dict[str, Any]], bool],
                      severity: ErrorSeverity, message_template: str,
                      cooldown_minutes: int = 5):
        """Register an alert"""
        self.alerts[name] = Alert(
            name=name,
            condition=condition,
            severity=severity,
            message_template=message_template,
            cooldown_minutes=cooldown_minutes
        )
        logger.debug(f"Registered alert: {name}")
    
    def register_alert_callback(self, callback: Callable[[str, str, ErrorSeverity], None]):
        """Register alert callback"""
        self.alert_callbacks.append(callback)
    
    def record_call_metric(self, metric_name: str, value: float):
        """Record call-related metric"""
        if metric_name in self.performance_data["call_metrics"]:
            self.performance_data["call_metrics"][metric_name] = value
        
        # Update Prometheus if available
        if metric_name in self.prometheus_metrics:
            if hasattr(self.prometheus_metrics[metric_name], 'set'):
                self.prometheus_metrics[metric_name].set(value)
            elif hasattr(self.prometheus_metrics[metric_name], 'inc'):
                self.prometheus_metrics[metric_name].inc()
    
    def record_audio_metric(self, metric_name: str, value: float):
        """Record audio processing metric"""
        if metric_name in self.performance_data["audio_metrics"]:
            if isinstance(self.performance_data["audio_metrics"][metric_name], list):
                self.performance_data["audio_metrics"][metric_name].append(value)
                # Keep only last 100 values
                if len(self.performance_data["audio_metrics"][metric_name]) > 100:
                    self.performance_data["audio_metrics"][metric_name] = self.performance_data["audio_metrics"][metric_name][-100:]
            else:
                self.performance_data["audio_metrics"][metric_name] = value
    
    def record_ai_metric(self, metric_name: str, value: float):
        """Record AI-related metric"""
        if metric_name in self.performance_data["ai_metrics"]:
            if isinstance(self.performance_data["ai_metrics"][metric_name], list):
                self.performance_data["ai_metrics"][metric_name].append(value)
                # Keep only last 100 values
                if len(self.performance_data["ai_metrics"][metric_name]) > 100:
                    self.performance_data["ai_metrics"][metric_name] = self.performance_data["ai_metrics"][metric_name][-100:]
            else:
                self.performance_data["ai_metrics"][metric_name] = value
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status"""
        return {
            "status": self.health_status.value,
            "last_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "checks": {
                name: {
                    "description": check.description,
                    "critical": check.critical
                }
                for name, check in self.health_checks.items()
            }
        }
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        return {
            "system": {
                name: metric.value
                for name, metric in self.metrics.items()
                if name in ["cpu_usage", "memory_usage", "disk_usage"]
            },
            "performance": self.performance_data,
            "health": self.get_health_status()
        }
    
    def get_prometheus_metrics_endpoint(self):
        """Get Prometheus metrics endpoint handler"""
        if not prometheus_client:
            return None
        
        def metrics_handler():
            return prometheus_client.generate_latest()
        
        return metrics_handler


# Global monitoring system instance
_monitoring_system = None


def get_monitoring_system(config: Optional[Dict[str, Any]] = None) -> MonitoringSystem:
    """Get the global monitoring system instance"""
    global _monitoring_system
    if _monitoring_system is None:
        _monitoring_system = MonitoringSystem(config)
    return _monitoring_system