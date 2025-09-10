"""
Cluster Management for Distributed Voice Assistant
Manages multiple nodes and coordinates distributed operations
"""

import asyncio
import time
import json
import uuid
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging
import aiohttp
import socket

logger = logging.getLogger(__name__)

class NodeRole(Enum):
    """Node roles in the cluster"""
    LEADER = "leader"
    FOLLOWER = "follower"
    CANDIDATE = "candidate"

class NodeState(Enum):
    """Node states"""
    STARTING = "starting"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    LEAVING = "leaving"
    LEFT = "left"

@dataclass
class ClusterNode:
    """Represents a node in the cluster"""
    id: str
    host: str
    port: int
    role: NodeRole = NodeRole.FOLLOWER
    state: NodeState = NodeState.STARTING
    last_heartbeat: float = field(default_factory=time.time)
    term: int = 0
    vote_count: int = 0
    capabilities: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def address(self) -> str:
        """Get node address"""
        return f"{self.host}:{self.port}"
    
    @property
    def is_alive(self) -> bool:
        """Check if node is alive based on heartbeat"""
        return time.time() - self.last_heartbeat < 30.0  # 30 second timeout

@dataclass
class ClusterEvent:
    """Cluster event"""
    event_type: str
    node_id: str
    timestamp: float = field(default_factory=time.time)
    data: Dict[str, Any] = field(default_factory=dict)

class ClusterManager:
    """Manages cluster membership and coordination"""
    
    def __init__(self, node_id: str, host: str, port: int):
        self.node_id = node_id
        self.host = host
        self.port = port
        
        # Cluster state
        self.nodes: Dict[str, ClusterNode] = {}
        self.current_term = 0
        self.voted_for: Optional[str] = None
        self.role = NodeRole.FOLLOWER
        self.leader_id: Optional[str] = None
        
        # Configuration
        self.heartbeat_interval = 5.0
        self.election_timeout = 15.0
        self.heartbeat_timeout = 30.0
        
        # Tasks
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.election_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        
        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = {}
        
        # Statistics
        self.stats = {
            'elections_started': 0,
            'elections_won': 0,
            'heartbeats_sent': 0,
            'heartbeats_received': 0,
            'nodes_joined': 0,
            'nodes_left': 0
        }
        
        # Add self to cluster
        self.nodes[self.node_id] = ClusterNode(
            id=self.node_id,
            host=self.host,
            port=self.port,
            state=NodeState.HEALTHY
        )
    
    async def start(self):
        """Start cluster manager"""
        logger.info(f"Starting cluster manager for node {self.node_id}")
        
        # Start background tasks
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self.election_task = asyncio.create_task(self._election_loop())
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        # Emit node joined event
        await self._emit_event("node_joined", self.node_id, {"address": f"{self.host}:{self.port}"})
    
    async def stop(self):
        """Stop cluster manager"""
        logger.info(f"Stopping cluster manager for node {self.node_id}")
        
        # Mark as leaving
        if self.node_id in self.nodes:
            self.nodes[self.node_id].state = NodeState.LEAVING
        
        # Notify other nodes
        await self._broadcast_leave()
        
        # Cancel tasks
        for task in [self.heartbeat_task, self.election_task, self.cleanup_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Emit node left event
        await self._emit_event("node_left", self.node_id)
    
    async def join_cluster(self, seed_nodes: List[str]):
        """Join an existing cluster"""
        logger.info(f"Joining cluster with seed nodes: {seed_nodes}")
        
        for seed_address in seed_nodes:
            try:
                host, port = seed_address.split(':')
                await self._send_join_request(host, int(port))
                break
            except Exception as e:
                logger.warning(f"Failed to join via {seed_address}: {e}")
        
        self.stats['nodes_joined'] += 1
    
    async def add_node(self, node: ClusterNode):
        """Add a node to the cluster"""
        self.nodes[node.id] = node
        logger.info(f"Added node {node.id} at {node.address}")
        
        await self._emit_event("node_added", node.id, {"address": node.address})
    
    async def remove_node(self, node_id: str):
        """Remove a node from the cluster"""
        if node_id in self.nodes:
            node = self.nodes[node_id]
            node.state = NodeState.LEFT
            
            # If removing leader, trigger election
            if node_id == self.leader_id:
                self.leader_id = None
                await self._start_election()
            
            del self.nodes[node_id]
            logger.info(f"Removed node {node_id}")
            
            await self._emit_event("node_removed", node_id)
            self.stats['nodes_left'] += 1
    
    async def get_leader(self) -> Optional[ClusterNode]:
        """Get current cluster leader"""
        if self.leader_id and self.leader_id in self.nodes:
            return self.nodes[self.leader_id]
        return None
    
    async def is_leader(self) -> bool:
        """Check if this node is the leader"""
        return self.role == NodeRole.LEADER
    
    async def get_cluster_size(self) -> int:
        """Get cluster size"""
        return len([node for node in self.nodes.values() if node.state == NodeState.HEALTHY])
    
    async def get_healthy_nodes(self) -> List[ClusterNode]:
        """Get all healthy nodes"""
        return [
            node for node in self.nodes.values() 
            if node.state == NodeState.HEALTHY and node.is_alive
        ]
    
    async def broadcast_message(self, message_type: str, data: Dict[str, Any]):
        """Broadcast message to all nodes"""
        healthy_nodes = await self.get_healthy_nodes()
        
        tasks = []
        for node in healthy_nodes:
            if node.id != self.node_id:  # Don't send to self
                task = asyncio.create_task(
                    self._send_message(node, message_type, data)
                )
                tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def add_event_handler(self, event_type: str, handler: Callable):
        """Add event handler"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    async def _heartbeat_loop(self):
        """Heartbeat loop"""
        while True:
            try:
                if self.role == NodeRole.LEADER:
                    await self._send_heartbeats()
                
                await asyncio.sleep(self.heartbeat_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")
                await asyncio.sleep(self.heartbeat_interval)
    
    async def _election_loop(self):
        """Election timeout loop"""
        while True:
            try:
                if self.role == NodeRole.FOLLOWER:
                    # Check if we've received heartbeat from leader recently
                    if self.leader_id:
                        leader_node = self.nodes.get(self.leader_id)
                        if not leader_node or not leader_node.is_alive:
                            logger.info("Leader appears to be down, starting election")
                            await self._start_election()
                    else:
                        # No leader, start election
                        await self._start_election()
                
                # Random election timeout to avoid split votes
                timeout = self.election_timeout + (time.time() % 5)
                await asyncio.sleep(timeout)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Election loop error: {e}")
                await asyncio.sleep(self.election_timeout)
    
    async def _cleanup_loop(self):
        """Cleanup dead nodes"""
        while True:
            try:
                current_time = time.time()
                dead_nodes = []
                
                for node_id, node in self.nodes.items():
                    if (node_id != self.node_id and 
                        current_time - node.last_heartbeat > self.heartbeat_timeout):
                        dead_nodes.append(node_id)
                
                for node_id in dead_nodes:
                    logger.warning(f"Node {node_id} appears dead, removing from cluster")
                    await self.remove_node(node_id)
                
                await asyncio.sleep(10)  # Cleanup every 10 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
                await asyncio.sleep(10)
    
    async def _send_heartbeats(self):
        """Send heartbeats to all followers"""
        healthy_nodes = await self.get_healthy_nodes()
        
        heartbeat_data = {
            'term': self.current_term,
            'leader_id': self.node_id,
            'timestamp': time.time()
        }
        
        tasks = []
        for node in healthy_nodes:
            if node.id != self.node_id:
                task = asyncio.create_task(
                    self._send_message(node, 'heartbeat', heartbeat_data)
                )
                tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            self.stats['heartbeats_sent'] += len(tasks)
    
    async def _start_election(self):
        """Start leader election"""
        if self.role == NodeRole.LEADER:
            return
        
        logger.info(f"Starting election for term {self.current_term + 1}")
        
        self.current_term += 1
        self.role = NodeRole.CANDIDATE
        self.voted_for = self.node_id
        self.stats['elections_started'] += 1
        
        # Vote for self
        vote_count = 1
        
        # Request votes from other nodes
        healthy_nodes = await self.get_healthy_nodes()
        vote_tasks = []
        
        for node in healthy_nodes:
            if node.id != self.node_id:
                task = asyncio.create_task(self._request_vote(node))
                vote_tasks.append(task)
        
        if vote_tasks:
            votes = await asyncio.gather(*vote_tasks, return_exceptions=True)
            vote_count += sum(1 for vote in votes if vote is True)
        
        # Check if we won the election
        cluster_size = len(healthy_nodes)
        majority = (cluster_size // 2) + 1
        
        if vote_count >= majority:
            await self._become_leader()
        else:
            self.role = NodeRole.FOLLOWER
            self.voted_for = None
    
    async def _become_leader(self):
        """Become cluster leader"""
        logger.info(f"Became leader for term {self.current_term}")
        
        self.role = NodeRole.LEADER
        self.leader_id = self.node_id
        self.stats['elections_won'] += 1
        
        # Send immediate heartbeat to establish leadership
        await self._send_heartbeats()
        
        await self._emit_event("leader_elected", self.node_id, {"term": self.current_term})
    
    async def _request_vote(self, node: ClusterNode) -> bool:
        """Request vote from a node"""
        try:
            vote_data = {
                'term': self.current_term,
                'candidate_id': self.node_id,
                'last_log_index': 0,  # Simplified for now
                'last_log_term': 0
            }
            
            response = await self._send_message(node, 'vote_request', vote_data)
            return response.get('vote_granted', False)
            
        except Exception as e:
            logger.warning(f"Failed to request vote from {node.address}: {e}")
            return False
    
    async def _send_message(self, node: ClusterNode, message_type: str, 
                           data: Dict[str, Any]) -> Dict[str, Any]:
        """Send message to a node"""
        try:
            message = {
                'type': message_type,
                'from': self.node_id,
                'term': self.current_term,
                'data': data
            }
            
            async with aiohttp.ClientSession() as session:
                url = f"http://{node.address}/cluster/message"
                
                async with session.post(url, json=message, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.warning(f"Message to {node.address} failed: {response.status}")
                        return {}
                        
        except Exception as e:
            logger.warning(f"Failed to send message to {node.address}: {e}")
            return {}
    
    async def _send_join_request(self, host: str, port: int):
        """Send join request to a node"""
        try:
            join_data = {
                'node_id': self.node_id,
                'host': self.host,
                'port': self.port,
                'capabilities': list(self.nodes[self.node_id].capabilities)
            }
            
            async with aiohttp.ClientSession() as session:
                url = f"http://{host}:{port}/cluster/join"
                
                async with session.post(url, json=join_data, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        cluster_info = await response.json()
                        await self._process_cluster_info(cluster_info)
                        logger.info(f"Successfully joined cluster via {host}:{port}")
                    else:
                        raise Exception(f"Join request failed: {response.status}")
                        
        except Exception as e:
            logger.error(f"Failed to join via {host}:{port}: {e}")
            raise
    
    async def _process_cluster_info(self, cluster_info: Dict[str, Any]):
        """Process cluster information received during join"""
        # Update cluster state
        if 'nodes' in cluster_info:
            for node_data in cluster_info['nodes']:
                node = ClusterNode(**node_data)
                self.nodes[node.id] = node
        
        if 'leader_id' in cluster_info:
            self.leader_id = cluster_info['leader_id']
        
        if 'term' in cluster_info:
            self.current_term = cluster_info['term']
    
    async def _broadcast_leave(self):
        """Broadcast leave message to cluster"""
        leave_data = {
            'node_id': self.node_id,
            'reason': 'graceful_shutdown'
        }
        
        await self.broadcast_message('node_leave', leave_data)
    
    async def _emit_event(self, event_type: str, node_id: str, data: Dict[str, Any] = None):
        """Emit cluster event"""
        event = ClusterEvent(
            event_type=event_type,
            node_id=node_id,
            data=data or {}
        )
        
        # Call event handlers
        handlers = self.event_handlers.get(event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Event handler error: {e}")
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """Get cluster status"""
        healthy_nodes = [node for node in self.nodes.values() if node.state == NodeState.HEALTHY]
        
        return {
            'node_id': self.node_id,
            'role': self.role.value,
            'term': self.current_term,
            'leader_id': self.leader_id,
            'cluster_size': len(healthy_nodes),
            'nodes': [
                {
                    'id': node.id,
                    'address': node.address,
                    'role': node.role.value,
                    'state': node.state.value,
                    'last_heartbeat': node.last_heartbeat,
                    'is_alive': node.is_alive
                }
                for node in self.nodes.values()
            ],
            'statistics': self.stats,
            'timestamp': time.time()
        }

class NodeManager:
    """Manages individual node operations"""
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.capabilities: Set[str] = set()
        self.services: Dict[str, Any] = {}
        self.resources = {
            'cpu_cores': self._get_cpu_cores(),
            'memory_gb': self._get_memory_gb(),
            'disk_gb': self._get_disk_gb()
        }
    
    def add_capability(self, capability: str):
        """Add node capability"""
        self.capabilities.add(capability)
        logger.info(f"Added capability: {capability}")
    
    def remove_capability(self, capability: str):
        """Remove node capability"""
        self.capabilities.discard(capability)
        logger.info(f"Removed capability: {capability}")
    
    def register_service(self, service_name: str, service_instance: Any):
        """Register a service on this node"""
        self.services[service_name] = service_instance
        logger.info(f"Registered service: {service_name}")
    
    def unregister_service(self, service_name: str):
        """Unregister a service"""
        if service_name in self.services:
            del self.services[service_name]
            logger.info(f"Unregistered service: {service_name}")
    
    def get_service(self, service_name: str) -> Any:
        """Get service instance"""
        return self.services.get(service_name)
    
    def get_node_info(self) -> Dict[str, Any]:
        """Get node information"""
        return {
            'node_id': self.node_id,
            'capabilities': list(self.capabilities),
            'services': list(self.services.keys()),
            'resources': self.resources,
            'timestamp': time.time()
        }
    
    def _get_cpu_cores(self) -> int:
        """Get number of CPU cores"""
        try:
            import multiprocessing
            return multiprocessing.cpu_count()
        except:
            return 1
    
    def _get_memory_gb(self) -> float:
        """Get memory in GB"""
        try:
            import psutil
            return psutil.virtual_memory().total / (1024**3)
        except:
            return 1.0
    
    def _get_disk_gb(self) -> float:
        """Get disk space in GB"""
        try:
            import psutil
            return psutil.disk_usage('/').total / (1024**3)
        except:
            return 10.0