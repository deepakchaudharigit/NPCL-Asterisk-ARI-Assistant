"""
Auto-scaling Implementation
Automatically scales services based on metrics and policies
"""

import asyncio
import time
import math
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

class ScalingDirection(Enum):
    """Scaling direction"""
    UP = "up"
    DOWN = "down"
    NONE = "none"

class ScalingTrigger(Enum):
    """Scaling trigger types"""
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    REQUEST_RATE = "request_rate"
    RESPONSE_TIME = "response_time"
    QUEUE_LENGTH = "queue_length"
    CUSTOM_METRIC = "custom_metric"

@dataclass
class ScalingMetric:
    """Scaling metric definition"""
    name: str
    trigger: ScalingTrigger
    threshold_up: float
    threshold_down: float
    evaluation_periods: int = 3
    cooldown_seconds: int = 300
    weight: float = 1.0

@dataclass
class ScalingPolicy:
    """Scaling policy definition"""
    name: str
    service_name: str
    min_instances: int
    max_instances: int
    metrics: List[ScalingMetric]
    scale_up_adjustment: int = 1
    scale_down_adjustment: int = 1
    enabled: bool = True

@dataclass
class ScalingEvent:
    """Scaling event record"""
    timestamp: float
    service_name: str
    direction: ScalingDirection
    from_instances: int
    to_instances: int
    trigger_metric: str
    trigger_value: float
    reason: str

class MetricsProvider(ABC):
    """Abstract metrics provider"""
    
    @abstractmethod
    async def get_metric(self, metric_name: str, service_name: str) -> float:
        """Get metric value for service"""
        pass

class ServiceScaler(ABC):
    """Abstract service scaler"""
    
    @abstractmethod
    async def get_current_instances(self, service_name: str) -> int:
        """Get current number of instances"""
        pass
    
    @abstractmethod
    async def scale_to(self, service_name: str, target_instances: int) -> bool:
        """Scale service to target number of instances"""
        pass

class AutoScaler:
    """Auto-scaling engine"""
    
    def __init__(self, metrics_provider: MetricsProvider, 
                 service_scaler: ServiceScaler):
        self.metrics_provider = metrics_provider
        self.service_scaler = service_scaler
        
        # Policies and state
        self.policies: Dict[str, ScalingPolicy] = {}
        self.metric_history: Dict[str, List[float]] = {}
        self.last_scaling_time: Dict[str, float] = {}
        self.scaling_events: List[ScalingEvent] = []
        
        # Configuration
        self.evaluation_interval = 30.0  # seconds
        self.max_events_history = 1000
        
        # Tasks
        self.scaling_task: Optional[asyncio.Task] = None
        self.running = False
        
        # Statistics
        self.stats = {
            'evaluations_performed': 0,
            'scale_up_events': 0,
            'scale_down_events': 0,
            'scaling_errors': 0,
            'policies_active': 0
        }
    
    def add_policy(self, policy: ScalingPolicy):
        """Add scaling policy"""
        self.policies[policy.service_name] = policy
        self.metric_history[policy.service_name] = []
        logger.info(f"Added scaling policy for {policy.service_name}")
    
    def remove_policy(self, service_name: str):
        """Remove scaling policy"""
        if service_name in self.policies:
            del self.policies[service_name]
            self.metric_history.pop(service_name, None)
            self.last_scaling_time.pop(service_name, None)
            logger.info(f"Removed scaling policy for {service_name}")
    
    def get_policy(self, service_name: str) -> Optional[ScalingPolicy]:
        """Get scaling policy"""
        return self.policies.get(service_name)
    
    def enable_policy(self, service_name: str):
        """Enable scaling policy"""
        if service_name in self.policies:
            self.policies[service_name].enabled = True
            logger.info(f"Enabled scaling policy for {service_name}")
    
    def disable_policy(self, service_name: str):
        """Disable scaling policy"""
        if service_name in self.policies:
            self.policies[service_name].enabled = False
            logger.info(f"Disabled scaling policy for {service_name}")
    
    async def start(self):
        """Start auto-scaling"""
        if self.running:
            return
        
        self.running = True
        self.scaling_task = asyncio.create_task(self._scaling_loop())
        logger.info("Auto-scaler started")
    
    async def stop(self):
        """Stop auto-scaling"""
        if not self.running:
            return
        
        self.running = False
        
        if self.scaling_task:
            self.scaling_task.cancel()
            try:
                await self.scaling_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Auto-scaler stopped")
    
    async def evaluate_scaling(self, service_name: str) -> Optional[ScalingDirection]:
        """Evaluate if scaling is needed for a service"""
        policy = self.policies.get(service_name)
        if not policy or not policy.enabled:
            return ScalingDirection.NONE
        
        # Check cooldown period
        last_scaling = self.last_scaling_time.get(service_name, 0)
        if time.time() - last_scaling < 300:  # 5 minute cooldown
            return ScalingDirection.NONE
        
        # Get current instances
        current_instances = await self.service_scaler.get_current_instances(service_name)
        
        # Evaluate each metric
        scale_up_votes = 0
        scale_down_votes = 0
        total_weight = 0
        
        for metric in policy.metrics:
            try:
                # Get metric value
                if metric.trigger == ScalingTrigger.CUSTOM_METRIC:
                    value = await self.metrics_provider.get_metric(metric.name, service_name)
                else:
                    value = await self._get_system_metric(metric.trigger, service_name)
                
                # Store in history
                history_key = f"{service_name}:{metric.name}"
                if history_key not in self.metric_history:
                    self.metric_history[history_key] = []
                
                self.metric_history[history_key].append(value)
                
                # Keep only recent history
                max_history = metric.evaluation_periods * 2
                if len(self.metric_history[history_key]) > max_history:
                    self.metric_history[history_key] = self.metric_history[history_key][-max_history:]
                
                # Check if we have enough data points
                if len(self.metric_history[history_key]) < metric.evaluation_periods:
                    continue
                
                # Calculate average over evaluation periods
                recent_values = self.metric_history[history_key][-metric.evaluation_periods:]
                avg_value = sum(recent_values) / len(recent_values)
                
                # Vote for scaling direction
                if avg_value > metric.threshold_up:
                    scale_up_votes += metric.weight
                elif avg_value < metric.threshold_down:
                    scale_down_votes += metric.weight
                
                total_weight += metric.weight
                
            except Exception as e:
                logger.error(f"Error evaluating metric {metric.name}: {e}")
        
        # Determine scaling direction
        if total_weight == 0:
            return ScalingDirection.NONE
        
        scale_up_ratio = scale_up_votes / total_weight
        scale_down_ratio = scale_down_votes / total_weight
        
        # Require majority vote for scaling
        if scale_up_ratio > 0.5 and current_instances < policy.max_instances:
            return ScalingDirection.UP
        elif scale_down_ratio > 0.5 and current_instances > policy.min_instances:
            return ScalingDirection.DOWN
        else:
            return ScalingDirection.NONE
    
    async def scale_service(self, service_name: str, direction: ScalingDirection) -> bool:
        """Scale a service"""
        policy = self.policies.get(service_name)
        if not policy:
            return False
        
        current_instances = await self.service_scaler.get_current_instances(service_name)
        
        if direction == ScalingDirection.UP:
            target_instances = min(
                current_instances + policy.scale_up_adjustment,
                policy.max_instances
            )
        elif direction == ScalingDirection.DOWN:
            target_instances = max(
                current_instances - policy.scale_down_adjustment,
                policy.min_instances
            )
        else:
            return False
        
        if target_instances == current_instances:
            return False
        
        try:
            success = await self.service_scaler.scale_to(service_name, target_instances)
            
            if success:
                # Record scaling event
                event = ScalingEvent(
                    timestamp=time.time(),
                    service_name=service_name,
                    direction=direction,
                    from_instances=current_instances,
                    to_instances=target_instances,
                    trigger_metric="multiple",
                    trigger_value=0.0,
                    reason=f"Auto-scaling {direction.value}"
                )
                
                self.scaling_events.append(event)
                
                # Maintain event history limit
                if len(self.scaling_events) > self.max_events_history:
                    self.scaling_events = self.scaling_events[-self.max_events_history:]
                
                # Update statistics
                if direction == ScalingDirection.UP:
                    self.stats['scale_up_events'] += 1
                else:
                    self.stats['scale_down_events'] += 1
                
                # Update last scaling time
                self.last_scaling_time[service_name] = time.time()
                
                logger.info(f"Scaled {service_name} {direction.value}: {current_instances} -> {target_instances}")
                
            return success
            
        except Exception as e:
            logger.error(f"Failed to scale {service_name}: {e}")
            self.stats['scaling_errors'] += 1
            return False
    
    async def _scaling_loop(self):
        """Main scaling evaluation loop"""
        while self.running:
            try:
                # Update active policies count
                self.stats['policies_active'] = len([p for p in self.policies.values() if p.enabled])
                
                # Evaluate each service
                for service_name, policy in self.policies.items():
                    if not policy.enabled:
                        continue
                    
                    try:
                        direction = await self.evaluate_scaling(service_name)
                        
                        if direction != ScalingDirection.NONE:
                            await self.scale_service(service_name, direction)
                        
                        self.stats['evaluations_performed'] += 1
                        
                    except Exception as e:
                        logger.error(f"Error evaluating scaling for {service_name}: {e}")
                
                await asyncio.sleep(self.evaluation_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scaling loop error: {e}")
                await asyncio.sleep(self.evaluation_interval)
    
    async def _get_system_metric(self, trigger: ScalingTrigger, service_name: str) -> float:
        """Get system metric value"""
        if trigger == ScalingTrigger.CPU_USAGE:
            return await self.metrics_provider.get_metric("cpu_percent", service_name)
        elif trigger == ScalingTrigger.MEMORY_USAGE:
            return await self.metrics_provider.get_metric("memory_percent", service_name)
        elif trigger == ScalingTrigger.REQUEST_RATE:
            return await self.metrics_provider.get_metric("requests_per_second", service_name)
        elif trigger == ScalingTrigger.RESPONSE_TIME:
            return await self.metrics_provider.get_metric("avg_response_time", service_name)
        elif trigger == ScalingTrigger.QUEUE_LENGTH:
            return await self.metrics_provider.get_metric("queue_length", service_name)
        else:
            return 0.0
    
    def get_scaling_history(self, service_name: str = None, 
                           limit: int = 100) -> List[ScalingEvent]:
        """Get scaling history"""
        events = self.scaling_events
        
        if service_name:
            events = [e for e in events if e.service_name == service_name]
        
        return events[-limit:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get auto-scaler statistics"""
        return {
            **self.stats,
            'policies_total': len(self.policies),
            'services_monitored': list(self.policies.keys()),
            'recent_events': len(self.scaling_events),
            'timestamp': time.time()
        }

class PrometheusMetricsProvider(MetricsProvider):
    """Prometheus metrics provider"""
    
    def __init__(self, prometheus_url: str):
        self.prometheus_url = prometheus_url
    
    async def get_metric(self, metric_name: str, service_name: str) -> float:
        """Get metric from Prometheus"""
        try:
            import aiohttp
            
            # Build Prometheus query
            query = f'{metric_name}{{service="{service_name}"}}'
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.prometheus_url}/api/v1/query"
                params = {'query': query}
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data['status'] == 'success' and data['data']['result']:
                            return float(data['data']['result'][0]['value'][1])
                        else:
                            return 0.0
                    else:
                        logger.error(f"Prometheus query failed: {response.status}")
                        return 0.0
                        
        except Exception as e:
            logger.error(f"Error getting metric from Prometheus: {e}")
            return 0.0

class KubernetesServiceScaler(ServiceScaler):
    """Kubernetes service scaler"""
    
    def __init__(self, namespace: str = "default"):
        self.namespace = namespace
    
    async def get_current_instances(self, service_name: str) -> int:
        """Get current number of instances from Kubernetes"""
        try:
            # This would use kubernetes client library
            # For now, return mock value
            return 3
            
        except Exception as e:
            logger.error(f"Error getting instances for {service_name}: {e}")
            return 0
    
    async def scale_to(self, service_name: str, target_instances: int) -> bool:
        """Scale Kubernetes deployment"""
        try:
            # This would use kubernetes client to scale deployment
            # kubectl scale deployment {service_name} --replicas={target_instances}
            logger.info(f"Would scale {service_name} to {target_instances} instances")
            return True
            
        except Exception as e:
            logger.error(f"Error scaling {service_name}: {e}")
            return False

class DockerServiceScaler(ServiceScaler):
    """Docker service scaler"""
    
    def __init__(self):
        pass
    
    async def get_current_instances(self, service_name: str) -> int:
        """Get current number of Docker containers"""
        try:
            # This would use docker client
            return 2
            
        except Exception as e:
            logger.error(f"Error getting Docker instances for {service_name}: {e}")
            return 0
    
    async def scale_to(self, service_name: str, target_instances: int) -> bool:
        """Scale Docker service"""
        try:
            # This would use docker client to scale service
            logger.info(f"Would scale Docker service {service_name} to {target_instances}")
            return True
            
        except Exception as e:
            logger.error(f"Error scaling Docker service {service_name}: {e}")
            return False

class PredictiveScaler:
    """Predictive auto-scaler using historical data"""
    
    def __init__(self, auto_scaler: AutoScaler):
        self.auto_scaler = auto_scaler
        self.prediction_window = 300  # 5 minutes
        self.learning_enabled = True
    
    async def predict_scaling_need(self, service_name: str) -> Optional[ScalingDirection]:
        """Predict future scaling needs"""
        policy = self.auto_scaler.get_policy(service_name)
        if not policy:
            return None
        
        # Analyze historical patterns
        current_time = time.time()
        
        # Get recent scaling events
        recent_events = [
            event for event in self.auto_scaler.scaling_events
            if (event.service_name == service_name and 
                current_time - event.timestamp < 3600)  # Last hour
        ]
        
        if len(recent_events) < 2:
            return None
        
        # Simple trend analysis
        scale_up_count = len([e for e in recent_events if e.direction == ScalingDirection.UP])
        scale_down_count = len([e for e in recent_events if e.direction == ScalingDirection.DOWN])
        
        # Predict based on recent trend
        if scale_up_count > scale_down_count * 2:
            return ScalingDirection.UP
        elif scale_down_count > scale_up_count * 2:
            return ScalingDirection.DOWN
        else:
            return None
    
    async def apply_predictive_scaling(self, service_name: str):
        """Apply predictive scaling"""
        prediction = await self.predict_scaling_need(service_name)
        
        if prediction and prediction != ScalingDirection.NONE:
            logger.info(f"Predictive scaling recommendation for {service_name}: {prediction.value}")
            
            # Apply with reduced adjustment to be conservative
            policy = self.auto_scaler.get_policy(service_name)
            if policy:
                # Reduce scaling adjustment for predictive scaling
                original_up = policy.scale_up_adjustment
                original_down = policy.scale_down_adjustment
                
                policy.scale_up_adjustment = max(1, original_up // 2)
                policy.scale_down_adjustment = max(1, original_down // 2)
                
                try:
                    await self.auto_scaler.scale_service(service_name, prediction)
                finally:
                    # Restore original adjustments
                    policy.scale_up_adjustment = original_up
                    policy.scale_down_adjustment = original_down