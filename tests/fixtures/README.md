# Test Fixtures Documentation

This directory contains comprehensive test fixtures for the Voice Assistant system. The fixtures are organized into different categories to support various types of testing.

## Overview

The test fixtures provide:
- **Realistic test data** for all system components
- **Configurable scenarios** for different testing environments
- **Error simulation** for robustness testing
- **Performance testing** data and scenarios
- **Integration testing** environments

## Fixture Categories

### 1. Core Fixtures (`conftest.py`)
Global pytest fixtures available to all tests:
- `test_settings`: Core test configuration
- `gemini_config`: Gemini Live API configuration
- `sample_audio_data`: Basic audio samples
- `sample_ari_events`: ARI event samples
- `mock_asterisk_server`: Mock Asterisk server
- `mock_gemini_client`: Mock Gemini client

### 2. Audio Fixtures

#### Basic Audio (`audio_samples.py`)
- Pre-generated audio samples for consistent testing
- Various audio types: speech, silence, noise, DTMF tones
- Audio test patterns for conversation flows

#### Enhanced Audio (`enhanced_audio_fixtures.py`)
- Realistic speech with speaker characteristics
- Environmental noise simulation (office, street, cafe)
- Audio quality variations (phone quality, compression, echo)
- Edge cases and corrupted audio samples

**Usage Example:**
```python
def test_audio_processing(enhanced_audio_samples):
    male_speech = enhanced_audio_samples["male_speech"]
    noisy_speech = enhanced_audio_samples["office_noise_speech"]
    # Test audio processing with different samples
```

### 3. Configuration Fixtures (`configuration_fixtures.py`)
Different environment configurations for testing:
- **Development**: Local testing with mocks
- **Integration**: Testing with real services
- **Performance**: High-load testing configuration
- **Error Simulation**: Fault injection testing

**Usage Example:**
```python
def test_with_performance_config(performance_config):
    # Test with performance-optimized configuration
    assert performance_config.performance_config["max_concurrent_calls"] == 100
```

### 4. Session Fixtures (`session_fixtures.py`)
Session management and conversation testing:
- Session lifecycle data
- Conversation scenarios (greeting, multi-turn, interruption)
- Long-running sessions for performance testing
- Error recovery scenarios

**Usage Example:**
```python
def test_conversation_flow(conversation_scenarios):
    greeting = conversation_scenarios["simple_greeting"]
    assert len(greeting.turns) == 2
    assert greeting.turns[0].role == ConversationRole.USER
```

### 5. Network Fixtures (`network_fixtures.py`)
Network conditions and performance testing:
- Network condition simulation (perfect, poor, terrible)
- Performance scenarios (light, moderate, heavy load)
- WebSocket connection mocking
- Latency and throughput testing

**Usage Example:**
```python
async def test_network_resilience(mock_connection_factory, network_conditions):
    poor_connection = mock_connection_factory("poor")
    success = await poor_connection.connect("ws://test-server")
    # Test behavior under poor network conditions
```

### 6. Error Fixtures (`error_fixtures.py`)
Error simulation and edge case testing:
- Error scenarios (network, API, audio, system errors)
- Error injection configurations
- Malformed data samples
- Resource exhaustion scenarios

**Usage Example:**
```python
def test_error_handling(error_scenarios, error_simulator_factory):
    simulator = error_simulator_factory("moderate_error_rate")
    error = simulator.inject_error("websocket_connect")
    # Test error handling and recovery
```

### 7. Integration Fixtures (`integration_fixtures.py`)
End-to-end testing scenarios:
- Complete integration test environments
- E2E test flows
- Load testing scenarios
- System monitoring

**Usage Example:**
```python
async def test_complete_call_flow(integration_environment, e2e_test_flows):
    flow = e2e_test_flows["complete_call_lifecycle"]
    # Execute complete call flow test
```

## Fixture Usage Patterns

### 1. Unit Testing
```python
import pytest

def test_audio_processing(sample_audio_data):
    # Test individual component with basic audio
    result = process_audio(sample_audio_data)
    assert result is not None

def test_session_creation(basic_session):
    # Test session management
    assert basic_session.state == SessionState.ACTIVE
```

### 2. Integration Testing
```python
async def test_call_handling(integration_environment):
    # Test complete call flow
    channel_id = await integration_environment.simulate_incoming_call()
    # ... test conversation flow
    await integration_environment.end_session(channel_id)
```

### 3. Performance Testing
```python
def test_high_load(performance_scenarios, performance_test_runner):
    scenario = performance_scenarios["heavy_load"]
    results = await performance_test_runner.run_concurrent_connections_test(
        scenario, mock_connection_factory
    )
    assert results["error_rate"] < 0.05  # Less than 5% error rate
```

### 4. Error Testing
```python
def test_error_recovery(error_scenarios, fault_injection_decorator):
    @fault_injection_decorator(error_rate=0.5)
    async def unreliable_operation():
        # Simulate unreliable operation
        return "success"
    
    # Test with 50% error rate
    result = await unreliable_operation()
```

## Custom Fixture Creation

### Creating Custom Audio Samples
```python
from tests.utils.audio_generator import AudioGenerator

def create_custom_audio():
    # Generate 2 seconds of 880Hz tone
    return AudioGenerator.generate_sine_wave(880, 2000)
```

### Creating Custom Configurations
```python
def test_custom_config(custom_config, development_config):
    # Create custom configuration based on development config
    config = custom_config(
        "test_config",
        base_config=development_config,
        overrides={
            "audio_config": {"sample_rate": 8000},
            "performance_config": {"max_memory_mb": 128}
        }
    )
```

### Creating Custom Scenarios
```python
def test_custom_conversation(conversation_factory):
    # Create custom conversation scenario
    conversation = conversation_factory(
        "custom_test",
        turns=[
            {"role": "user", "content": "Custom question"},
            {"role": "assistant", "content": "Custom response"}
        ],
        expected_outcomes={"custom_metric": True}
    )
```

## Best Practices

### 1. Fixture Selection
- Use **basic fixtures** for unit tests
- Use **enhanced fixtures** for integration tests
- Use **error fixtures** for robustness testing
- Use **performance fixtures** for load testing

### 2. Test Isolation
- Each test should be independent
- Use fixture scopes appropriately (`function`, `class`, `module`, `session`)
- Clean up resources in fixture teardown

### 3. Realistic Testing
- Use realistic audio samples for audio processing tests
- Use realistic network conditions for network tests
- Use realistic error scenarios for error handling tests

### 4. Performance Considerations
- Large fixtures should use `session` scope when possible
- Generate test data lazily when appropriate
- Clean up large test data after use

## Fixture Dependencies

```
conftest.py (core fixtures)
├── configuration_fixtures.py
├── audio_samples.py
│   └── enhanced_audio_fixtures.py
├── session_fixtures.py
├── network_fixtures.py
├── error_fixtures.py
└── integration_fixtures.py
    ├── Uses all other fixtures
    └── Provides complete test environments
```

## Adding New Fixtures

When adding new fixtures:

1. **Choose the appropriate module** based on fixture category
2. **Follow naming conventions** (descriptive, snake_case)
3. **Add documentation** with usage examples
4. **Consider fixture scope** (function, class, module, session)
5. **Add cleanup logic** if the fixture creates resources
6. **Update this documentation** with the new fixture

### Example New Fixture
```python
@pytest.fixture
def custom_test_fixture():
    """Custom fixture for specific testing needs."""
    # Setup
    resource = create_test_resource()
    
    yield resource
    
    # Cleanup
    cleanup_test_resource(resource)
```

## Troubleshooting

### Common Issues

1. **Fixture not found**: Ensure the fixture is imported or defined in conftest.py
2. **Scope conflicts**: Check fixture scopes and dependencies
3. **Resource leaks**: Ensure proper cleanup in fixture teardown
4. **Performance issues**: Consider using session-scoped fixtures for expensive setup

### Debug Tips

1. Use `pytest --fixtures` to list available fixtures
2. Use `pytest -v` for verbose output
3. Use `pytest --setup-show` to see fixture setup/teardown
4. Add logging to fixtures for debugging

## Contributing

When contributing new fixtures:

1. Follow the existing patterns and conventions
2. Add comprehensive documentation
3. Include usage examples
4. Add appropriate tests for the fixtures themselves
5. Update this README with new fixture information