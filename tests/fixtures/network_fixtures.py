"""
Network and performance testing fixtures.
Provides fixtures for testing network conditions, WebSocket connections, and performance scenarios.
"""

import pytest
import asyncio
import time
import random
from typing import Dict, Any, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from unittest.mock import Mock, AsyncMock
import websockets
from websockets.exceptions import ConnectionClosed, ConnectionClosedError


@dataclass
class NetworkCondition:
    """Network condition simulation parameters."""
    name: str
    latency_ms: int
    jitter_ms: int
    packet_loss_percent: float
    bandwidth_kbps: int
    connection_stability: float  # 0.0 to 1.0
    description: str = ""


@dataclass
class PerformanceScenario:
    """Performance testing scenario."""
    name: str
    description: str
    concurrent_connections: int
    messages_per_second: int
    test_duration_seconds: int
    message_size_bytes: int
    expected_metrics: Dict[str, Any] = field(default_factory=dict)


class NetworkSimulator:
    """Simulates various network conditions for testing."""
    
    def __init__(self, condition: NetworkCondition):
        self.condition = condition
        self.message_count = 0
        self.dropped_messages = 0
        
    async def simulate_latency(self):
        """Simulate network latency with jitter."""
        base_latency = self.condition.latency_ms / 1000.0
        jitter = random.uniform(-self.condition.jitter_ms, self.condition.jitter_ms) / 1000.0
        total_latency = max(0, base_latency + jitter)
        
        if total_latency > 0:
            await asyncio.sleep(total_latency)
    
    def should_drop_packet(self) -> bool:
        """Determine if a packet should be dropped based on loss rate."""
        return random.random() < (self.condition.packet_loss_percent / 100.0)
    
    def is_connection_stable(self) -> bool:
        """Check if connection should remain stable."""
        return random.random() < self.condition.connection_stability
    
    async def send_with_simulation(self, websocket, message: str) -> bool:
        """Send message with network condition simulation."""
        self.message_count += 1
        
        # Check packet loss
        if self.should_drop_packet():
            self.dropped_messages += 1
            return False
        
        # Check connection stability
        if not self.is_connection_stable():
            raise ConnectionClosedError(None, None)
        
        # Simulate latency
        await self.simulate_latency()
        
        # Send message
        try:
            await websocket.send(message)
            return True
        except Exception:
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get network simulation statistics."""
        return {
            "total_messages": self.message_count,
            "dropped_messages": self.dropped_messages,
            "drop_rate": self.dropped_messages / max(1, self.message_count),
            "condition": self.condition.name
        }


class MockWebSocketConnection:
    """Mock WebSocket connection with network simulation."""
    
    def __init__(self, network_condition: Optional[NetworkCondition] = None):
        self.network_simulator = NetworkSimulator(network_condition) if network_condition else None
        self.is_connected = False
        self.messages_sent = []
        self.messages_received = []
        self.connection_events = []
        self.error_events = []
        
    async def connect(self, uri: str) -> bool:
        """Simulate connection establishment."""
        if self.network_simulator:
            await self.network_simulator.simulate_latency()
            if not self.network_simulator.is_connection_stable():
                self.error_events.append({"type": "connection_failed", "timestamp": time.time()})
                return False
        
        self.is_connected = True
        self.connection_events.append({"type": "connected", "timestamp": time.time()})
        return True
    
    async def disconnect(self):
        """Simulate disconnection."""
        self.is_connected = False
        self.connection_events.append({"type": "disconnected", "timestamp": time.time()})
    
    async def send(self, message: str) -> bool:
        """Send message with network simulation."""
        if not self.is_connected:
            return False
        
        if self.network_simulator:
            try:
                success = await self.network_simulator.send_with_simulation(self, message)
                if success:
                    self.messages_sent.append({"message": message, "timestamp": time.time()})
                return success
            except ConnectionClosedError:
                await self.disconnect()
                return False
        else:
            self.messages_sent.append({"message": message, "timestamp": time.time()})
            return True
    
    async def receive(self) -> Optional[str]:
        """Simulate receiving a message."""
        if not self.is_connected:
            return None
        
        if self.network_simulator:
            await self.network_simulator.simulate_latency()
            if not self.network_simulator.is_connection_stable():
                await self.disconnect()
                return None
        
        # Return a mock message for testing
        message = f"mock_response_{len(self.messages_received)}"
        self.messages_received.append({"message": message, "timestamp": time.time()})
        return message
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get connection statistics."""
        stats = {
            "is_connected": self.is_connected,
            "messages_sent": len(self.messages_sent),
            "messages_received": len(self.messages_received),
            "connection_events": len(self.connection_events),
            "error_events": len(self.error_events)
        }
        
        if self.network_simulator:
            stats.update(self.network_simulator.get_statistics())
        
        return stats


class PerformanceTestRunner:
    """Runs performance tests with various scenarios."""
    
    def __init__(self):
        self.test_results = []
        self.active_connections = []
        
    async def run_concurrent_connections_test(
        self,
        scenario: PerformanceScenario,
        connection_factory: Callable[[], MockWebSocketConnection]
    ) -> Dict[str, Any]:
        """Test concurrent WebSocket connections."""
        start_time = time.time()
        connections = []
        
        # Create connections
        for i in range(scenario.concurrent_connections):
            conn = connection_factory()
            connections.append(conn)
            success = await conn.connect(f"ws://test-server/{i}")
            if not success:
                continue
        
        # Send messages concurrently
        tasks = []
        for conn in connections:
            if conn.is_connected:
                task = self._send_messages_continuously(
                    conn,
                    scenario.messages_per_second,
                    scenario.test_duration_seconds,
                    scenario.message_size_bytes
                )
                tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Cleanup connections
        for conn in connections:
            if conn.is_connected:
                await conn.disconnect()
        
        end_time = time.time()
        
        # Collect statistics
        total_messages_sent = sum(len(conn.messages_sent) for conn in connections)
        total_errors = sum(len(conn.error_events) for conn in connections)
        
        return {
            "scenario": scenario.name,
            "duration": end_time - start_time,
            "concurrent_connections": len([c for c in connections if c.is_connected]),
            "total_messages_sent": total_messages_sent,
            "total_errors": total_errors,
            "messages_per_second": total_messages_sent / (end_time - start_time),
            "error_rate": total_errors / max(1, total_messages_sent),
            "connection_statistics": [conn.get_statistics() for conn in connections]
        }
    
    async def _send_messages_continuously(
        self,
        connection: MockWebSocketConnection,
        messages_per_second: int,
        duration_seconds: int,
        message_size_bytes: int
    ):
        """Send messages continuously at specified rate."""
        message = "x" * message_size_bytes
        interval = 1.0 / messages_per_second
        end_time = time.time() + duration_seconds
        
        while time.time() < end_time and connection.is_connected:
            await connection.send(message)
            await asyncio.sleep(interval)
    
    async def run_throughput_test(
        self,
        connection: MockWebSocketConnection,
        message_sizes: List[int],
        messages_per_size: int = 100
    ) -> Dict[str, Any]:
        """Test message throughput with different message sizes."""
        results = {}
        
        for size in message_sizes:
            message = "x" * size
            start_time = time.time()
            
            successful_sends = 0
            for _ in range(messages_per_size):
                if await connection.send(message):
                    successful_sends += 1
            
            end_time = time.time()
            duration = end_time - start_time
            
            results[f"size_{size}"] = {
                "message_size": size,
                "messages_sent": successful_sends,
                "duration": duration,
                "throughput_mbps": (successful_sends * size * 8) / (duration * 1_000_000),
                "messages_per_second": successful_sends / duration
            }
        
        return results


@pytest.fixture
def network_conditions():
    """Various network conditions for testing."""
    return {
        "perfect": NetworkCondition(
            name="perfect",
            latency_ms=0,
            jitter_ms=0,
            packet_loss_percent=0.0,
            bandwidth_kbps=1000000,
            connection_stability=1.0,
            description="Perfect network conditions"
        ),
        "good": NetworkCondition(
            name="good",
            latency_ms=50,
            jitter_ms=5,
            packet_loss_percent=0.1,
            bandwidth_kbps=1000,
            connection_stability=0.99,
            description="Good network conditions"
        ),
        "poor": NetworkCondition(
            name="poor",
            latency_ms=200,
            jitter_ms=50,
            packet_loss_percent=2.0,
            bandwidth_kbps=128,
            connection_stability=0.95,
            description="Poor network conditions"
        ),
        "terrible": NetworkCondition(
            name="terrible",
            latency_ms=500,
            jitter_ms=200,
            packet_loss_percent=10.0,
            bandwidth_kbps=64,
            connection_stability=0.80,
            description="Terrible network conditions"
        ),
        "mobile": NetworkCondition(
            name="mobile",
            latency_ms=150,
            jitter_ms=30,
            packet_loss_percent=1.0,
            bandwidth_kbps=256,
            connection_stability=0.90,
            description="Mobile network conditions"
        ),
        "satellite": NetworkCondition(
            name="satellite",
            latency_ms=600,
            jitter_ms=100,
            packet_loss_percent=0.5,
            bandwidth_kbps=512,
            connection_stability=0.95,
            description="Satellite network conditions"
        )
    }


@pytest.fixture
def performance_scenarios():
    """Performance testing scenarios."""
    return {
        "light_load": PerformanceScenario(
            name="light_load",
            description="Light load testing",
            concurrent_connections=5,
            messages_per_second=10,
            test_duration_seconds=30,
            message_size_bytes=100,
            expected_metrics={
                "max_response_time_ms": 1000,
                "error_rate_percent": 1.0,
                "memory_usage_mb": 100
            }
        ),
        "moderate_load": PerformanceScenario(
            name="moderate_load",
            description="Moderate load testing",
            concurrent_connections=20,
            messages_per_second=50,
            test_duration_seconds=60,
            message_size_bytes=500,
            expected_metrics={
                "max_response_time_ms": 2000,
                "error_rate_percent": 2.0,
                "memory_usage_mb": 300
            }
        ),
        "heavy_load": PerformanceScenario(
            name="heavy_load",
            description="Heavy load testing",
            concurrent_connections=100,
            messages_per_second=200,
            test_duration_seconds=120,
            message_size_bytes=1000,
            expected_metrics={
                "max_response_time_ms": 5000,
                "error_rate_percent": 5.0,
                "memory_usage_mb": 1000
            }
        ),
        "stress_test": PerformanceScenario(
            name="stress_test",
            description="Stress testing to find limits",
            concurrent_connections=500,
            messages_per_second=1000,
            test_duration_seconds=300,
            message_size_bytes=2000,
            expected_metrics={
                "max_response_time_ms": 10000,
                "error_rate_percent": 10.0,
                "memory_usage_mb": 2000
            }
        )
    }


@pytest.fixture
def mock_websocket_connection():
    """Basic mock WebSocket connection."""
    return MockWebSocketConnection()


@pytest.fixture
def network_simulator_factory(network_conditions):
    """Factory for creating network simulators."""
    def _create_simulator(condition_name: str) -> NetworkSimulator:
        condition = network_conditions[condition_name]
        return NetworkSimulator(condition)
    
    return _create_simulator


@pytest.fixture
def mock_connection_factory(network_conditions):
    """Factory for creating mock connections with network conditions."""
    def _create_connection(condition_name: Optional[str] = None) -> MockWebSocketConnection:
        condition = network_conditions.get(condition_name) if condition_name else None
        return MockWebSocketConnection(condition)
    
    return _create_connection


@pytest.fixture
def performance_test_runner():
    """Performance test runner."""
    return PerformanceTestRunner()


@pytest.fixture
async def websocket_server_mock():
    """Mock WebSocket server for testing."""
    class MockWebSocketServer:
        def __init__(self):
            self.clients = []
            self.messages = []
            self.is_running = False
        
        async def start(self, host: str = "localhost", port: int = 8765):
            self.is_running = True
            # Simulate server startup
            await asyncio.sleep(0.1)
        
        async def stop(self):
            self.is_running = False
            self.clients.clear()
        
        async def broadcast(self, message: str):
            self.messages.append(message)
            # Simulate broadcasting to all clients
            for client in self.clients:
                await client.send(message)
        
        def add_client(self, client):
            self.clients.append(client)
        
        def remove_client(self, client):
            if client in self.clients:
                self.clients.remove(client)
    
    server = MockWebSocketServer()
    yield server
    if server.is_running:
        await server.stop()


@pytest.fixture
def connection_pool():
    """Pool of WebSocket connections for testing."""
    class ConnectionPool:
        def __init__(self):
            self.connections = []
            self.active_connections = 0
        
        async def create_connection(self, network_condition: Optional[NetworkCondition] = None):
            conn = MockWebSocketConnection(network_condition)
            self.connections.append(conn)
            return conn
        
        async def connect_all(self, uri: str = "ws://test-server"):
            results = []
            for conn in self.connections:
                success = await conn.connect(uri)
                if success:
                    self.active_connections += 1
                results.append(success)
            return results
        
        async def disconnect_all(self):
            for conn in self.connections:
                if conn.is_connected:
                    await conn.disconnect()
            self.active_connections = 0
        
        def get_statistics(self):
            return {
                "total_connections": len(self.connections),
                "active_connections": self.active_connections,
                "connection_stats": [conn.get_statistics() for conn in self.connections]
            }
    
    pool = ConnectionPool()
    yield pool
    await pool.disconnect_all()


@pytest.fixture
def latency_test_scenarios():
    """Scenarios for testing latency under different conditions."""
    return {
        "baseline": {
            "description": "Baseline latency measurement",
            "network_condition": "perfect",
            "message_count": 100,
            "expected_max_latency_ms": 50
        },
        "high_latency": {
            "description": "High latency network",
            "network_condition": "satellite",
            "message_count": 50,
            "expected_max_latency_ms": 1000
        },
        "jittery_network": {
            "description": "Network with high jitter",
            "network_condition": "poor",
            "message_count": 100,
            "expected_max_latency_ms": 500
        },
        "packet_loss": {
            "description": "Network with packet loss",
            "network_condition": "terrible",
            "message_count": 200,
            "expected_max_latency_ms": 1000,
            "expected_loss_rate": 0.1
        }
    }


@pytest.fixture
def throughput_test_scenarios():
    """Scenarios for testing throughput."""
    return {
        "small_messages": {
            "description": "High frequency small messages",
            "message_sizes": [10, 50, 100],
            "messages_per_size": 1000,
            "expected_min_throughput_mbps": 1.0
        },
        "medium_messages": {
            "description": "Medium frequency medium messages",
            "message_sizes": [500, 1000, 2000],
            "messages_per_size": 500,
            "expected_min_throughput_mbps": 5.0
        },
        "large_messages": {
            "description": "Low frequency large messages",
            "message_sizes": [5000, 10000, 20000],
            "messages_per_size": 100,
            "expected_min_throughput_mbps": 10.0
        }
    }


@pytest.fixture
def error_injection_scenarios():
    """Scenarios for testing error handling."""
    return {
        "connection_drops": {
            "description": "Random connection drops",
            "error_type": "connection_drop",
            "frequency": 0.1,  # 10% chance per operation
            "recovery_expected": True
        },
        "timeout_errors": {
            "description": "Timeout errors",
            "error_type": "timeout",
            "frequency": 0.05,  # 5% chance per operation
            "recovery_expected": True
        },
        "protocol_errors": {
            "description": "Protocol-level errors",
            "error_type": "protocol_error",
            "frequency": 0.02,  # 2% chance per operation
            "recovery_expected": False
        },
        "server_errors": {
            "description": "Server-side errors",
            "error_type": "server_error",
            "frequency": 0.01,  # 1% chance per operation
            "recovery_expected": True
        }
    }