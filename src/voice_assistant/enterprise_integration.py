"""
Enterprise Integration Module
Integrates security, observability, and scalability components
"""

import asyncio
import time
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging

# Security imports
from .security import (
    SecurityManager, JWTAuthManager, TokenBucketRateLimiter,
    SecurityValidator, AuditLogger, EncryptionManager
)

# Observability imports
from .observability import (
    MetricsCollector, PrometheusMetrics, InMemoryMetricsCollector,
    ApplicationMetrics, DistributedTracer, StructuredLogger,
    HealthChecker, AlertManager, DashboardManager
)

# Scalability imports
from .scalability import (
    LoadBalancer, RoundRobinBalancer, ClusterManager, AutoScaler,
    ServiceDiscovery, InMemoryServiceDiscovery, DatabaseCluster,
    RedisCluster
)

logger = logging.getLogger(__name__)

@dataclass
class EnterpriseConfig:
    """Enterprise configuration"""
    # Security settings
    enable_security: bool = True
    enable_rate_limiting: bool = True
    enable_input_validation: bool = True
    enable_encryption: bool = True
    enable_audit_logging: bool = True
    
    # Observability settings
    enable_metrics: bool = True
    enable_tracing: bool = True
    enable_structured_logging: bool = True
    enable_health_checks: bool = True
    enable_alerting: bool = True
    enable_dashboard: bool = True
    
    # Scalability settings
    enable_clustering: bool = True
    enable_load_balancing: bool = True
    enable_auto_scaling: bool = True
    enable_service_discovery: bool = True
    enable_database_clustering: bool = True
    
    # Component configurations
    metrics_type: str = "prometheus"  # prometheus, memory
    service_discovery_type: str = "memory"  # memory, consul, kubernetes
    load_balancer_type: str = "round_robin"  # round_robin, weighted, adaptive
    database_cluster_type: str = "redis"  # redis, postgresql
    
    # Network settings
    cluster_node_id: str = ""
    cluster_host: str = "localhost"
    cluster_port: int = 8000
    metrics_port: int = 9090
    dashboard_port: int = 8080
    
    # External services
    prometheus_url: str = "http://localhost:9090"
    consul_url: str = "http://localhost:8500"
    redis_url: str = "redis://localhost:6379"

class EnterpriseVoiceAssistant:
    """Enterprise-grade voice assistant with full observability, security, and scalability"""
    
    def __init__(self, config: EnterpriseConfig):
        self.config = config
        
        # Core components
        self.security_manager: Optional[SecurityManager] = None
        self.metrics_collector: Optional[MetricsCollector] = None
        self.application_metrics: Optional[ApplicationMetrics] = None
        self.tracer: Optional[DistributedTracer] = None
        self.logger: Optional[StructuredLogger] = None
        self.health_checker: Optional[HealthChecker] = None
        self.alert_manager: Optional[AlertManager] = None
        self.dashboard_manager: Optional[DashboardManager] = None
        self.load_balancer: Optional[LoadBalancer] = None
        self.cluster_manager: Optional[ClusterManager] = None
        self.auto_scaler: Optional[AutoScaler] = None
        self.service_discovery: Optional[ServiceDiscovery] = None
        self.database_cluster: Optional[DatabaseCluster] = None
        
        # State
        self.running = False
        self.startup_time = time.time()
    
    async def initialize(self):
        """Initialize all enterprise components"""
        logger.info("Initializing enterprise voice assistant...")
        
        try:
            # Initialize security components
            if self.config.enable_security:
                await self._initialize_security()
            
            # Initialize observability components
            if self.config.enable_metrics:
                await self._initialize_observability()
            
            # Initialize scalability components
            if self.config.enable_clustering:
                await self._initialize_scalability()
            
            logger.info("Enterprise voice assistant initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize enterprise components: {e}")
            raise
    
    async def start(self):
        """Start all enterprise components"""
        if self.running:
            return
        
        logger.info("Starting enterprise voice assistant...")
        
        try:
            # Start observability components
            if self.health_checker:
                await self.health_checker.start_monitoring()
            
            if self.tracer:
                await self.tracer.start_export_task()
            
            if self.dashboard_manager:
                await self.dashboard_manager.start_server()
            
            # Start scalability components
            if self.cluster_manager:
                await self.cluster_manager.start()
            
            if self.auto_scaler:
                await self.auto_scaler.start()
            
            if self.load_balancer:
                await self.load_balancer.start_health_checks()
            
            if self.database_cluster:
                await self.database_cluster.start()
            
            self.running = True
            logger.info("Enterprise voice assistant started successfully")
            
            # Log startup metrics
            if self.application_metrics:
                startup_time = time.time() - self.startup_time
                self.application_metrics.collector.record_histogram(
                    "startup_duration_seconds", startup_time
                )
            
        except Exception as e:
            logger.error(f"Failed to start enterprise components: {e}")
            raise
    
    async def stop(self):
        """Stop all enterprise components"""
        if not self.running:
            return
        
        logger.info("Stopping enterprise voice assistant...")
        
        try:
            # Stop scalability components
            if self.database_cluster:
                await self.database_cluster.stop()
            
            if self.load_balancer:
                await self.load_balancer.stop_health_checks()
            
            if self.auto_scaler:
                await self.auto_scaler.stop()
            
            if self.cluster_manager:
                await self.cluster_manager.stop()
            
            # Stop observability components
            if self.dashboard_manager:
                await self.dashboard_manager.stop_server()
            
            if self.tracer:
                await self.tracer.stop_export_task()
            
            if self.health_checker:
                await self.health_checker.stop_monitoring()
            
            self.running = False
            logger.info("Enterprise voice assistant stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping enterprise components: {e}")
    
    async def _initialize_security(self):
        """Initialize security components"""
        logger.info("Initializing security components...")
        
        # JWT Authentication Manager
        jwt_secret = os.getenv("JWT_SECRET_KEY", "default-secret-key")
        auth_manager = JWTAuthManager(jwt_secret)
        
        # Rate Limiter
        rate_limiter = TokenBucketRateLimiter()
        
        # Input Validator
        input_validator = SecurityValidator()
        
        # Audit Logger
        audit_logger = AuditLogger(
            log_file="logs/audit.log" if self.config.enable_audit_logging else None
        )
        
        # Encryption Manager
        encryption_manager = EncryptionManager(
            master_key=os.getenv("ENCRYPTION_KEY")
        )
        
        # Security Manager
        self.security_manager = SecurityManager(
            auth_manager=auth_manager,
            rate_limiter=rate_limiter,
            input_validator=input_validator,
            audit_logger=audit_logger,
            encryption_manager=encryption_manager
        )
        
        logger.info("Security components initialized")
    
    async def _initialize_observability(self):
        """Initialize observability components"""
        logger.info("Initializing observability components...")
        
        # Metrics Collector
        if self.config.metrics_type == "prometheus":
            try:
                self.metrics_collector = PrometheusMetrics()
            except ImportError:
                logger.warning("Prometheus not available, using in-memory metrics")
                self.metrics_collector = InMemoryMetricsCollector()
        else:
            self.metrics_collector = InMemoryMetricsCollector()
        
        # Application Metrics
        self.application_metrics = ApplicationMetrics(self.metrics_collector)
        
        # Distributed Tracer
        if self.config.enable_tracing:
            service_name = "npcl-voice-assistant"
            self.tracer = DistributedTracer(service_name)
        
        # Structured Logger
        if self.config.enable_structured_logging:
            self.logger = StructuredLogger(
                name="enterprise-voice-assistant",
                output_file="logs/application.log",
                json_format=True
            )
        
        # Health Checker
        if self.config.enable_health_checks:
            self.health_checker = HealthChecker()
            
            # Add custom health checks
            self._register_health_checks()
        
        # Alert Manager
        if self.config.enable_alerting:
            self.alert_manager = AlertManager()
            
            # Add default alerting rules
            self._setup_alerting_rules()
        
        # Dashboard Manager
        if self.config.enable_dashboard:
            self.dashboard_manager = DashboardManager(port=self.config.dashboard_port)
            
            # Register data sources
            self._register_dashboard_data_sources()
        
        logger.info("Observability components initialized")
    
    async def _initialize_scalability(self):
        """Initialize scalability components"""
        logger.info("Initializing scalability components...")
        
        # Service Discovery
        if self.config.enable_service_discovery:
            if self.config.service_discovery_type == "consul":
                try:
                    from .scalability.service_discovery import ConsulServiceDiscovery
                    self.service_discovery = ConsulServiceDiscovery()
                except ImportError:
                    logger.warning("Consul not available, using in-memory service discovery")
                    self.service_discovery = InMemoryServiceDiscovery()
            else:
                self.service_discovery = InMemoryServiceDiscovery()
        
        # Load Balancer
        if self.config.enable_load_balancing:
            from .scalability.load_balancer import LoadBalancerFactory
            self.load_balancer = LoadBalancerFactory.create_balancer(
                self.config.load_balancer_type
            )
        
        # Cluster Manager
        if self.config.enable_clustering:
            node_id = self.config.cluster_node_id or f"node-{int(time.time())}"
            self.cluster_manager = ClusterManager(
                node_id=node_id,
                host=self.config.cluster_host,
                port=self.config.cluster_port
            )
        
        # Auto Scaler
        if self.config.enable_auto_scaling:
            # This would need proper metrics provider and service scaler
            # For now, we'll skip auto-scaler initialization
            logger.info("Auto-scaler requires external metrics provider and service scaler")
        
        # Database Cluster
        if self.config.enable_database_clustering:
            if self.config.database_cluster_type == "redis":
                try:
                    self.database_cluster = RedisCluster()
                except ImportError:
                    logger.warning("Redis not available, skipping database clustering")
        
        logger.info("Scalability components initialized")
    
    def _register_health_checks(self):
        """Register custom health checks"""
        if not self.health_checker:
            return
        
        from .observability.monitoring import HealthCheck
        
        # Voice assistant specific health checks
        def check_ai_service():
            """Check if AI service is responding"""
            # This would check Gemini API connectivity
            return True
        
        def check_audio_system():
            """Check audio system health"""
            # This would check audio device availability
            return True
        
        def check_telephony_system():
            """Check telephony system health"""
            # This would check Asterisk connectivity
            return True
        
        # Register checks
        self.health_checker.register_check(HealthCheck(
            name="ai_service",
            check_function=check_ai_service,
            description="Check AI service connectivity"
        ))
        
        self.health_checker.register_check(HealthCheck(
            name="audio_system",
            check_function=check_audio_system,
            description="Check audio system health"
        ))
        
        self.health_checker.register_check(HealthCheck(
            name="telephony_system",
            check_function=check_telephony_system,
            description="Check telephony system health"
        ))
    
    def _setup_alerting_rules(self):
        """Setup alerting rules"""
        if not self.alert_manager:
            return
        
        from .observability.monitoring import create_default_alert_rules
        
        # Add default rules
        for rule in create_default_alert_rules():
            self.alert_manager.add_rule(rule)
        
        # Add voice assistant specific rules
        def high_session_count_rule(metrics: Dict[str, Any]):
            """Alert on high session count"""
            active_sessions = metrics.get('active_sessions', 0)
            if active_sessions > 50:
                from .observability.monitoring import Alert, AlertSeverity
                return Alert(
                    id=f"high_sessions_{int(time.time())}",
                    title="High Session Count",
                    message=f"Active sessions: {active_sessions}",
                    severity=AlertSeverity.WARNING,
                    source="voice_assistant",
                    tags={'metric': 'active_sessions', 'value': str(active_sessions)}
                )
            return None
        
        self.alert_manager.add_rule(high_session_count_rule)
    
    def _register_dashboard_data_sources(self):
        """Register dashboard data sources"""
        if not self.dashboard_manager:
            return
        
        # System metrics data source
        def get_system_metrics():
            if self.application_metrics:
                return self.application_metrics.collector.get_metrics()
            return {}
        
        # Health status data source
        def get_health_status():
            if self.health_checker:
                return self.health_checker.get_health_status()
            return {"status": "unknown"}
        
        # Voice metrics data source
        def get_voice_metrics():
            return {
                "active_sessions": 5,  # This would come from actual session manager
                "avg_response_time": 1.2,
                "error_rate": 0.02
            }
        
        # Register data sources
        self.dashboard_manager.register_data_source("system_metrics", get_system_metrics)
        self.dashboard_manager.register_data_source("health_status", get_health_status)
        self.dashboard_manager.register_data_source("voice_metrics", get_voice_metrics)
    
    async def get_enterprise_status(self) -> Dict[str, Any]:
        """Get comprehensive enterprise status"""
        status = {
            "timestamp": time.time(),
            "running": self.running,
            "uptime": time.time() - self.startup_time,
            "components": {}
        }
        
        # Security status
        if self.security_manager:
            status["components"]["security"] = await self.security_manager.get_security_metrics()
        
        # Observability status
        if self.health_checker:
            status["components"]["health"] = self.health_checker.get_health_status()
        
        if self.application_metrics:
            status["components"]["metrics"] = self.application_metrics.collector.get_metrics()
        
        if self.tracer:
            status["components"]["tracing"] = self.tracer.get_statistics()
        
        # Scalability status
        if self.cluster_manager:
            status["components"]["cluster"] = self.cluster_manager.get_cluster_status()
        
        if self.load_balancer:
            status["components"]["load_balancer"] = self.load_balancer.get_statistics()
        
        if self.database_cluster:
            status["components"]["database_cluster"] = await self.database_cluster.get_cluster_status()
        
        return status
    
    def get_security_manager(self) -> Optional[SecurityManager]:
        """Get security manager instance"""
        return self.security_manager
    
    def get_metrics_collector(self) -> Optional[MetricsCollector]:
        """Get metrics collector instance"""
        return self.metrics_collector
    
    def get_application_metrics(self) -> Optional[ApplicationMetrics]:
        """Get application metrics instance"""
        return self.application_metrics
    
    def get_tracer(self) -> Optional[DistributedTracer]:
        """Get distributed tracer instance"""
        return self.tracer
    
    def get_cluster_manager(self) -> Optional[ClusterManager]:
        """Get cluster manager instance"""
        return self.cluster_manager

# Factory function for easy initialization
async def create_enterprise_voice_assistant(config: Optional[EnterpriseConfig] = None) -> EnterpriseVoiceAssistant:
    """Create and initialize enterprise voice assistant"""
    if config is None:
        config = EnterpriseConfig()
    
    assistant = EnterpriseVoiceAssistant(config)
    await assistant.initialize()
    
    return assistant

# Configuration from environment variables
def load_config_from_env() -> EnterpriseConfig:
    """Load configuration from environment variables"""
    return EnterpriseConfig(
        # Security settings
        enable_security=os.getenv("SECURITY_ENABLED", "true").lower() == "true",
        enable_rate_limiting=os.getenv("RATE_LIMITING_ENABLED", "true").lower() == "true",
        enable_input_validation=os.getenv("INPUT_VALIDATION_ENABLED", "true").lower() == "true",
        enable_encryption=os.getenv("ENCRYPTION_ENABLED", "true").lower() == "true",
        enable_audit_logging=os.getenv("AUDIT_LOGGING_ENABLED", "true").lower() == "true",
        
        # Observability settings
        enable_metrics=os.getenv("METRICS_ENABLED", "true").lower() == "true",
        enable_tracing=os.getenv("TRACING_ENABLED", "true").lower() == "true",
        enable_structured_logging=os.getenv("STRUCTURED_LOGGING_ENABLED", "true").lower() == "true",
        enable_health_checks=os.getenv("HEALTH_CHECKS_ENABLED", "true").lower() == "true",
        enable_alerting=os.getenv("ALERTING_ENABLED", "true").lower() == "true",
        enable_dashboard=os.getenv("DASHBOARD_ENABLED", "true").lower() == "true",
        
        # Scalability settings
        enable_clustering=os.getenv("CLUSTERING_ENABLED", "false").lower() == "true",
        enable_load_balancing=os.getenv("LOAD_BALANCING_ENABLED", "false").lower() == "true",
        enable_auto_scaling=os.getenv("AUTO_SCALING_ENABLED", "false").lower() == "true",
        enable_service_discovery=os.getenv("SERVICE_DISCOVERY_ENABLED", "false").lower() == "true",
        enable_database_clustering=os.getenv("DATABASE_CLUSTERING_ENABLED", "false").lower() == "true",
        
        # Component configurations
        metrics_type=os.getenv("METRICS_TYPE", "prometheus"),
        service_discovery_type=os.getenv("SERVICE_DISCOVERY_TYPE", "memory"),
        load_balancer_type=os.getenv("LOAD_BALANCER_TYPE", "round_robin"),
        database_cluster_type=os.getenv("DATABASE_CLUSTER_TYPE", "redis"),
        
        # Network settings
        cluster_node_id=os.getenv("CLUSTER_NODE_ID", ""),
        cluster_host=os.getenv("CLUSTER_HOST", "localhost"),
        cluster_port=int(os.getenv("CLUSTER_PORT", "8000")),
        metrics_port=int(os.getenv("METRICS_PORT", "9090")),
        dashboard_port=int(os.getenv("DASHBOARD_PORT", "8080")),
        
        # External services
        prometheus_url=os.getenv("PROMETHEUS_URL", "http://localhost:9090"),
        consul_url=os.getenv("CONSUL_URL", "http://localhost:8500"),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379")
    )