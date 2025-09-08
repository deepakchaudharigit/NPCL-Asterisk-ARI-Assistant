"""
Test helper functions and utilities.
"""

import asyncio
import time
import psutil
import threading
from typing import Any, Dict, List, Optional, Callable, Awaitable
from unittest.mock import Mock, AsyncMock
import json
import base64


class PerformanceMonitor:
    """Monitor performance metrics during tests."""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.memory_usage = []
        self.cpu_usage = []
        self.monitoring = False
        self.monitor_thread = None
    
    def start_monitoring(self):
        """Start performance monitoring."""
        self.start_time = time.time()
        self.monitoring = True
        self.memory_usage = []
        self.cpu_usage = []
        
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop performance monitoring."""
        self.monitoring = False
        self.end_time = time.time()
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
    
    def _monitor_loop(self):
        """Monitor loop running in separate thread."""
        process = psutil.Process()
        
        while self.monitoring:
            try:
                # Memory usage in MB
                memory_mb = process.memory_info().rss / 1024 / 1024
                self.memory_usage.append(memory_mb)
                
                # CPU usage percentage
                cpu_percent = process.cpu_percent()
                self.cpu_usage.append(cpu_percent)
                
                time.sleep(0.1)  # Sample every 100ms
            except Exception:
                break
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        duration = (self.end_time or time.time()) - (self.start_time or time.time())
        
        return {
            "duration_seconds": duration,
            "peak_memory_mb": max(self.memory_usage) if self.memory_usage else 0,
            "avg_memory_mb": sum(self.memory_usage) / len(self.memory_usage) if self.memory_usage else 0,
            "peak_cpu_percent": max(self.cpu_usage) if self.cpu_usage else 0,
            "avg_cpu_percent": sum(self.cpu_usage) / len(self.cpu_usage) if self.cpu_usage else 0
        }


class AsyncTestHelper:
    """Helper for async test operations."""
    
    @staticmethod
    async def wait_for_condition(
        condition: Callable[[], bool],
        timeout: float = 5.0,
        interval: float = 0.1
    ) -> bool:
        """Wait for a condition to become true."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if condition():
                return True
            await asyncio.sleep(interval)
        
        return False
    
    @staticmethod
    async def wait_for_async_condition(
        condition: Callable[[], Awaitable[bool]],
        timeout: float = 5.0,
        interval: float = 0.1
    ) -> bool:
        """Wait for an async condition to become true."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if await condition():
                return True
            await asyncio.sleep(interval)
        
        return False
    
    @staticmethod
    async def run_with_timeout(
        coro: Awaitable[Any],
        timeout: float = 5.0
    ) -> Any:
        """Run coroutine with timeout."""
        return await asyncio.wait_for(coro, timeout=timeout)


class MockWebSocketServer:
    """Mock WebSocket server for testing."""
    
    def __init__(self, host: str = "localhost", port: int = 8090):
        self.host = host
        self.port = port
        self.server = None
        self.connections = []
        self.message_handlers = {}
        self.connection_handlers = []
    
    async def start(self):
        """Start the mock WebSocket server."""
        import websockets
        
        self.server = await websockets.serve(
            self._handle_connection,
            self.host,
            self.port
        )
    
    async def stop(self):
        """Stop the mock WebSocket server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
    
    async def _handle_connection(self, websocket, path):
        """Handle new WebSocket connection."""
        self.connections.append(websocket)
        
        # Notify connection handlers
        for handler in self.connection_handlers:
            await handler(websocket, path)
        
        try:
            async for message in websocket:
                # Handle message based on path
                if path in self.message_handlers:
                    await self.message_handlers[path](websocket, message)
        except Exception:
            pass
        finally:
            if websocket in self.connections:
                self.connections.remove(websocket)
    
    def add_message_handler(self, path: str, handler: Callable):
        """Add message handler for specific path."""
        self.message_handlers[path] = handler
    
    def add_connection_handler(self, handler: Callable):
        """Add connection handler."""
        self.connection_handlers.append(handler)
    
    async def broadcast(self, message: Any):
        """Broadcast message to all connections."""
        if self.connections:
            await asyncio.gather(
                *[conn.send(message) for conn in self.connections],
                return_exceptions=True
            )


class MockAsteriskARI:
    """Mock Asterisk ARI server for testing."""
    
    def __init__(self):
        self.channels = {}
        self.bridges = {}
        self.recordings = {}
        self.event_handlers = []
    
    def add_event_handler(self, handler: Callable):
        """Add event handler."""
        self.event_handlers.append(handler)
    
    async def send_event(self, event: Dict[str, Any]):
        """Send event to all handlers."""
        for handler in self.event_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception:
                pass
    
    async def simulate_call_flow(self, channel_id: str, caller_number: str):
        """Simulate a complete call flow."""
        # StasisStart
        await self.send_event({
            "type": "StasisStart",
            "application": "gemini-voice-assistant",
            "timestamp": "2024-01-01T12:00:00.000Z",
            "channel": {
                "id": channel_id,
                "name": f"SIP/test-{channel_id}",
                "state": "Up",
                "caller": {"number": caller_number, "name": "Test Caller"},
                "dialplan": {"context": "gemini-voice-assistant", "exten": "1000"}
            }
        })
        
        # Simulate some delay
        await asyncio.sleep(0.1)
        
        # ChannelStateChange
        await self.send_event({
            "type": "ChannelStateChange",
            "timestamp": "2024-01-01T12:00:01.000Z",
            "channel": {
                "id": channel_id,
                "state": "Up"
            }
        })
        
        # Simulate call duration
        await asyncio.sleep(1.0)
        
        # StasisEnd
        await self.send_event({
            "type": "StasisEnd",
            "application": "gemini-voice-assistant",
            "timestamp": "2024-01-01T12:01:00.000Z",
            "channel": {
                "id": channel_id,
                "state": "Down"
            }
        })


class MockGeminiLiveAPI:
    """Mock Gemini Live API for testing."""
    
    def __init__(self):
        self.session_id = "test-session-123"
        self.response_id = "test-response-123"
        self.event_handlers = []
        self.audio_buffer = []
    
    def add_event_handler(self, handler: Callable):
        """Add event handler."""
        self.event_handlers.append(handler)
    
    async def send_event(self, event: Dict[str, Any]):
        """Send event to all handlers."""
        for handler in self.event_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception:
                pass
    
    async def simulate_session_creation(self):
        """Simulate session creation."""
        await self.send_event({
            "type": "session.created",
            "session": {
                "id": self.session_id,
                "model": "gemini-2.0-flash-exp"
            }
        })
    
    async def simulate_speech_detection(self, started: bool = True):
        """Simulate speech detection."""
        event_type = "input_audio_buffer.speech_started" if started else "input_audio_buffer.speech_stopped"
        await self.send_event({
            "type": event_type,
            "audio_start_ms" if started else "audio_end_ms": 1000
        })
    
    async def simulate_audio_response(self, audio_data: bytes):
        """Simulate audio response."""
        # Encode audio as base64
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        await self.send_event({
            "type": "response.audio.delta",
            "response": {
                "id": self.response_id,
                "output": {
                    "audio": audio_base64
                }
            }
        })
    
    async def simulate_response_complete(self):
        """Simulate response completion."""
        await self.send_event({
            "type": "response.audio.done",
            "response": {
                "id": self.response_id
            }
        })


class TestDataValidator:
    """Validate test data and results."""
    
    @staticmethod
    def validate_audio_data(
        audio_data: bytes,
        expected_duration_ms: int,
        sample_rate: int = 16000,
        tolerance_ms: int = 5
    ) -> bool:
        """Validate audio data duration and format."""
        expected_samples = int(sample_rate * expected_duration_ms / 1000)
        expected_bytes = expected_samples * 2  # 16-bit samples
        
        actual_bytes = len(audio_data)
        tolerance_bytes = int(sample_rate * tolerance_ms / 1000) * 2
        
        return abs(actual_bytes - expected_bytes) <= tolerance_bytes
    
    @staticmethod
    def validate_session_metrics(metrics: Dict[str, Any]) -> bool:
        """Validate session metrics structure."""
        required_fields = [
            "total_turns", "user_turns", "assistant_turns",
            "total_audio_duration", "average_response_time"
        ]
        
        return all(field in metrics for field in required_fields)
    
    @staticmethod
    def validate_performance_metrics(
        metrics: Dict[str, Any],
        thresholds: Dict[str, float]
    ) -> Dict[str, bool]:
        """Validate performance metrics against thresholds."""
        results = {}
        
        for metric, threshold in thresholds.items():
            if metric in metrics:
                results[metric] = metrics[metric] <= threshold
            else:
                results[metric] = False
        
        return results


class EventCollector:
    """Collect and analyze events during tests."""
    
    def __init__(self):
        self.events = []
        self.event_counts = {}
        self.start_time = None
    
    def start_collecting(self):
        """Start collecting events."""
        self.events = []
        self.event_counts = {}
        self.start_time = time.time()
    
    def add_event(self, event_type: str, data: Any = None):
        """Add an event."""
        timestamp = time.time() - (self.start_time or time.time())
        
        event = {
            "type": event_type,
            "timestamp": timestamp,
            "data": data
        }
        
        self.events.append(event)
        self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
    
    def get_events_by_type(self, event_type: str) -> List[Dict[str, Any]]:
        """Get events by type."""
        return [event for event in self.events if event["type"] == event_type]
    
    def get_event_timeline(self) -> List[Dict[str, Any]]:
        """Get chronological event timeline."""
        return sorted(self.events, key=lambda x: x["timestamp"])
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get event statistics."""
        return {
            "total_events": len(self.events),
            "event_counts": self.event_counts.copy(),
            "duration": max([e["timestamp"] for e in self.events]) if self.events else 0
        }