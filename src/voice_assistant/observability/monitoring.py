"""
Health Monitoring and Alerting System
Provides health checks, alerting, and system monitoring
"""

import asyncio
import time
import psutil
import json
from typing import Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import logging
import aiohttp
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart

logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    """Health check status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class HealthCheck:
    """Health check definition"""
    name: str
    check_function: Callable[[], bool]
    timeout: float = 5.0
    interval: float = 30.0
    description: str = ""
    dependencies: List[str] = field(default_factory=list)

@dataclass
class HealthResult:
    """Result of a health check"""
    name: str
    status: HealthStatus
    message: str = ""
    timestamp: float = field(default_factory=time.time)
    duration: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Alert:
    """Alert definition"""
    id: str
    title: str
    message: str
    severity: AlertSeverity
    timestamp: float = field(default_factory=time.time)
    source: str = ""
    tags: Dict[str, str] = field(default_factory=dict)
    resolved: bool = False
    resolved_at: Optional[float] = None

class HealthChecker:
    """Health monitoring system"""
    
    def __init__(self):
        self.checks: Dict[str, HealthCheck] = {}
        self.results: Dict[str, HealthResult] = {}
        self.running = False
        self.check_tasks: Dict[str, asyncio.Task] = {}
        self.overall_status = HealthStatus.UNKNOWN
        
        # System metrics
        self.system_metrics = {
            'cpu_percent': 0.0,
            'memory_percent': 0.0,
            'disk_percent': 0.0,
            'network_connections': 0,
            'uptime': 0.0
        }
        
        # Register default system checks
        self._register_default_checks()
    
    def register_check(self, check: HealthCheck):
        """Register a health check"""
        self.checks[check.name] = check
        logger.info(f"Registered health check: {check.name}")
    
    def unregister_check(self, name: str):
        """Unregister a health check"""
        if name in self.checks:
            del self.checks[name]
            if name in self.results:
                del self.results[name]
            logger.info(f"Unregistered health check: {name}")
    
    async def start_monitoring(self):
        """Start health monitoring"""
        if self.running:
            return
        
        self.running = True
        logger.info("Starting health monitoring")
        
        # Start check tasks
        for name, check in self.checks.items():
            self.check_tasks[name] = asyncio.create_task(
                self._run_check_loop(check)
            )
        
        # Start system metrics collection
        self.check_tasks['system_metrics'] = asyncio.create_task(
            self._collect_system_metrics()
        )
    
    async def stop_monitoring(self):
        """Stop health monitoring"""
        if not self.running:
            return
        
        self.running = False
        logger.info("Stopping health monitoring")
        
        # Cancel all tasks
        for task in self.check_tasks.values():
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.check_tasks.values(), return_exceptions=True)
        self.check_tasks.clear()
    
    async def run_check(self, name: str) -> HealthResult:
        """Run a specific health check"""
        if name not in self.checks:
            return HealthResult(
                name=name,
                status=HealthStatus.UNKNOWN,
                message="Check not found"
            )
        
        check = self.checks[name]
        start_time = time.time()
        
        try:
            # Run check with timeout
            result = await asyncio.wait_for(
                asyncio.create_task(self._execute_check(check)),
                timeout=check.timeout
            )
            
            duration = time.time() - start_time
            
            health_result = HealthResult(
                name=name,
                status=HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY,
                message="Check passed" if result else "Check failed",
                duration=duration
            )
            
        except asyncio.TimeoutError:
            duration = time.time() - start_time
            health_result = HealthResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check timed out after {check.timeout}s",
                duration=duration
            )
            
        except Exception as e:
            duration = time.time() - start_time
            health_result = HealthResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check failed: {str(e)}",
                duration=duration
            )
        
        self.results[name] = health_result
        self._update_overall_status()
        
        return health_result
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status"""
        return {
            'status': self.overall_status.value,
            'timestamp': time.time(),
            'checks': {name: {
                'status': result.status.value,
                'message': result.message,
                'timestamp': result.timestamp,
                'duration': result.duration,
                'details': result.details
            } for name, result in self.results.items()},
            'system_metrics': self.system_metrics
        }
    
    def get_check_result(self, name: str) -> Optional[HealthResult]:
        """Get result of specific check"""
        return self.results.get(name)
    
    async def _run_check_loop(self, check: HealthCheck):
        """Run health check in a loop"""
        while self.running:
            try:
                await self.run_check(check.name)
                await asyncio.sleep(check.interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop for {check.name}: {e}")
                await asyncio.sleep(check.interval)
    
    async def _execute_check(self, check: HealthCheck) -> bool:
        """Execute a health check function"""
        if asyncio.iscoroutinefunction(check.check_function):
            return await check.check_function()
        else:
            return check.check_function()
    
    async def _collect_system_metrics(self):
        """Collect system metrics"""
        while self.running:
            try:
                # CPU usage
                self.system_metrics['cpu_percent'] = psutil.cpu_percent(interval=1)
                
                # Memory usage
                memory = psutil.virtual_memory()
                self.system_metrics['memory_percent'] = memory.percent
                
                # Disk usage
                disk = psutil.disk_usage('/')
                self.system_metrics['disk_percent'] = (disk.used / disk.total) * 100
                
                # Network connections
                self.system_metrics['network_connections'] = len(psutil.net_connections())
                
                # Uptime
                boot_time = psutil.boot_time()
                self.system_metrics['uptime'] = time.time() - boot_time
                
                await asyncio.sleep(10)  # Collect every 10 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error collecting system metrics: {e}")
                await asyncio.sleep(10)
    
    def _update_overall_status(self):
        """Update overall health status based on individual checks"""
        if not self.results:
            self.overall_status = HealthStatus.UNKNOWN
            return
        
        statuses = [result.status for result in self.results.values()]
        
        if all(status == HealthStatus.HEALTHY for status in statuses):
            self.overall_status = HealthStatus.HEALTHY
        elif any(status == HealthStatus.UNHEALTHY for status in statuses):
            self.overall_status = HealthStatus.UNHEALTHY
        else:
            self.overall_status = HealthStatus.DEGRADED
    
    def _register_default_checks(self):
        """Register default system health checks"""
        
        def check_memory():
            """Check memory usage"""
            memory = psutil.virtual_memory()
            return memory.percent < 90  # Alert if memory > 90%
        
        def check_disk():
            """Check disk usage"""
            disk = psutil.disk_usage('/')
            return (disk.used / disk.total) * 100 < 90  # Alert if disk > 90%
        
        def check_cpu():
            """Check CPU usage"""
            cpu_percent = psutil.cpu_percent(interval=1)
            return cpu_percent < 90  # Alert if CPU > 90%
        
        # Register checks
        self.register_check(HealthCheck(
            name="memory_usage",
            check_function=check_memory,
            description="Check system memory usage"
        ))
        
        self.register_check(HealthCheck(
            name="disk_usage",
            check_function=check_disk,
            description="Check system disk usage"
        ))
        
        self.register_check(HealthCheck(
            name="cpu_usage",
            check_function=check_cpu,
            description="Check system CPU usage"
        ))

class AlertManager:
    """Alert management system"""
    
    def __init__(self):
        self.alerts: Dict[str, Alert] = {}
        self.handlers: List[Callable[[Alert], None]] = []
        self.rules: List[Callable[[Dict[str, Any]], Optional[Alert]]] = []
        self.suppression_rules: List[Callable[[Alert], bool]] = []
        
        # Alert statistics
        self.stats = {
            'total_alerts': 0,
            'active_alerts': 0,
            'resolved_alerts': 0,
            'suppressed_alerts': 0
        }
    
    def add_handler(self, handler: Callable[[Alert], None]):
        """Add alert handler"""
        self.handlers.append(handler)
    
    def add_rule(self, rule: Callable[[Dict[str, Any]], Optional[Alert]]):
        """Add alerting rule"""
        self.rules.append(rule)
    
    def add_suppression_rule(self, rule: Callable[[Alert], bool]):
        """Add alert suppression rule"""
        self.suppression_rules.append(rule)
    
    async def process_metrics(self, metrics: Dict[str, Any]):
        """Process metrics and generate alerts"""
        for rule in self.rules:
            try:
                alert = rule(metrics)
                if alert:
                    await self.fire_alert(alert)
            except Exception as e:
                logger.error(f"Error processing alert rule: {e}")
    
    async def fire_alert(self, alert: Alert):
        """Fire an alert"""
        # Check suppression rules
        for suppression_rule in self.suppression_rules:
            try:
                if suppression_rule(alert):
                    self.stats['suppressed_alerts'] += 1
                    logger.debug(f"Alert suppressed: {alert.title}")
                    return
            except Exception as e:
                logger.error(f"Error in suppression rule: {e}")
        
        # Store alert
        self.alerts[alert.id] = alert
        self.stats['total_alerts'] += 1
        self.stats['active_alerts'] += 1
        
        logger.warning(f"Alert fired: {alert.title} - {alert.message}")
        
        # Send to handlers
        for handler in self.handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                logger.error(f"Error in alert handler: {e}")
    
    async def resolve_alert(self, alert_id: str, message: str = ""):
        """Resolve an alert"""
        if alert_id in self.alerts:
            alert = self.alerts[alert_id]
            if not alert.resolved:
                alert.resolved = True
                alert.resolved_at = time.time()
                
                self.stats['active_alerts'] -= 1
                self.stats['resolved_alerts'] += 1
                
                logger.info(f"Alert resolved: {alert.title} - {message}")
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts"""
        return [alert for alert in self.alerts.values() if not alert.resolved]
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics"""
        return {
            **self.stats,
            'timestamp': time.time()
        }

class EmailAlertHandler:
    """Email alert handler"""
    
    def __init__(self, smtp_server: str, smtp_port: int,
                 username: str, password: str,
                 from_email: str, to_emails: List[str]):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.to_emails = to_emails
    
    async def __call__(self, alert: Alert):
        """Send alert via email"""
        try:
            # Create message
            msg = MimeMultipart()
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.title}"
            
            # Email body
            body = f"""
Alert Details:
- Title: {alert.title}
- Severity: {alert.severity.value}
- Source: {alert.source}
- Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(alert.timestamp))}
- Message: {alert.message}

Tags: {json.dumps(alert.tags, indent=2)}
            """
            
            msg.attach(MimeText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"Email alert sent: {alert.title}")
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")

class WebhookAlertHandler:
    """Webhook alert handler"""
    
    def __init__(self, webhook_url: str, headers: Dict[str, str] = None):
        self.webhook_url = webhook_url
        self.headers = headers or {}
    
    async def __call__(self, alert: Alert):
        """Send alert via webhook"""
        try:
            payload = {
                'id': alert.id,
                'title': alert.title,
                'message': alert.message,
                'severity': alert.severity.value,
                'timestamp': alert.timestamp,
                'source': alert.source,
                'tags': alert.tags
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        logger.info(f"Webhook alert sent: {alert.title}")
                    else:
                        logger.error(f"Webhook alert failed: {response.status}")
                        
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")

class SlackAlertHandler:
    """Slack alert handler"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    async def __call__(self, alert: Alert):
        """Send alert to Slack"""
        try:
            # Color based on severity
            color_map = {
                AlertSeverity.INFO: "#36a64f",
                AlertSeverity.WARNING: "#ff9500",
                AlertSeverity.ERROR: "#ff0000",
                AlertSeverity.CRITICAL: "#8B0000"
            }
            
            payload = {
                "attachments": [{
                    "color": color_map.get(alert.severity, "#36a64f"),
                    "title": alert.title,
                    "text": alert.message,
                    "fields": [
                        {
                            "title": "Severity",
                            "value": alert.severity.value.upper(),
                            "short": True
                        },
                        {
                            "title": "Source",
                            "value": alert.source,
                            "short": True
                        },
                        {
                            "title": "Time",
                            "value": time.strftime('%Y-%m-%d %H:%M:%S', 
                                               time.localtime(alert.timestamp)),
                            "short": True
                        }
                    ],
                    "footer": "NPCL Voice Assistant",
                    "ts": int(alert.timestamp)
                }]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 200:
                        logger.info(f"Slack alert sent: {alert.title}")
                    else:
                        logger.error(f"Slack alert failed: {response.status}")
                        
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")

# Default alerting rules
def create_default_alert_rules() -> List[Callable[[Dict[str, Any]], Optional[Alert]]]:
    """Create default alerting rules"""
    
    def high_cpu_rule(metrics: Dict[str, Any]) -> Optional[Alert]:
        """Alert on high CPU usage"""
        cpu_percent = metrics.get('system_metrics', {}).get('cpu_percent', 0)
        if cpu_percent > 90:
            return Alert(
                id=f"high_cpu_{int(time.time())}",
                title="High CPU Usage",
                message=f"CPU usage is {cpu_percent:.1f}%",
                severity=AlertSeverity.WARNING,
                source="system_monitor",
                tags={'metric': 'cpu_percent', 'value': str(cpu_percent)}
            )
        return None
    
    def high_memory_rule(metrics: Dict[str, Any]) -> Optional[Alert]:
        """Alert on high memory usage"""
        memory_percent = metrics.get('system_metrics', {}).get('memory_percent', 0)
        if memory_percent > 90:
            return Alert(
                id=f"high_memory_{int(time.time())}",
                title="High Memory Usage",
                message=f"Memory usage is {memory_percent:.1f}%",
                severity=AlertSeverity.WARNING,
                source="system_monitor",
                tags={'metric': 'memory_percent', 'value': str(memory_percent)}
            )
        return None
    
    def service_unhealthy_rule(metrics: Dict[str, Any]) -> Optional[Alert]:
        """Alert on unhealthy service"""
        status = metrics.get('status')
        if status == 'unhealthy':
            return Alert(
                id=f"service_unhealthy_{int(time.time())}",
                title="Service Unhealthy",
                message="One or more health checks are failing",
                severity=AlertSeverity.ERROR,
                source="health_monitor",
                tags={'status': status}
            )
        return None
    
    return [high_cpu_rule, high_memory_rule, service_unhealthy_rule]

# Default suppression rules
def create_default_suppression_rules() -> List[Callable[[Alert], bool]]:
    """Create default suppression rules"""
    
    def duplicate_suppression(alert: Alert) -> bool:
        """Suppress duplicate alerts within 5 minutes"""
        # This would need to track recent alerts
        # For now, just return False (no suppression)
        return False
    
    def maintenance_window_suppression(alert: Alert) -> bool:
        """Suppress alerts during maintenance windows"""
        # Check if we're in a maintenance window
        # For now, just return False
        return False
    
    return [duplicate_suppression, maintenance_window_suppression]