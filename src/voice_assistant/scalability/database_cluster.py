"""
Database Clustering Implementation
Provides database clustering and replication for scalability
"""

import asyncio
import time
import json
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import logging
import hashlib

try:
    import redis
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    import asyncpg
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

logger = logging.getLogger(__name__)

class NodeRole(Enum):
    """Database node roles"""
    PRIMARY = "primary"
    REPLICA = "replica"
    STANDBY = "standby"

class NodeStatus(Enum):
    """Database node status"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    SYNCING = "syncing"
    MAINTENANCE = "maintenance"

@dataclass
class DatabaseNode:
    """Database node information"""
    id: str
    host: str
    port: int
    role: NodeRole
    status: NodeStatus = NodeStatus.HEALTHY
    lag_bytes: int = 0
    last_heartbeat: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def address(self) -> str:
        """Get node address"""
        return f"{self.host}:{self.port}"
    
    @property
    def is_healthy(self) -> bool:
        """Check if node is healthy"""
        return (self.status == NodeStatus.HEALTHY and 
                time.time() - self.last_heartbeat < 30)

class DatabaseCluster(ABC):
    """Abstract database cluster interface"""
    
    @abstractmethod
    async def add_node(self, node: DatabaseNode) -> bool:
        """Add node to cluster"""
        pass
    
    @abstractmethod
    async def remove_node(self, node_id: str) -> bool:
        """Remove node from cluster"""
        pass
    
    @abstractmethod
    async def get_primary_node(self) -> Optional[DatabaseNode]:
        """Get primary node"""
        pass
    
    @abstractmethod
    async def get_replica_nodes(self) -> List[DatabaseNode]:
        """Get replica nodes"""
        pass
    
    @abstractmethod
    async def failover(self, new_primary_id: str) -> bool:
        """Perform failover to new primary"""
        pass
    
    @abstractmethod
    async def get_cluster_status(self) -> Dict[str, Any]:
        """Get cluster status"""
        pass

class RedisCluster(DatabaseCluster):
    """Redis cluster implementation"""
    
    def __init__(self):
        if not REDIS_AVAILABLE:
            raise ImportError("redis package is required for RedisCluster")
        
        self.nodes: Dict[str, DatabaseNode] = {}
        self.primary_node_id: Optional[str] = None
        self.redis_connections: Dict[str, aioredis.Redis] = {}
        
        # Configuration
        self.heartbeat_interval = 10.0
        self.failover_timeout = 30.0
        self.replication_timeout = 60.0
        
        # Tasks
        self.monitoring_task: Optional[asyncio.Task] = None
        self.running = False
        
        # Statistics
        self.stats = {
            'nodes_count': 0,
            'healthy_nodes': 0,
            'failovers_performed': 0,
            'replication_lag_max': 0
        }
    
    async def start(self):
        """Start cluster monitoring"""
        if not self.running:
            self.running = True
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            logger.info("Started Redis cluster monitoring")
    
    async def stop(self):
        """Stop cluster monitoring"""
        if self.running:
            self.running = False
            
            if self.monitoring_task:
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
            
            # Close connections
            for connection in self.redis_connections.values():
                await connection.close()
            
            self.redis_connections.clear()
            logger.info("Stopped Redis cluster monitoring")
    
    async def add_node(self, node: DatabaseNode) -> bool:
        """Add Redis node to cluster"""
        try:
            # Create connection to node
            redis_conn = aioredis.Redis(
                host=node.host,
                port=node.port,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Test connection
            await redis_conn.ping()
            
            # Add to cluster
            self.nodes[node.id] = node
            self.redis_connections[node.id] = redis_conn
            
            # Set as primary if first node or explicitly primary
            if not self.primary_node_id or node.role == NodeRole.PRIMARY:
                self.primary_node_id = node.id
                node.role = NodeRole.PRIMARY
            else:
                node.role = NodeRole.REPLICA
                # Configure replication
                await self._configure_replication(node.id)
            
            self.stats['nodes_count'] = len(self.nodes)
            logger.info(f"Added Redis node: {node.address} as {node.role.value}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add Redis node {node.address}: {e}")
            return False
    
    async def remove_node(self, node_id: str) -> bool:
        """Remove Redis node from cluster"""
        try:
            if node_id not in self.nodes:
                return False
            
            node = self.nodes[node_id]
            
            # If removing primary, perform failover first
            if node_id == self.primary_node_id:
                replica_nodes = await self.get_replica_nodes()
                if replica_nodes:
                    await self.failover(replica_nodes[0].id)
                else:
                    self.primary_node_id = None
            
            # Close connection
            if node_id in self.redis_connections:
                await self.redis_connections[node_id].close()
                del self.redis_connections[node_id]
            
            del self.nodes[node_id]
            self.stats['nodes_count'] = len(self.nodes)
            
            logger.info(f"Removed Redis node: {node.address}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove Redis node {node_id}: {e}")
            return False
    
    async def get_primary_node(self) -> Optional[DatabaseNode]:
        """Get primary Redis node"""
        if self.primary_node_id and self.primary_node_id in self.nodes:
            return self.nodes[self.primary_node_id]
        return None
    
    async def get_replica_nodes(self) -> List[DatabaseNode]:
        """Get replica Redis nodes"""
        return [
            node for node in self.nodes.values()
            if node.role == NodeRole.REPLICA and node.is_healthy
        ]
    
    async def failover(self, new_primary_id: str) -> bool:
        """Perform Redis failover"""
        try:
            if new_primary_id not in self.nodes:
                return False
            
            new_primary = self.nodes[new_primary_id]
            old_primary_id = self.primary_node_id
            
            logger.info(f"Starting failover from {old_primary_id} to {new_primary_id}")
            
            # Promote new primary
            if new_primary_id in self.redis_connections:
                redis_conn = self.redis_connections[new_primary_id]
                await redis_conn.execute_command("REPLICAOF", "NO", "ONE")
                
                new_primary.role = NodeRole.PRIMARY
                self.primary_node_id = new_primary_id
            
            # Demote old primary to replica
            if old_primary_id and old_primary_id in self.nodes:
                old_primary = self.nodes[old_primary_id]
                old_primary.role = NodeRole.REPLICA
                
                if old_primary_id in self.redis_connections:
                    old_redis_conn = self.redis_connections[old_primary_id]
                    await old_redis_conn.execute_command(
                        "REPLICAOF", new_primary.host, str(new_primary.port)
                    )
            
            # Reconfigure other replicas
            for node_id, node in self.nodes.items():
                if (node_id != new_primary_id and 
                    node.role == NodeRole.REPLICA and 
                    node_id in self.redis_connections):
                    
                    redis_conn = self.redis_connections[node_id]
                    await redis_conn.execute_command(
                        "REPLICAOF", new_primary.host, str(new_primary.port)
                    )
            
            self.stats['failovers_performed'] += 1
            logger.info(f"Failover completed: {new_primary_id} is now primary")
            
            return True
            
        except Exception as e:
            logger.error(f"Failover failed: {e}")
            return False
    
    async def get_cluster_status(self) -> Dict[str, Any]:
        """Get Redis cluster status"""
        healthy_nodes = [node for node in self.nodes.values() if node.is_healthy]
        self.stats['healthy_nodes'] = len(healthy_nodes)
        
        # Calculate max replication lag
        max_lag = 0
        for node in self.nodes.values():
            if node.role == NodeRole.REPLICA:
                max_lag = max(max_lag, node.lag_bytes)
        
        self.stats['replication_lag_max'] = max_lag
        
        return {
            'cluster_type': 'redis',
            'primary_node': self.primary_node_id,
            'nodes': [
                {
                    'id': node.id,
                    'address': node.address,
                    'role': node.role.value,
                    'status': node.status.value,
                    'lag_bytes': node.lag_bytes,
                    'is_healthy': node.is_healthy
                }
                for node in self.nodes.values()
            ],
            'statistics': self.stats,
            'timestamp': time.time()
        }
    
    async def _monitoring_loop(self):
        """Monitoring loop for cluster health"""
        while self.running:
            try:
                await self._check_cluster_health()
                await self._update_replication_lag()
                await asyncio.sleep(self.heartbeat_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(self.heartbeat_interval)
    
    async def _check_cluster_health(self):
        """Check health of all nodes"""
        for node_id, node in self.nodes.items():
            if node_id in self.redis_connections:
                try:
                    redis_conn = self.redis_connections[node_id]
                    await redis_conn.ping()
                    node.status = NodeStatus.HEALTHY
                    node.last_heartbeat = time.time()
                except Exception:
                    node.status = NodeStatus.UNHEALTHY
                    logger.warning(f"Redis node {node.address} is unhealthy")
        
        # Check if primary is down and perform automatic failover
        if self.primary_node_id:
            primary_node = self.nodes.get(self.primary_node_id)
            if primary_node and not primary_node.is_healthy:
                logger.warning("Primary node is unhealthy, attempting failover")
                replica_nodes = await self.get_replica_nodes()
                if replica_nodes:
                    await self.failover(replica_nodes[0].id)
    
    async def _update_replication_lag(self):
        """Update replication lag for replica nodes"""
        for node_id, node in self.nodes.items():
            if (node.role == NodeRole.REPLICA and 
                node_id in self.redis_connections):
                try:
                    redis_conn = self.redis_connections[node_id]
                    info = await redis_conn.info('replication')
                    
                    if 'master_repl_offset' in info and 'slave_repl_offset' in info:
                        master_offset = int(info['master_repl_offset'])
                        slave_offset = int(info['slave_repl_offset'])
                        node.lag_bytes = max(0, master_offset - slave_offset)
                    
                except Exception as e:
                    logger.warning(f"Failed to get replication lag for {node.address}: {e}")
    
    async def _configure_replication(self, replica_node_id: str):
        """Configure replication for a replica node"""
        if not self.primary_node_id or replica_node_id not in self.redis_connections:
            return
        
        primary_node = self.nodes[self.primary_node_id]
        redis_conn = self.redis_connections[replica_node_id]
        
        try:
            await redis_conn.execute_command(
                "REPLICAOF", primary_node.host, str(primary_node.port)
            )
            logger.info(f"Configured replication for {replica_node_id}")
        except Exception as e:
            logger.error(f"Failed to configure replication for {replica_node_id}: {e}")

class PostgreSQLCluster(DatabaseCluster):
    """PostgreSQL cluster implementation"""
    
    def __init__(self):
        if not POSTGRES_AVAILABLE:
            raise ImportError("asyncpg package is required for PostgreSQLCluster")
        
        self.nodes: Dict[str, DatabaseNode] = {}
        self.primary_node_id: Optional[str] = None
        self.connections: Dict[str, asyncpg.Connection] = {}
        
        # Configuration
        self.heartbeat_interval = 15.0
        self.replication_check_interval = 30.0
        
        # Tasks
        self.monitoring_task: Optional[asyncio.Task] = None
        self.running = False
        
        # Statistics
        self.stats = {
            'nodes_count': 0,
            'healthy_nodes': 0,
            'failovers_performed': 0,
            'replication_lag_max_bytes': 0
        }
    
    async def start(self):
        """Start PostgreSQL cluster monitoring"""
        if not self.running:
            self.running = True
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            logger.info("Started PostgreSQL cluster monitoring")
    
    async def stop(self):
        """Stop PostgreSQL cluster monitoring"""
        if self.running:
            self.running = False
            
            if self.monitoring_task:
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
            
            # Close connections
            for connection in self.connections.values():
                await connection.close()
            
            self.connections.clear()
            logger.info("Stopped PostgreSQL cluster monitoring")
    
    async def add_node(self, node: DatabaseNode) -> bool:
        """Add PostgreSQL node to cluster"""
        try:
            # Create connection to node
            connection = await asyncpg.connect(
                host=node.host,
                port=node.port,
                user=node.metadata.get('username', 'postgres'),
                password=node.metadata.get('password', ''),
                database=node.metadata.get('database', 'postgres'),
                command_timeout=5
            )
            
            # Test connection
            await connection.fetchval('SELECT 1')
            
            # Add to cluster
            self.nodes[node.id] = node
            self.connections[node.id] = connection
            
            # Determine role
            is_in_recovery = await connection.fetchval('SELECT pg_is_in_recovery()')
            
            if is_in_recovery:
                node.role = NodeRole.REPLICA
            else:
                if not self.primary_node_id:
                    self.primary_node_id = node.id
                    node.role = NodeRole.PRIMARY
                else:
                    # Multiple primaries - this shouldn't happen
                    logger.warning(f"Multiple primary nodes detected: {self.primary_node_id}, {node.id}")
                    node.role = NodeRole.STANDBY
            
            self.stats['nodes_count'] = len(self.nodes)
            logger.info(f"Added PostgreSQL node: {node.address} as {node.role.value}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add PostgreSQL node {node.address}: {e}")
            return False
    
    async def remove_node(self, node_id: str) -> bool:
        """Remove PostgreSQL node from cluster"""
        try:
            if node_id not in self.nodes:
                return False
            
            node = self.nodes[node_id]
            
            # If removing primary, we need manual intervention
            if node_id == self.primary_node_id:
                logger.warning(f"Removing primary node {node.address} - manual failover required")
                self.primary_node_id = None
            
            # Close connection
            if node_id in self.connections:
                await self.connections[node_id].close()
                del self.connections[node_id]
            
            del self.nodes[node_id]
            self.stats['nodes_count'] = len(self.nodes)
            
            logger.info(f"Removed PostgreSQL node: {node.address}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove PostgreSQL node {node_id}: {e}")
            return False
    
    async def get_primary_node(self) -> Optional[DatabaseNode]:
        """Get primary PostgreSQL node"""
        if self.primary_node_id and self.primary_node_id in self.nodes:
            return self.nodes[self.primary_node_id]
        return None
    
    async def get_replica_nodes(self) -> List[DatabaseNode]:
        """Get replica PostgreSQL nodes"""
        return [
            node for node in self.nodes.values()
            if node.role == NodeRole.REPLICA and node.is_healthy
        ]
    
    async def failover(self, new_primary_id: str) -> bool:
        """Perform PostgreSQL failover (manual process)"""
        try:
            if new_primary_id not in self.nodes:
                return False
            
            # PostgreSQL failover is typically handled by external tools
            # like Patroni, repmgr, or pg_auto_failover
            # This is a simplified version
            
            logger.warning("PostgreSQL failover requires manual intervention or external tools")
            logger.info(f"Promoting {new_primary_id} to primary (manual step required)")
            
            # Update our tracking
            old_primary_id = self.primary_node_id
            self.primary_node_id = new_primary_id
            
            if new_primary_id in self.nodes:
                self.nodes[new_primary_id].role = NodeRole.PRIMARY
            
            if old_primary_id and old_primary_id in self.nodes:
                self.nodes[old_primary_id].role = NodeRole.STANDBY
            
            self.stats['failovers_performed'] += 1
            
            return True
            
        except Exception as e:
            logger.error(f"PostgreSQL failover failed: {e}")
            return False
    
    async def get_cluster_status(self) -> Dict[str, Any]:
        """Get PostgreSQL cluster status"""
        healthy_nodes = [node for node in self.nodes.values() if node.is_healthy]
        self.stats['healthy_nodes'] = len(healthy_nodes)
        
        return {
            'cluster_type': 'postgresql',
            'primary_node': self.primary_node_id,
            'nodes': [
                {
                    'id': node.id,
                    'address': node.address,
                    'role': node.role.value,
                    'status': node.status.value,
                    'lag_bytes': node.lag_bytes,
                    'is_healthy': node.is_healthy
                }
                for node in self.nodes.values()
            ],
            'statistics': self.stats,
            'timestamp': time.time()
        }
    
    async def _monitoring_loop(self):
        """Monitoring loop for PostgreSQL cluster"""
        while self.running:
            try:
                await self._check_cluster_health()
                await self._update_replication_lag()
                await asyncio.sleep(self.heartbeat_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"PostgreSQL monitoring loop error: {e}")
                await asyncio.sleep(self.heartbeat_interval)
    
    async def _check_cluster_health(self):
        """Check health of PostgreSQL nodes"""
        for node_id, node in self.nodes.items():
            if node_id in self.connections:
                try:
                    connection = self.connections[node_id]
                    await connection.fetchval('SELECT 1')
                    node.status = NodeStatus.HEALTHY
                    node.last_heartbeat = time.time()
                except Exception:
                    node.status = NodeStatus.UNHEALTHY
                    logger.warning(f"PostgreSQL node {node.address} is unhealthy")
    
    async def _update_replication_lag(self):
        """Update replication lag for PostgreSQL replicas"""
        if not self.primary_node_id or self.primary_node_id not in self.connections:
            return
        
        try:
            primary_conn = self.connections[self.primary_node_id]
            primary_lsn = await primary_conn.fetchval('SELECT pg_current_wal_lsn()')
            
            for node_id, node in self.nodes.items():
                if (node.role == NodeRole.REPLICA and 
                    node_id in self.connections):
                    try:
                        replica_conn = self.connections[node_id]
                        replica_lsn = await replica_conn.fetchval('SELECT pg_last_wal_receive_lsn()')
                        
                        if primary_lsn and replica_lsn:
                            # Calculate lag in bytes (simplified)
                            lag_query = "SELECT pg_wal_lsn_diff($1, $2)"
                            lag_bytes = await replica_conn.fetchval(lag_query, primary_lsn, replica_lsn)
                            node.lag_bytes = max(0, int(lag_bytes or 0))
                        
                    except Exception as e:
                        logger.warning(f"Failed to get replication lag for {node.address}: {e}")
                        
        except Exception as e:
            logger.error(f"Failed to update replication lag: {e}")

class DatabaseClusterManager:
    """Manages multiple database clusters"""
    
    def __init__(self):
        self.clusters: Dict[str, DatabaseCluster] = {}
        self.cluster_configs: Dict[str, Dict[str, Any]] = {}
    
    def add_cluster(self, name: str, cluster: DatabaseCluster, 
                   config: Dict[str, Any] = None):
        """Add a database cluster"""
        self.clusters[name] = cluster
        self.cluster_configs[name] = config or {}
        logger.info(f"Added database cluster: {name}")
    
    def remove_cluster(self, name: str):
        """Remove a database cluster"""
        if name in self.clusters:
            del self.clusters[name]
            self.cluster_configs.pop(name, None)
            logger.info(f"Removed database cluster: {name}")
    
    def get_cluster(self, name: str) -> Optional[DatabaseCluster]:
        """Get a database cluster"""
        return self.clusters.get(name)
    
    async def start_all(self):
        """Start all clusters"""
        for name, cluster in self.clusters.items():
            try:
                await cluster.start()
                logger.info(f"Started cluster: {name}")
            except Exception as e:
                logger.error(f"Failed to start cluster {name}: {e}")
    
    async def stop_all(self):
        """Stop all clusters"""
        for name, cluster in self.clusters.items():
            try:
                await cluster.stop()
                logger.info(f"Stopped cluster: {name}")
            except Exception as e:
                logger.error(f"Failed to stop cluster {name}: {e}")
    
    async def get_all_status(self) -> Dict[str, Any]:
        """Get status of all clusters"""
        status = {}
        
        for name, cluster in self.clusters.items():
            try:
                status[name] = await cluster.get_cluster_status()
            except Exception as e:
                status[name] = {'error': str(e)}
        
        return status