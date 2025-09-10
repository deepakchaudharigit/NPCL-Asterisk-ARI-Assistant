"""
Load Balancing Implementation
Provides various load balancing strategies for horizontal scaling
"""

import asyncio
import time
import random
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum
import logging
import aiohttp
import hashlib

logger = logging.getLogger(__name__)

class NodeStatus(Enum):
    """Node status"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DRAINING = "draining"
    MAINTENANCE = "maintenance"

@dataclass
class ServiceNode:
    """Represents a service node"""
    id: str
    host: str
    port: int
    weight: int = 1
    status: NodeStatus = NodeStatus.HEALTHY
    current_connections: int = 0
    max_connections: int = 1000
    response_time: float = 0.0
    error_count: int = 0
    last_health_check: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def address(self) -> str:
        """Get node address"""
        return f"{self.host}:{self.port}"
    
    @property
    def url(self) -> str:
        """Get node URL"""
        return f"http://{self.host}:{self.port}"
    
    @property
    def load_factor(self) -> float:
        """Calculate current load factor (0.0 to 1.0)"""
        if self.max_connections == 0:
            return 0.0
        return self.current_connections / self.max_connections
    
    def is_available(self) -> bool:
        """Check if node is available for requests"""
        return (self.status == NodeStatus.HEALTHY and 
                self.current_connections < self.max_connections)

class LoadBalancer(ABC):
    """Abstract base class for load balancers"""
    
    def __init__(self):
        self.nodes: List[ServiceNode] = []
        self.health_check_interval = 30.0
        self.health_check_timeout = 5.0
        self.health_check_task: Optional[asyncio.Task] = None
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'nodes_count': 0,
            'healthy_nodes': 0
        }
    
    def add_node(self, node: ServiceNode):
        """Add a node to the load balancer"""
        self.nodes.append(node)
        self.stats['nodes_count'] = len(self.nodes)
        logger.info(f"Added node: {node.address}")
    
    def remove_node(self, node_id: str):
        """Remove a node from the load balancer"""
        self.nodes = [node for node in self.nodes if node.id != node_id]
        self.stats['nodes_count'] = len(self.nodes)
        logger.info(f"Removed node: {node_id}")
    
    def get_node(self, node_id: str) -> Optional[ServiceNode]:
        """Get a node by ID"""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None
    
    def get_healthy_nodes(self) -> List[ServiceNode]:
        """Get all healthy nodes"""
        healthy = [node for node in self.nodes if node.is_available()]
        self.stats['healthy_nodes'] = len(healthy)
        return healthy
    
    @abstractmethod
    def select_node(self, request_context: Dict[str, Any] = None) -> Optional[ServiceNode]:
        """Select a node for the request"""
        pass
    
    async def forward_request(self, method: str, path: str, 
                            headers: Dict[str, str] = None,
                            data: Any = None,
                            request_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Forward request to selected node"""
        node = self.select_node(request_context)
        
        if not node:
            self.stats['failed_requests'] += 1
            raise Exception("No healthy nodes available")
        
        self.stats['total_requests'] += 1
        node.current_connections += 1
        
        try:
            start_time = time.time()
            
            async with aiohttp.ClientSession() as session:
                url = f"{node.url}{path}"
                
                async with session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data if data else None,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    response_data = await response.json()
                    
                    # Update node metrics
                    response_time = time.time() - start_time
                    node.response_time = response_time
                    
                    if response.status >= 400:
                        node.error_count += 1
                        self.stats['failed_requests'] += 1
                    else:
                        self.stats['successful_requests'] += 1
                    
                    return {
                        'status': response.status,
                        'data': response_data,
                        'node_id': node.id,
                        'response_time': response_time
                    }
                    
        except Exception as e:
            node.error_count += 1
            self.stats['failed_requests'] += 1
            logger.error(f"Request failed to node {node.address}: {e}")
            raise
        finally:
            node.current_connections -= 1
    
    async def start_health_checks(self):
        """Start health check monitoring"""
        if self.health_check_task is None:
            self.health_check_task = asyncio.create_task(self._health_check_loop())
            logger.info("Started health check monitoring")
    
    async def stop_health_checks(self):
        """Stop health check monitoring"""
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
            self.health_check_task = None
            logger.info("Stopped health check monitoring")
    
    async def _health_check_loop(self):
        """Health check loop"""
        while True:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(self.health_check_interval)
    
    async def _perform_health_checks(self):
        """Perform health checks on all nodes"""
        tasks = []
        for node in self.nodes:
            task = asyncio.create_task(self._check_node_health(node))
            tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _check_node_health(self, node: ServiceNode):
        """Check health of a single node"""
        try:
            async with aiohttp.ClientSession() as session:
                health_url = f"{node.url}/health"
                
                async with session.get(
                    health_url,
                    timeout=aiohttp.ClientTimeout(total=self.health_check_timeout)
                ) as response:
                    if response.status == 200:
                        if node.status == NodeStatus.UNHEALTHY:
                            logger.info(f"Node {node.address} is now healthy")
                        node.status = NodeStatus.HEALTHY
                        node.error_count = max(0, node.error_count - 1)
                    else:
                        node.status = NodeStatus.UNHEALTHY
                        node.error_count += 1
                        
        except Exception as e:
            logger.warning(f"Health check failed for node {node.address}: {e}")
            node.status = NodeStatus.UNHEALTHY
            node.error_count += 1
        
        node.last_health_check = time.time()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get load balancer statistics"""
        return {
            **self.stats,
            'nodes': [
                {
                    'id': node.id,
                    'address': node.address,
                    'status': node.status.value,
                    'current_connections': node.current_connections,
                    'load_factor': node.load_factor,
                    'response_time': node.response_time,
                    'error_count': node.error_count
                }
                for node in self.nodes
            ],
            'timestamp': time.time()
        }

class RoundRobinBalancer(LoadBalancer):
    """Round-robin load balancer"""
    
    def __init__(self):
        super().__init__()
        self.current_index = 0
    
    def select_node(self, request_context: Dict[str, Any] = None) -> Optional[ServiceNode]:
        """Select node using round-robin algorithm"""
        healthy_nodes = self.get_healthy_nodes()
        
        if not healthy_nodes:
            return None
        
        # Round-robin selection
        node = healthy_nodes[self.current_index % len(healthy_nodes)]
        self.current_index += 1
        
        return node

class WeightedBalancer(LoadBalancer):
    """Weighted round-robin load balancer"""
    
    def __init__(self):
        super().__init__()
        self.current_weights: Dict[str, int] = {}
    
    def select_node(self, request_context: Dict[str, Any] = None) -> Optional[ServiceNode]:
        """Select node using weighted round-robin algorithm"""
        healthy_nodes = self.get_healthy_nodes()
        
        if not healthy_nodes:
            return None
        
        # Initialize weights if needed
        for node in healthy_nodes:
            if node.id not in self.current_weights:
                self.current_weights[node.id] = 0
        
        # Find node with highest current weight
        selected_node = None
        max_weight = -1
        
        for node in healthy_nodes:
            self.current_weights[node.id] += node.weight
            
            if self.current_weights[node.id] > max_weight:
                max_weight = self.current_weights[node.id]
                selected_node = node
        
        # Reduce selected node's current weight
        if selected_node:
            total_weight = sum(node.weight for node in healthy_nodes)
            self.current_weights[selected_node.id] -= total_weight
        
        return selected_node

class LeastConnectionsBalancer(LoadBalancer):
    """Least connections load balancer"""
    
    def select_node(self, request_context: Dict[str, Any] = None) -> Optional[ServiceNode]:
        """Select node with least connections"""
        healthy_nodes = self.get_healthy_nodes()
        
        if not healthy_nodes:
            return None
        
        # Select node with minimum connections
        return min(healthy_nodes, key=lambda node: node.current_connections)

class ConsistentHashBalancer(LoadBalancer):
    """Consistent hash load balancer"""
    
    def __init__(self, virtual_nodes: int = 150):
        super().__init__()
        self.virtual_nodes = virtual_nodes
        self.hash_ring: Dict[int, ServiceNode] = {}
        self._rebuild_hash_ring()
    
    def add_node(self, node: ServiceNode):
        """Add node and rebuild hash ring"""
        super().add_node(node)
        self._rebuild_hash_ring()
    
    def remove_node(self, node_id: str):
        """Remove node and rebuild hash ring"""
        super().remove_node(node_id)
        self._rebuild_hash_ring()
    
    def select_node(self, request_context: Dict[str, Any] = None) -> Optional[ServiceNode]:
        """Select node using consistent hashing"""
        healthy_nodes = self.get_healthy_nodes()
        
        if not healthy_nodes:
            return None
        
        # Get hash key from request context
        hash_key = self._get_hash_key(request_context)
        hash_value = self._hash(hash_key)
        
        # Find the first node in the ring
        for ring_hash in sorted(self.hash_ring.keys()):
            if ring_hash >= hash_value:
                node = self.hash_ring[ring_hash]
                if node in healthy_nodes:
                    return node
        
        # Wrap around to the first node
        if self.hash_ring:
            first_hash = min(self.hash_ring.keys())
            node = self.hash_ring[first_hash]
            if node in healthy_nodes:
                return node
        
        return None
    
    def _rebuild_hash_ring(self):
        """Rebuild the hash ring"""
        self.hash_ring.clear()
        
        for node in self.nodes:
            for i in range(self.virtual_nodes):
                virtual_key = f"{node.id}:{i}"
                hash_value = self._hash(virtual_key)
                self.hash_ring[hash_value] = node
    
    def _get_hash_key(self, request_context: Dict[str, Any] = None) -> str:
        """Get hash key from request context"""
        if not request_context:
            return str(time.time())
        
        # Use session ID, user ID, or IP address for consistent routing
        for key in ['session_id', 'user_id', 'ip_address']:
            if key in request_context:
                return str(request_context[key])
        
        return str(time.time())
    
    def _hash(self, key: str) -> int:
        """Hash function"""
        return int(hashlib.md5(key.encode()).hexdigest(), 16)

class IPHashBalancer(LoadBalancer):
    """IP hash load balancer"""
    
    def select_node(self, request_context: Dict[str, Any] = None) -> Optional[ServiceNode]:
        """Select node based on client IP hash"""
        healthy_nodes = self.get_healthy_nodes()
        
        if not healthy_nodes:
            return None
        
        # Get client IP from request context
        client_ip = request_context.get('ip_address', '127.0.0.1') if request_context else '127.0.0.1'
        
        # Hash IP and select node
        hash_value = hash(client_ip)
        index = hash_value % len(healthy_nodes)
        
        return healthy_nodes[index]

class AdaptiveBalancer(LoadBalancer):
    """Adaptive load balancer that considers multiple factors"""
    
    def __init__(self):
        super().__init__()
        self.response_time_weight = 0.4
        self.connection_weight = 0.3
        self.error_rate_weight = 0.3
    
    def select_node(self, request_context: Dict[str, Any] = None) -> Optional[ServiceNode]:
        """Select node using adaptive algorithm"""
        healthy_nodes = self.get_healthy_nodes()
        
        if not healthy_nodes:
            return None
        
        if len(healthy_nodes) == 1:
            return healthy_nodes[0]
        
        # Calculate scores for each node
        node_scores = []
        
        for node in healthy_nodes:
            score = self._calculate_node_score(node, healthy_nodes)
            node_scores.append((score, node))
        
        # Select node with best score (lowest is better)
        node_scores.sort(key=lambda x: x[0])
        return node_scores[0][1]
    
    def _calculate_node_score(self, node: ServiceNode, all_nodes: List[ServiceNode]) -> float:
        """Calculate node score (lower is better)"""
        # Normalize response time
        max_response_time = max(n.response_time for n in all_nodes) or 1
        response_score = node.response_time / max_response_time
        
        # Normalize connection load
        connection_score = node.load_factor
        
        # Calculate error rate
        total_requests = max(node.error_count + 100, 1)  # Avoid division by zero
        error_rate = node.error_count / total_requests
        
        # Weighted score
        score = (
            response_score * self.response_time_weight +
            connection_score * self.connection_weight +
            error_rate * self.error_rate_weight
        )
        
        return score

class LoadBalancerFactory:
    """Factory for creating load balancers"""
    
    @staticmethod
    def create_balancer(balancer_type: str, **kwargs) -> LoadBalancer:
        """Create load balancer by type"""
        balancer_types = {
            'round_robin': RoundRobinBalancer,
            'weighted': WeightedBalancer,
            'least_connections': LeastConnectionsBalancer,
            'consistent_hash': ConsistentHashBalancer,
            'ip_hash': IPHashBalancer,
            'adaptive': AdaptiveBalancer
        }
        
        if balancer_type not in balancer_types:
            raise ValueError(f"Unknown balancer type: {balancer_type}")
        
        return balancer_types[balancer_type](**kwargs)