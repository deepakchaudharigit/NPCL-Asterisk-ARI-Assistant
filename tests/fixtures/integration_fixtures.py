"""
Integration test fixtures for end-to-end testing scenarios.
Combines all components for comprehensive system testing.
"""

import pytest
import asyncio
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from unittest.mock import Mock, AsyncMock

from tests.fixtures.configuration_fixtures import TestEnvironmentConfig
from tests.fixtures.session_fixtures import SessionTestData, ConversationScenario
from tests.fixtures.network_fixtures import NetworkCondition, PerformanceScenario
from tests.fixtures.error_fixtures import ErrorScenario, ErrorInjectionConfig
from tests.mocks.mock_asterisk import MockAsteriskARIServer
from tests.mocks.mock_gemini import MockGeminiLiveAPI


@dataclass
class IntegrationTestScenario:
    """Complete integration test scenario."""
    name: str
    description: str
    environment_config: TestEnvironmentConfig
    test_duration_seconds: int
    expected_outcomes: Dict[str, Any] = field(default_factory=dict)
    performance_requirements: Dict[str, Any] = field(default_factory=dict)
    error_conditions: List[ErrorScenario] = field(default_factory=list)
    network_conditions: Optional[NetworkCondition] = None
    test_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class E2ETestFlow:
    """End-to-end test flow definition."""
    name: str
    description: str
    steps: List[Dict[str, Any]]
    expected_results: Dict[str, Any] = field(default_factory=dict)
    cleanup_steps: List[Dict[str, Any]] = field(default_factory=list)


class IntegrationTestEnvironment:
    """Complete integration test environment."""
    
    def __init__(self, config: TestEnvironmentConfig):
        self.config = config
        self.asterisk_server = None
        self.gemini_api = None
        self.active_sessions = {}
        self.test_metrics = {}
        self.is_running = False
        
    async def setup(self):
        """Setup the integration test environment."""
        # Start mock Asterisk server
        self.asterisk_server = MockAsteriskARIServer()
        
        # Start mock Gemini API
        self.gemini_api = MockGeminiLiveAPI()
        await self.gemini_api.connect()
        
        # Initialize metrics collection
        self.test_metrics = {
            "start_time": time.time(),
            "calls_processed": 0,
            "messages_sent": 0,
            "messages_received": 0,
            "errors_encountered": 0,
            "average_response_time": 0.0,
            "peak_memory_usage": 0,
            "peak_cpu_usage": 0
        }
        
        self.is_running = True
        
    async def teardown(self):
        """Teardown the integration test environment."""
        self.is_running = False
        
        # End all active sessions
        for session_id in list(self.active_sessions.keys()):
            await self.end_session(session_id)
        
        # Stop services
        if self.gemini_api:
            await self.gemini_api.disconnect()
        
        if self.asterisk_server:
            self.asterisk_server.reset()
        
        # Finalize metrics
        self.test_metrics["end_time"] = time.time()
        self.test_metrics["total_duration"] = (
            self.test_metrics["end_time"] - self.test_metrics["start_time"]
        )
    
    async def simulate_incoming_call(
        self,
        caller_number: str = "1234567890",
        called_number: str = "1000"
    ) -> str:
        """Simulate an incoming call."""
        channel_id = f"channel-{len(self.active_sessions)}"
        
        # Create session
        session_data = {
            "channel_id": channel_id,
            "caller_number": caller_number,
            "called_number": called_number,
            "start_time": time.time(),
            "state": "active",
            "conversation": []
        }
        
        self.active_sessions[channel_id] = session_data
        
        # Simulate ARI events
        await self.asterisk_server.simulate_incoming_call(channel_id, caller_number, called_number)
        
        self.test_metrics["calls_processed"] += 1
        return channel_id
    
    async def simulate_conversation(
        self,
        channel_id: str,
        conversation: ConversationScenario
    ):
        """Simulate a conversation on the given channel."""
        if channel_id not in self.active_sessions:
            raise ValueError(f"No active session for channel {channel_id}")
        
        session = self.active_sessions[channel_id]
        
        for turn in conversation.turns:
            # Simulate user speech
            if turn.role.value == "user":
                # Send audio to Gemini
                if turn.audio_data:
                    await self.gemini_api.send_audio_chunk(turn.audio_data)
                
                # Simulate speech detection
                await self.gemini_api.simulate_speech_detection(True)
                await asyncio.sleep(0.1)
                await self.gemini_api.simulate_speech_detection(False)
                
                # Commit audio buffer
                await self.gemini_api.commit_audio_buffer()
                
                self.test_metrics["messages_sent"] += 1
            
            # Simulate assistant response
            elif turn.role.value == "assistant":
                # Generate response
                await self.gemini_api.create_response()
                
                # Simulate audio response
                if turn.audio_data:
                    await self.gemini_api.simulate_audio_response(turn.audio_data)
                
                await self.gemini_api.simulate_response_complete()
                
                self.test_metrics["messages_received"] += 1
            
            # Add to conversation history
            session["conversation"].append({
                "role": turn.role.value,
                "content": turn.content,
                "timestamp": turn.timestamp
            })
            
            # Small delay between turns
            await asyncio.sleep(0.5)
    
    async def end_session(self, channel_id: str):
        """End a session."""
        if channel_id in self.active_sessions:
            # Simulate call hangup
            await self.asterisk_server.simulate_call_hangup(channel_id)
            
            # Remove from active sessions
            del self.active_sessions[channel_id]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current test metrics."""
        return self.test_metrics.copy()


class E2ETestRunner:
    """Runner for end-to-end test scenarios."""
    
    def __init__(self):
        self.test_results = []
        self.current_environment = None
    
    async def run_scenario(
        self,
        scenario: IntegrationTestScenario
    ) -> Dict[str, Any]:
        """Run a complete integration test scenario."""
        start_time = time.time()
        
        # Setup environment
        environment = IntegrationTestEnvironment(scenario.environment_config)
        await environment.setup()
        self.current_environment = environment
        
        try:
            # Execute test scenario
            results = await self._execute_scenario(scenario, environment)
            
            # Collect metrics
            metrics = environment.get_metrics()
            
            # Validate results
            validation_results = self._validate_results(
                results, scenario.expected_outcomes, metrics
            )
            
            end_time = time.time()
            
            return {
                "scenario": scenario.name,
                "success": validation_results["success"],
                "duration": end_time - start_time,
                "results": results,
                "metrics": metrics,
                "validation": validation_results,
                "performance": self._check_performance_requirements(
                    metrics, scenario.performance_requirements
                )
            }
            
        finally:
            # Cleanup
            await environment.teardown()
            self.current_environment = None
    
    async def _execute_scenario(
        self,
        scenario: IntegrationTestScenario,
        environment: IntegrationTestEnvironment
    ) -> Dict[str, Any]:
        """Execute the test scenario steps."""
        results = {
            "calls_completed": 0,
            "conversations_completed": 0,
            "errors_handled": 0,
            "performance_metrics": {}
        }
        
        # Run for specified duration
        end_time = time.time() + scenario.test_duration_seconds
        
        while time.time() < end_time and environment.is_running:
            try:
                # Simulate incoming call
                channel_id = await environment.simulate_incoming_call()
                
                # Run conversation if specified in test data
                if "conversation" in scenario.test_data:
                    conversation = scenario.test_data["conversation"]
                    await environment.simulate_conversation(channel_id, conversation)
                    results["conversations_completed"] += 1
                
                # End call
                await environment.end_session(channel_id)
                results["calls_completed"] += 1
                
                # Small delay between calls
                await asyncio.sleep(1.0)
                
            except Exception as e:
                results["errors_handled"] += 1
                # Continue with next iteration
        
        return results
    
    def _validate_results(
        self,
        results: Dict[str, Any],
        expected_outcomes: Dict[str, Any],
        metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate test results against expected outcomes."""
        validation = {
            "success": True,
            "failures": [],
            "warnings": []
        }
        
        # Check expected outcomes
        for key, expected_value in expected_outcomes.items():
            if key in results:
                actual_value = results[key]
                if actual_value != expected_value:
                    validation["failures"].append(
                        f"Expected {key}={expected_value}, got {actual_value}"
                    )
                    validation["success"] = False
            else:
                validation["failures"].append(f"Missing expected result: {key}")
                validation["success"] = False
        
        # Check basic metrics
        if metrics["calls_processed"] == 0:
            validation["warnings"].append("No calls were processed")
        
        if metrics["errors_encountered"] > metrics["calls_processed"] * 0.1:
            validation["warnings"].append("High error rate detected")
        
        return validation
    
    def _check_performance_requirements(
        self,
        metrics: Dict[str, Any],
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check if performance requirements are met."""
        performance = {
            "requirements_met": True,
            "violations": []
        }
        
        for requirement, threshold in requirements.items():
            if requirement in metrics:
                actual_value = metrics[requirement]
                if actual_value > threshold:
                    performance["violations"].append(
                        f"{requirement}: {actual_value} > {threshold}"
                    )
                    performance["requirements_met"] = False
        
        return performance


@pytest.fixture
def integration_test_scenarios():
    """Collection of integration test scenarios."""
    from tests.fixtures.configuration_fixtures import ConfigurationFixtures
    from tests.fixtures.session_fixtures import ConversationFixtures
    
    return {
        "basic_call_flow": IntegrationTestScenario(
            name="basic_call_flow",
            description="Basic call flow with simple conversation",
            environment_config=ConfigurationFixtures.create_development_config(),
            test_duration_seconds=30,
            expected_outcomes={
                "calls_completed": 1,
                "conversations_completed": 1,
                "errors_handled": 0
            },
            performance_requirements={
                "average_response_time": 2.0,
                "peak_memory_usage": 256,
                "peak_cpu_usage": 50
            },
            test_data={
                "conversation": ConversationFixtures.create_simple_greeting()
            }
        ),
        
        "high_load_scenario": IntegrationTestScenario(
            name="high_load_scenario",
            description="High load testing with multiple concurrent calls",
            environment_config=ConfigurationFixtures.create_performance_config(),
            test_duration_seconds=120,
            expected_outcomes={
                "calls_completed": 10,
                "conversations_completed": 10
            },
            performance_requirements={
                "average_response_time": 5.0,
                "peak_memory_usage": 1024,
                "peak_cpu_usage": 80
            },
            test_data={
                "conversation": ConversationFixtures.create_multi_turn_conversation()
            }
        ),
        
        "error_recovery_scenario": IntegrationTestScenario(
            name="error_recovery_scenario",
            description="Testing error recovery and resilience",
            environment_config=ConfigurationFixtures.create_error_simulation_config(),
            test_duration_seconds=60,
            expected_outcomes={
                "calls_completed": 3,
                "errors_handled": 2
            },
            performance_requirements={
                "average_response_time": 3.0
            },
            test_data={
                "conversation": ConversationFixtures.create_error_recovery_scenario()
            }
        )
    }


@pytest.fixture
def e2e_test_flows():
    """End-to-end test flows."""
    return {
        "complete_call_lifecycle": E2ETestFlow(
            name="complete_call_lifecycle",
            description="Complete call lifecycle from start to finish",
            steps=[
                {"action": "start_environment", "timeout": 10},
                {"action": "simulate_incoming_call", "caller": "1234567890"},
                {"action": "answer_call", "timeout": 5},
                {"action": "start_conversation", "timeout": 2},
                {"action": "exchange_messages", "count": 5, "timeout": 30},
                {"action": "end_conversation", "timeout": 2},
                {"action": "hangup_call", "timeout": 5}
            ],
            expected_results={
                "call_answered": True,
                "conversation_started": True,
                "messages_exchanged": 5,
                "call_ended_gracefully": True
            },
            cleanup_steps=[
                {"action": "cleanup_sessions"},
                {"action": "stop_environment"}
            ]
        ),
        
        "multi_call_scenario": E2ETestFlow(
            name="multi_call_scenario",
            description="Multiple simultaneous calls",
            steps=[
                {"action": "start_environment", "timeout": 10},
                {"action": "simulate_multiple_calls", "count": 5, "interval": 2},
                {"action": "handle_concurrent_conversations", "duration": 60},
                {"action": "end_all_calls", "timeout": 10}
            ],
            expected_results={
                "concurrent_calls": 5,
                "all_calls_handled": True,
                "no_call_interference": True
            },
            cleanup_steps=[
                {"action": "cleanup_all_sessions"},
                {"action": "stop_environment"}
            ]
        ),
        
        "network_resilience_test": E2ETestFlow(
            name="network_resilience_test",
            description="Test network resilience and recovery",
            steps=[
                {"action": "start_environment", "timeout": 10},
                {"action": "start_call", "timeout": 5},
                {"action": "simulate_network_issues", "duration": 10},
                {"action": "verify_recovery", "timeout": 15},
                {"action": "continue_conversation", "duration": 20},
                {"action": "end_call", "timeout": 5}
            ],
            expected_results={
                "network_issues_detected": True,
                "recovery_successful": True,
                "conversation_resumed": True
            },
            cleanup_steps=[
                {"action": "restore_network"},
                {"action": "cleanup_sessions"},
                {"action": "stop_environment"}
            ]
        )
    }


@pytest.fixture
async def integration_environment(integration_test_scenarios):
    """Integration test environment fixture."""
    scenario = integration_test_scenarios["basic_call_flow"]
    environment = IntegrationTestEnvironment(scenario.environment_config)
    
    await environment.setup()
    yield environment
    await environment.teardown()


@pytest.fixture
def e2e_test_runner():
    """End-to-end test runner fixture."""
    return E2ETestRunner()


@pytest.fixture
def load_test_scenarios():
    """Load testing scenarios for integration tests."""
    return {
        "light_load": {
            "concurrent_calls": 5,
            "call_duration_seconds": 30,
            "calls_per_minute": 10,
            "test_duration_minutes": 5
        },
        
        "moderate_load": {
            "concurrent_calls": 20,
            "call_duration_seconds": 60,
            "calls_per_minute": 30,
            "test_duration_minutes": 10
        },
        
        "heavy_load": {
            "concurrent_calls": 100,
            "call_duration_seconds": 120,
            "calls_per_minute": 100,
            "test_duration_minutes": 30
        },
        
        "stress_test": {
            "concurrent_calls": 500,
            "call_duration_seconds": 300,
            "calls_per_minute": 200,
            "test_duration_minutes": 60
        }
    }


@pytest.fixture
def system_monitoring():
    """System monitoring for integration tests."""
    class SystemMonitor:
        def __init__(self):
            self.metrics = {
                "cpu_usage": [],
                "memory_usage": [],
                "network_io": [],
                "disk_io": [],
                "response_times": [],
                "error_rates": []
            }
            self.monitoring = False
        
        async def start_monitoring(self):
            """Start system monitoring."""
            self.monitoring = True
            asyncio.create_task(self._monitor_loop())
        
        async def stop_monitoring(self):
            """Stop system monitoring."""
            self.monitoring = False
        
        async def _monitor_loop(self):
            """Monitoring loop."""
            import psutil
            
            while self.monitoring:
                # Collect system metrics
                self.metrics["cpu_usage"].append(psutil.cpu_percent())
                self.metrics["memory_usage"].append(psutil.virtual_memory().percent)
                
                # Network and disk I/O
                net_io = psutil.net_io_counters()
                disk_io = psutil.disk_io_counters()
                
                self.metrics["network_io"].append({
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv
                })
                
                self.metrics["disk_io"].append({
                    "read_bytes": disk_io.read_bytes,
                    "write_bytes": disk_io.write_bytes
                })
                
                await asyncio.sleep(1.0)
        
        def get_summary(self):
            """Get monitoring summary."""
            return {
                "avg_cpu_usage": sum(self.metrics["cpu_usage"]) / len(self.metrics["cpu_usage"]) if self.metrics["cpu_usage"] else 0,
                "max_cpu_usage": max(self.metrics["cpu_usage"]) if self.metrics["cpu_usage"] else 0,
                "avg_memory_usage": sum(self.metrics["memory_usage"]) / len(self.metrics["memory_usage"]) if self.metrics["memory_usage"] else 0,
                "max_memory_usage": max(self.metrics["memory_usage"]) if self.metrics["memory_usage"] else 0,
                "total_network_bytes": sum(
                    io["bytes_sent"] + io["bytes_recv"] for io in self.metrics["network_io"]
                ) if self.metrics["network_io"] else 0
            }
    
    monitor = SystemMonitor()
    yield monitor
    if monitor.monitoring:
        await monitor.stop_monitoring()


@pytest.fixture
def test_data_factory():
    """Factory for creating test data for integration tests."""
    def _create_test_data(
        scenario_type: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Create test data for specific scenario types."""
        
        if scenario_type == "voice_assistant_demo":
            return {
                "caller_info": {
                    "number": kwargs.get("caller_number", "1234567890"),
                    "name": kwargs.get("caller_name", "Test User")
                },
                "conversation_script": [
                    {"role": "user", "content": "Hello, I need help with my account"},
                    {"role": "assistant", "content": "I'd be happy to help you with your account. What specific issue are you experiencing?"},
                    {"role": "user", "content": "I can't log in to my online banking"},
                    {"role": "assistant", "content": "I understand you're having trouble logging into online banking. For security reasons, I'll need to verify your identity first."},
                    {"role": "user", "content": "Sure, what information do you need?"},
                    {"role": "assistant", "content": "Thank you for your cooperation. This completes our demo conversation."}
                ],
                "expected_outcomes": {
                    "authentication_requested": True,
                    "issue_identified": "login_problem",
                    "customer_satisfied": True
                }
            }
        
        elif scenario_type == "technical_support":
            return {
                "caller_info": {
                    "number": kwargs.get("caller_number", "9876543210"),
                    "name": kwargs.get("caller_name", "Tech User")
                },
                "conversation_script": [
                    {"role": "user", "content": "My internet connection is very slow"},
                    {"role": "assistant", "content": "I'm sorry to hear about the slow internet connection. Let me help you troubleshoot this issue."},
                    {"role": "user", "content": "I've already restarted my router"},
                    {"role": "assistant", "content": "Good, that's a great first step. Can you tell me what speed you're currently getting?"},
                    {"role": "user", "content": "It's about 5 Mbps, but I'm paying for 100 Mbps"},
                    {"role": "assistant", "content": "That's definitely much slower than expected. Let me run some diagnostics on your connection."}
                ],
                "expected_outcomes": {
                    "issue_identified": "slow_internet",
                    "troubleshooting_started": True,
                    "diagnostics_initiated": True
                }
            }
        
        else:
            # Default test data
            return {
                "caller_info": {"number": "0000000000", "name": "Default User"},
                "conversation_script": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi! How can I help you?"}
                ],
                "expected_outcomes": {"basic_interaction": True}
            }
    
    return _create_test_data