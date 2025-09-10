"""
Service Discovery Implementation
Provides service registration and discovery for distributed systems
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from abc import ABC, abstractmethod
import logging
import aiohttp
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class ServiceInstance:
    """Service instance information"""
    id: str
    name: str
    host: str
    port: int
    health_check_url: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    status: str = "healthy"
    last_heartbeat: float = field(default_factory=time.time)
    
    @property
    def address(self) -> str:
        """Get service address"""
        return f"{self.host}:{self.port}"
    
    @property
    def url(self) -> str:
        """Get service URL"""
        return f"http://{self.host}:{self.port}"

class ServiceDiscovery(ABC):
    """Abstract service discovery interface"""
    
    @abstractmethod
    async def register_service(self, service: ServiceInstance) -> bool:
        """Register a service instance"""
        pass
    
    @abstractmethod
    async def deregister_service(self, service_id: str) -> bool:
        """Deregister a service instance"""
        pass
    
    @abstractmethod
    async def discover_services(self, service_name: str) -> List[ServiceInstance]:
        """Discover instances of a service"""
        pass
    
    @abstractmethod
    async def get_service(self, service_id: str) -> Optional[ServiceInstance]:
        """Get specific service instance"""
        pass
    
    @abstractmethod
    async def list_services(self) -> List[str]:
        """List all service names"""
        pass

class InMemoryServiceDiscovery(ServiceDiscovery):
    """In-memory service discovery for development"""
    
    def __init__(self):
        self.services: Dict[str, ServiceInstance] = {}
        self.service_names: Dict[str, List[str]] = {}
        self.health_check_interval = 30.0
        self.health_check_timeout = 5.0
        self.health_check_task: Optional[asyncio.Task] = None
        self.running = False
    
    async def start(self):
        """Start service discovery"""
        if not self.running:
            self.running = True
            self.health_check_task = asyncio.create_task(self._health_check_loop())
            logger.info("Started in-memory service discovery")
    
    async def stop(self):
        """Stop service discovery"""
        if self.running:
            self.running = False
            if self.health_check_task:
                self.health_check_task.cancel()
                try:
                    await self.health_check_task
                except asyncio.CancelledError:
                    pass
            logger.info("Stopped in-memory service discovery")
    
    async def register_service(self, service: ServiceInstance) -> bool:
        """Register a service instance"""
        try:
            self.services[service.id] = service
            
            # Add to service name index
            if service.name not in self.service_names:
                self.service_names[service.name] = []
            
            if service.id not in self.service_names[service.name]:
                self.service_names[service.name].append(service.id)
            
            logger.info(f"Registered service: {service.name} ({service.id}) at {service.address}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register service {service.id}: {e}")
            return False
    
    async def deregister_service(self, service_id: str) -> bool:
        """Deregister a service instance"""
        try:
            if service_id in self.services:
                service = self.services[service_id]
                
                # Remove from service name index
                if service.name in self.service_names:
                    self.service_names[service.name] = [
                        sid for sid in self.service_names[service.name] 
                        if sid != service_id
                    ]
                    
                    # Clean up empty service name entries
                    if not self.service_names[service.name]:
                        del self.service_names[service.name]
                
                del self.services[service_id]
                logger.info(f"Deregistered service: {service.name} ({service_id})")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to deregister service {service_id}: {e}")
            return False
    
    async def discover_services(self, service_name: str) -> List[ServiceInstance]:
        """Discover instances of a service"""
        try:
            service_ids = self.service_names.get(service_name, [])
            services = []
            
            for service_id in service_ids:
                if service_id in self.services:
                    service = self.services[service_id]
                    if service.status == "healthy":
                        services.append(service)
            
            return services
            
        except Exception as e:
            logger.error(f"Failed to discover services for {service_name}: {e}")
            return []
    
    async def get_service(self, service_id: str) -> Optional[ServiceInstance]:
        """Get specific service instance"""
        return self.services.get(service_id)
    
    async def list_services(self) -> List[str]:
        """List all service names"""
        return list(self.service_names.keys())
    
    async def _health_check_loop(self):
        """Health check loop"""
        while self.running:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(self.health_check_interval)
    
    async def _perform_health_checks(self):
        """Perform health checks on all services"""
        tasks = []
        for service in self.services.values():
            if service.health_check_url:
                task = asyncio.create_task(self._check_service_health(service))
                tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _check_service_health(self, service: ServiceInstance):
        """Check health of a service instance"""
        try:
            async with aiohttp.ClientSession() as session:
                health_url = service.health_check_url or f"{service.url}/health"
                
                async with session.get(
                    health_url,
                    timeout=aiohttp.ClientTimeout(total=self.health_check_timeout)
                ) as response:
                    if response.status == 200:
                        service.status = "healthy"
                        service.last_heartbeat = time.time()
                    else:
                        service.status = "unhealthy"
                        
        except Exception as e:
            logger.warning(f"Health check failed for {service.id}: {e}")
            service.status = "unhealthy"

class ConsulServiceDiscovery(ServiceDiscovery):
    """Consul-based service discovery"""
    
    def __init__(self, consul_host: str = "localhost", consul_port: int = 8500):
        self.consul_host = consul_host
        self.consul_port = consul_port
        self.consul_url = f"http://{consul_host}:{consul_port}"
        self.session_id: Optional[str] = None
    
    async def register_service(self, service: ServiceInstance) -> bool:
        """Register service with Consul"""
        try:
            registration_data = {
                "ID": service.id,
                "Name": service.name,
                "Address": service.host,
                "Port": service.port,
                "Tags": service.tags,
                "Meta": service.metadata
            }
            
            # Add health check if URL provided
            if service.health_check_url:
                registration_data["Check"] = {
                    "HTTP": service.health_check_url,
                    "Interval": "30s",
                    "Timeout": "5s"
                }
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.consul_url}/v1/agent/service/register"
                
                async with session.put(url, json=registration_data) as response:
                    if response.status == 200:
                        logger.info(f"Registered service with Consul: {service.name} ({service.id})")
                        return True
                    else:
                        logger.error(f"Failed to register with Consul: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Error registering service with Consul: {e}")
            return False
    
    async def deregister_service(self, service_id: str) -> bool:
        """Deregister service from Consul"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.consul_url}/v1/agent/service/deregister/{service_id}"
                
                async with session.put(url) as response:
                    if response.status == 200:
                        logger.info(f"Deregistered service from Consul: {service_id}")
                        return True
                    else:
                        logger.error(f"Failed to deregister from Consul: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Error deregistering service from Consul: {e}")
            return False
    
    async def discover_services(self, service_name: str) -> List[ServiceInstance]:
        """Discover services from Consul"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.consul_url}/v1/health/service/{service_name}"
                params = {"passing": "true"}  # Only healthy services
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        services = []
                        
                        for entry in data:
                            service_data = entry["Service"]
                            
                            service = ServiceInstance(
                                id=service_data["ID"],
                                name=service_data["Service"],
                                host=service_data["Address"],
                                port=service_data["Port"],
                                metadata=service_data.get("Meta", {}),
                                tags=service_data.get("Tags", []),
                                status="healthy"
                            )
                            
                            services.append(service)
                        
                        return services
                    else:
                        logger.error(f"Failed to discover services from Consul: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error discovering services from Consul: {e}")
            return []
    
    async def get_service(self, service_id: str) -> Optional[ServiceInstance]:
        """Get service from Consul"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.consul_url}/v1/agent/service/{service_id}"
                
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        return ServiceInstance(
                            id=data["ID"],
                            name=data["Service"],
                            host=data["Address"],
                            port=data["Port"],
                            metadata=data.get("Meta", {}),
                            tags=data.get("Tags", [])
                        )
                    else:
                        return None
                        
        except Exception as e:
            logger.error(f"Error getting service from Consul: {e}")
            return None
    
    async def list_services(self) -> List[str]:
        """List services from Consul"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.consul_url}/v1/agent/services"
                
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        service_names = set()
                        
                        for service_data in data.values():
                            service_names.add(service_data["Service"])
                        
                        return list(service_names)
                    else:
                        return []
                        
        except Exception as e:
            logger.error(f"Error listing services from Consul: {e}")
            return []

class ServiceRegistry:
    """Service registry with automatic registration and discovery"""
    
    def __init__(self, discovery: ServiceDiscovery, node_id: str, 
                 host: str, port: int):
        self.discovery = discovery
        self.node_id = node_id
        self.host = host
        self.port = port
        
        # Registered services
        self.registered_services: Dict[str, ServiceInstance] = {}
        
        # Service watchers
        self.watchers: Dict[str, List[Callable]] = {}
        self.watch_tasks: Dict[str, asyncio.Task] = {}
        
        # Configuration
        self.watch_interval = 10.0
        self.auto_deregister = True
    
    async def register(self, service_name: str, service_port: int = None,
                      health_check_path: str = "/health",
                      metadata: Dict[str, Any] = None,
                      tags: List[str] = None) -> str:
        """Register a service"""
        service_id = f"{self.node_id}:{service_name}"
        port = service_port or self.port
        
        service = ServiceInstance(
            id=service_id,
            name=service_name,
            host=self.host,
            port=port,
            health_check_url=f"http://{self.host}:{port}{health_check_path}",
            metadata=metadata or {},
            tags=tags or []
        )
        
        success = await self.discovery.register_service(service)
        
        if success:
            self.registered_services[service_id] = service
            logger.info(f"Registered service: {service_name}")
        
        return service_id
    
    async def deregister(self, service_id: str) -> bool:
        """Deregister a service"""
        success = await self.discovery.deregister_service(service_id)
        
        if success and service_id in self.registered_services:
            del self.registered_services[service_id]
            logger.info(f"Deregistered service: {service_id}")
        
        return success
    
    async def discover(self, service_name: str) -> List[ServiceInstance]:
        """Discover service instances"""
        return await self.discovery.discover_services(service_name)
    
    async def get_healthy_instance(self, service_name: str) -> Optional[ServiceInstance]:
        """Get a healthy instance of a service"""
        instances = await self.discover(service_name)
        healthy_instances = [i for i in instances if i.status == "healthy"]
        
        if healthy_instances:
            # Simple round-robin selection
            import random
            return random.choice(healthy_instances)
        
        return None
    
    def watch_service(self, service_name: str, callback: Callable[[List[ServiceInstance]], None]):
        """Watch for changes in service instances"""
        if service_name not in self.watchers:
            self.watchers[service_name] = []
            # Start watch task
            self.watch_tasks[service_name] = asyncio.create_task(
                self._watch_service_loop(service_name)
            )
        
        self.watchers[service_name].append(callback)
        logger.info(f"Added watcher for service: {service_name}")
    
    def unwatch_service(self, service_name: str, callback: Callable = None):
        """Stop watching a service"""
        if service_name in self.watchers:
            if callback:
                self.watchers[service_name] = [
                    cb for cb in self.watchers[service_name] if cb != callback
                ]
            else:
                self.watchers[service_name].clear()
            
            # Stop watch task if no more watchers
            if not self.watchers[service_name]:
                if service_name in self.watch_tasks:
                    self.watch_tasks[service_name].cancel()
                    del self.watch_tasks[service_name]
                del self.watchers[service_name]
    
    async def cleanup(self):
        """Cleanup registered services"""
        if self.auto_deregister:
            for service_id in list(self.registered_services.keys()):
                await self.deregister(service_id)
        
        # Cancel watch tasks
        for task in self.watch_tasks.values():
            task.cancel()
        
        if self.watch_tasks:
            await asyncio.gather(*self.watch_tasks.values(), return_exceptions=True)
        
        self.watch_tasks.clear()
        self.watchers.clear()
    
    async def _watch_service_loop(self, service_name: str):
        """Watch service instances for changes"""
        last_instances = []
        
        while True:
            try:
                current_instances = await self.discover(service_name)
                
                # Check if instances changed
                if self._instances_changed(last_instances, current_instances):
                    # Notify watchers
                    for callback in self.watchers.get(service_name, []):
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(current_instances)
                            else:
                                callback(current_instances)
                        except Exception as e:
                            logger.error(f"Error in service watcher callback: {e}")
                    
                    last_instances = current_instances
                
                await asyncio.sleep(self.watch_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in service watch loop: {e}")
                await asyncio.sleep(self.watch_interval)
    
    def _instances_changed(self, old_instances: List[ServiceInstance], 
                          new_instances: List[ServiceInstance]) -> bool:
        """Check if service instances changed"""
        if len(old_instances) != len(new_instances):
            return True
        
        old_ids = {i.id for i in old_instances}
        new_ids = {i.id for i in new_instances}
        
        return old_ids != new_ids

class LoadBalancedServiceClient:
    """Client that automatically load balances across service instances"""
    
    def __init__(self, service_registry: ServiceRegistry, service_name: str):
        self.service_registry = service_registry
        self.service_name = service_name
        self.instances: List[ServiceInstance] = []
        self.current_index = 0
        
        # Start watching for service changes
        self.service_registry.watch_service(service_name, self._update_instances)
    
    async def _update_instances(self, instances: List[ServiceInstance]):
        """Update available instances"""
        self.instances = [i for i in instances if i.status == "healthy"]
        logger.debug(f"Updated instances for {self.service_name}: {len(self.instances)} available")
    
    async def make_request(self, method: str, path: str, **kwargs) -> Any:
        """Make load-balanced request to service"""
        if not self.instances:
            # Try to discover instances
            self.instances = await self.service_registry.discover(self.service_name)
            self.instances = [i for i in self.instances if i.status == "healthy"]
        
        if not self.instances:
            raise Exception(f"No healthy instances available for {self.service_name}")
        
        # Round-robin selection
        instance = self.instances[self.current_index % len(self.instances)]
        self.current_index += 1
        
        # Make request
        url = f"{instance.url}{path}"
        
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, **kwargs) as response:
                if response.content_type == 'application/json':
                    return await response.json()
                else:
                    return await response.text()
    
    async def get(self, path: str, **kwargs):
        """Make GET request"""
        return await self.make_request("GET", path, **kwargs)
    
    async def post(self, path: str, **kwargs):
        """Make POST request"""
        return await self.make_request("POST", path, **kwargs)
    
    async def put(self, path: str, **kwargs):
        """Make PUT request"""
        return await self.make_request("PUT", path, **kwargs)
    
    async def delete(self, path: str, **kwargs):
        """Make DELETE request"""
        return await self.make_request("DELETE", path, **kwargs)