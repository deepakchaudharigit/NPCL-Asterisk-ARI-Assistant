"""
Scalability module for Voice Assistant
Provides horizontal scaling, load balancing, and clustering capabilities
"""

from .load_balancer import LoadBalancer, RoundRobinBalancer, WeightedBalancer
from .cluster_manager import ClusterManager, NodeManager
from .auto_scaler import AutoScaler, ScalingPolicy
from .service_discovery import ServiceDiscovery, ConsulServiceDiscovery
from .database_cluster import DatabaseCluster, RedisCluster

__all__ = [
    'LoadBalancer',
    'RoundRobinBalancer', 
    'WeightedBalancer',
    'ClusterManager',
    'NodeManager',
    'AutoScaler',
    'ScalingPolicy',
    'ServiceDiscovery',
    'ConsulServiceDiscovery',
    'DatabaseCluster',
    'RedisCluster'
]